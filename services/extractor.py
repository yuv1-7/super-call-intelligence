import os
from typing import Literal
from openai import AsyncOpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

FAST_MODEL = "gpt-4.1-nano"


# ═══════════════════════════════════════════════════════
# PYDANTIC SCHEMAS — used by OpenAI Structured Outputs
# ═══════════════════════════════════════════════════════

class IntentClassification(BaseModel):
    intent: Literal[
        "car_accident",
        "car_theft",
        "car_vandalism",
        "life_death_claim",
        "life_accidental_death",
        "general_inquiry",
    ]
    claim_type: Literal["car_insurance", "life_insurance", "general"]


class ClaimFacts(BaseModel):
    """Structured extraction of all claim-relevant facts mentioned in the conversation."""
    caller_name: str | None
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


# ═══════════════════════════════════════════════════════
# INTENT CLASSIFICATION — Structured Output
# ═══════════════════════════════════════════════════════

async def classify_intent(transcript: str) -> dict:
    """Use LLM to classify the caller's intent into an FNOL category."""

    system_prompt = """You are an insurance call classification system.
Analyze the caller's statement and classify it.
- "intent": the most fitting FNOL category.
- "claim_type": the broad insurance line the intent falls under."""

    response = await client.beta.chat.completions.parse(
        model=FAST_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript},
        ],
        temperature=0.0,
        max_tokens=100,
        response_format=IntentClassification,
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
- The transcript comes from speech-to-text and may contain spelling errors, phonetic misspellings, or garbled text.
- You MUST normalize and clean all extracted values:
  * Fix obvious spelling mistakes (e.g., "Feburary" -> "February", "hosptial" -> "Hospital")
  * Capitalize proper nouns correctly (names, cities, hospitals, roads, etc.)
  * Standardize location names (e.g., "mg road" -> "MG Road", "city general" -> "City General Hospital")
  * Clean up caller names (e.g., "my name is priya" -> caller_name: "Priya", "i'm ravi kumar" -> "Ravi Kumar")
  * For incident descriptions, write a clean, concise summary in proper English, not verbatim speech-to-text.
  * For police report numbers, extract the exact alphanumeric code and format it cleanly (e.g., "F I R 2026 M H 4521" -> "FIR-2026-MH-4521")
- Output all values as clean, professional text suitable for an official insurance form.

CRITICAL — date_of_incident and time_of_incident rules:
- The current date and time is: {current_datetime_str}
- If the caller uses RELATIVE time references like "happened an hour ago", "just happened", "yesterday", "two days ago", "last night", "this morning", etc., you MUST extrapolate the actual date and time based on the current date/time above.
- For example, if it is currently 2026-02-26 10:30 and the caller says "it happened about one hour ago", set date_of_incident to "2026-02-26" and time_of_incident to "approximately 09:30".

CRITICAL — caller_name rules:
- The caller_name is the CUSTOMER's own name — the person calling in.
- When the customer says "Hi George" or "Hello Josh", they are ADDRESSING THE AGENT by the agent's name. This is NOT the caller's name. Do NOT extract the agent's name as the caller_name.

CRITICAL — policy_number rules:
- Extract the policy number ONLY if the customer explicitly states it (e.g. "my policy number is NS-88402911").
- Format it in standard form: uppercase prefix, hyphen, digits (e.g., "ns 88402911" -> "NS-88402911").

CRITICAL — police_report_filed and police_report_number rules:
- If the caller explicitly says they DID file a police report, set police_report_filed to true.
- If the caller explicitly says they did NOT file a police report ("no", "not yet", "haven't filed one"), set police_report_filed to false.
- If police reporting was never discussed, set police_report_filed to null.
- If they say a police report was filed but did NOT provide the number, set police_report_filed to true and police_report_number to null."""

    response = await client.beta.chat.completions.parse(
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
