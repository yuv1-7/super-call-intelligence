import os
from typing import Literal
from openai import AsyncOpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

_client = None

def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

FAST_MODEL = "gpt-4.1-nano"


# ═══════════════════════════════════════════════════════
# PYDANTIC SCHEMAS — used by OpenAI Structured Outputs
# ═══════════════════════════════════════════════════════

class IntentClassification(BaseModel):
    english_translation: str
    intent: Literal[
        "car_accident",
        "car_theft",
        "car_vandalism",
        "life_death_claim",
        "life_accidental_death",
        "medical_hospitalization",
        "medical_outpatient",
        "medical_critical_illness",
        "general_inquiry",
    ]
    claim_type: Literal["car_insurance", "life_insurance", "medical_insurance", "general"]


class EntityExtraction(BaseModel):
    policy_id: str | None
    name: str | None
    phone: str | None


class ClaimFacts(BaseModel):
    """Structured extraction of all claim-relevant facts mentioned in the conversation."""
    caller_name: str | None
    caller_phone: str | None
    policy_number: str | None
    relationship_to_policyholder: str | None
    incident_description: str | None
    date_of_incident: str | None
    time_of_incident: str | None
    location_of_incident: str | None
    cause_of_death: str | None
    injuries_reported: str | None
    vehicle_drivable: bool | None
    police_report_filed: bool | None
    police_report_number: str | None
    other_parties_involved: str | None
    # Medical-specific fields
    hospital_name: str | None
    admission_date: str | None
    discharge_date: str | None
    diagnosis: str | None
    treating_doctor: str | None
    cashless_or_reimbursement: str | None
    pre_authorization_number: str | None


# ═══════════════════════════════════════════════════════
# INTENT CLASSIFICATION — Structured Output
# ═══════════════════════════════════════════════════════

async def classify_intent(transcript: str) -> dict:
    """Use LLM to classify the caller's intent into an FNOL category."""

    system_prompt = """You are an insurance call classification system.
Analyze the caller's statement (which may be in English, another language, or a mix of languages) and classify it.
- "english_translation": an accurate English translation of what the caller said (if they spoke in English, just repeat it).
- "intent": the most fitting FNOL category.
- "claim_type": the broad insurance line the intent falls under."""

    response = await _get_client().beta.chat.completions.parse(
        model=FAST_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript},
        ],
        temperature=0.0,
        max_tokens=150,
        response_format=IntentClassification,
    )

    return response.choices[0].message.parsed.model_dump()


# ═══════════════════════════════════════════════════════
# ENTITY EXTRACTION — Structured Output
# ═══════════════════════════════════════════════════════

async def extract_entities(transcript: str) -> dict:
    """Use LLM to extract names, phone numbers, and policy IDs from transcript."""
    
    system_prompt = """You are an insurance entity extraction system.
Analyze the provided transcript segment (which may contain multiple sentences in any language or mix of languages) and extract the following if present. Your output must be in English:
- "policy_id": formatted strictly as CAR-XXXXXX, LIFE-XXXXXX, or MED-XXXXXX. 
  * CRITICAL: The policy number might be split across multiple sentences (e.g., "My policy is Life.", "Two zero zero zero zero one"). You MUST stitch them together into "LIFE-200001".
  * CRITICAL: If the user speaks the numbers as words in any language (e.g., Hindi "do lakh ek", "ek do teen", Spanish "uno dos tres"), you MUST translate them to English digits (123).
- "name": full or partial name of the caller.
- "phone": phone number referenced. You MUST translate any spoken numbers into English digits and stitch them if split across sentences.
Return null for fields not found."""

    response = await _get_client().beta.chat.completions.parse(
        model=FAST_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript},
        ],
        temperature=0.0,
        max_tokens=150,
        response_format=EntityExtraction,
    )

    return response.choices[0].message.parsed.model_dump()


# ═══════════════════════════════════════════════════════
# CLAIM FACTS EXTRACTION — Structured Output
# ═══════════════════════════════════════════════════════

async def extract_claim_facts(full_transcript: str) -> dict:
    """Extract all claim-relevant facts already mentioned in the conversation.
    This runs on the FULL transcript so the suggestion LLM gets an explicit
    list of what's known vs what's still missing."""

    # Get current time for relative time extrapolation
    from datetime import datetime
    now = datetime.now()
    current_datetime_str = now.strftime("%Y-%m-%d %H:%M")

    system_prompt = f"""You are a fact extraction system for insurance calls.
Analyze the ENTIRE conversation transcript and extract every claim-relevant fact that has been mentioned by either the customer or the agent.
Return null for any field that has NOT been mentioned or discussed at all.
Be generous in extraction — if someone says "at City General Hospital", that IS the location. If they say "heart attack", that IS the cause of death. If they say "February 10th", that IS the date.
Do NOT leave a field null if the information was mentioned even casually or indirectly.

CRITICAL — Data Quality & Normalization:
- The transcript comes from speech-to-text and may contain spelling errors, phonetic misspellings, garbled text, or a mix of multiple languages.
- You must understand the context regardless of the language and write your extracted facts strictly in English.
- You MUST normalize and clean all extracted values:
  * Fix obvious spelling mistakes (e.g., "Feburary" → "February", "hosptial" → "Hospital")
  * Capitalize proper nouns correctly (names, cities, hospitals, roads, etc.)
  * Standardize location names (e.g., "mg road" → "MG Road", "city general" → "City General Hospital")
  * Clean up caller names (e.g., "my name is priya" → caller_name: "Priya", "i'm ravi kumar" → "Ravi Kumar")
  * For incident descriptions, write a clean, concise summary in proper English, not verbatim speech-to-text. E.g., "yeah so like this guy he just backed into my car in the parking" → "Another vehicle backed into the caller's car in a parking lot."
  * For injuries, write clearly: "yeah my neck hurts a bit" → "Minor neck pain reported"
  * For police report numbers, extract the exact alphanumeric code and format it cleanly (e.g., "F I R 2026 M H 4521" → "FIR-2026-MH-4521")
- Output all values as clean, professional text suitable for an official insurance form.

CRITICAL — date_of_incident and time_of_incident rules:
- The current date and time is: {current_datetime_str}
- If the caller uses RELATIVE time references like "happened an hour ago", "just happened", "yesterday", "two days ago", "last night", "this morning", etc., you MUST extrapolate the actual date and time based on the current date/time above.
- For example, if it is currently 2026-02-26 10:30 and the caller says "it happened about one hour ago", set date_of_incident to "2026-02-26" and time_of_incident to "approximately 09:30".
- If they say "yesterday afternoon", set date_of_incident to the previous date and time_of_incident to "afternoon".
- Always output date_of_incident in YYYY-MM-DD format when you can extrapolate it.
- Always output time_of_incident as a specific time (HH:MM) or descriptive ("morning", "evening") when you can.

CRITICAL — caller_name rules:
- The caller_name is the CUSTOMER's own name — the person calling in.
- When the customer says "Hi George" or "Hello Josh", they are ADDRESSING THE AGENT by the agent's name. This is NOT the caller's name. Do NOT extract the agent's name as the caller_name.
- Only extract caller_name if the customer explicitly introduces themselves, e.g. "My name is Sarah" or "This is Ravi calling".
- If the customer has not stated their own name, return null for caller_name.

CRITICAL — caller_phone rules:
- Extract the caller's phone number if explicitly stated (e.g. "my number is 555-1234").
- Format it nicely with hyphens or just extract digits.
- Return null if no phone number was mentioned.

CRITICAL — policy_number rules:
- Extract the policy number ONLY if the customer explicitly states it (e.g. "my policy number is CAR-12345").
- Format it in standard form: uppercase prefix, hyphen, digits (e.g., "car 12345" → "CAR-12345", "life 200001" → "LIFE-200001", "med 300001" → "MED-300001").
- Return null if no policy number has been mentioned.

CRITICAL — police_report_filed and police_report_number rules:
- If the caller explicitly says they DID file a police report, set police_report_filed to true.
- If the caller explicitly says they did NOT file a police report ("no", "not yet", "haven't filed one"), set police_report_filed to false.
- If police reporting was never discussed, set police_report_filed to null.
- If the caller mentions a police report number, FIR number, or complaint number, extract it.
- e.g. "the police report number is FIR-2026-4521" → police_report_number = "FIR-2026-4521"
- If they say a police report was filed but did NOT provide the number, set police_report_filed to true and police_report_number to null.
- Return null for police_report_number if no number was mentioned.

CRITICAL — Medical claim fields:
- hospital_name: Name of the hospital where the policyholder is admitted or being treated. Extract from context (e.g. "I'm at Mount Sinai" → "Mount Sinai Hospital").
- admission_date: When the person was admitted. Use YYYY-MM-DD format. Extrapolate from relative references using current date/time.
- discharge_date: When discharged, if mentioned. Use YYYY-MM-DD format. Null if still admitted or not mentioned.
- diagnosis: The medical condition, disease, or reason for hospitalization (e.g. "appendicitis", "kidney stones", "heart attack").
- treating_doctor: Name of the doctor, if mentioned.
- cashless_or_reimbursement: If the caller mentions in-network/out-of-network or direct billing/reimbursement preference. One of: "in-network", "out-of-network", or null if not discussed.
- pre_authorization_number: Pre-authorization or approval reference number if provided by the caller or hospital.
- Return null for all medical fields if this is not a medical claim."""

    response = await _get_client().beta.chat.completions.parse(
        model=FAST_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_transcript or "No transcript yet"},
        ],
        temperature=0.0,
        max_tokens=500,
        response_format=ClaimFacts,
    )

    return response.choices[0].message.parsed.model_dump()


# ═══════════════════════════════════════════════════════
# STALL RESPONSE — Ultra-fast empathetic filler while
# the main pipeline (intent + KB + facts + ReAct) runs
# ═══════════════════════════════════════════════════════

async def generate_stall_response(utterance: str, is_opening: bool = True):
    """Generate a fast filler response for the agent to say while the main
    pipeline processes. Yields tokens as an async generator for streaming.

    Args:
        utterance: The caller's latest text.
        is_opening: True for the first utterance (empathetic tone),
                    False for mid-call topic changes (transitional tone).
    """

    if is_opening:
        system_prompt = """You are an insurance call center assistant. Generate a brief, empathetic acknowledgement for the agent to say to the caller while their account information is being retrieved.

Rules:
- Keep it to 1-2 SHORT sentences maximum (under 40 words)
- Be warm, professional, and contextually appropriate to what the caller said
- If the caller reports a loss or death, express brief sincere condolences
- If the caller reports an accident, express concern for safety first
- If it's a general inquiry, be helpful and reassuring
- Always end with a natural transitional phrase like "Let me pull up your account right away..." or "Let me look into this for you immediately..."
- Write the response FOR the agent to read verbatim to the caller
- Do NOT ask for policy numbers, phone numbers, or any specific information
- Do NOT ask any questions — this is purely an acknowledgement and transition
- Output in the same language the caller is using (use Romanized/Latin script only, no Devanagari or other scripts)"""
    else:
        system_prompt = """You are an insurance call center assistant. The caller has just brought up a new topic or issue mid-call. Generate a very brief transitional acknowledgement for the agent to say while the system retrieves updated information.

Rules:
- Keep it to 1 SHORT sentence (under 20 words)
- Be professional and reassuring — NOT empathetic or sympathetic (this is mid-call, not the opening)
- Use a transitional phrase like "Sure, let me pull up the details on that for you..." or "Absolutely, let me look into that right away..."
- Do NOT express condolences, sympathy, or concern — the caller is just changing topics
- Do NOT ask any questions
- Write the response FOR the agent to read verbatim to the caller
- Output in the same language the caller is using (use Romanized/Latin script only)"""

    response = await _get_client().chat.completions.create(
        model=FAST_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": utterance},
        ],
        temperature=0.4,
        max_tokens=80,
        stream=True,
    )

    async for chunk in response:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
