# tools/llm.py — OpenAI LLM utilities for Insurance FNOL + Post-Call Evaluation

import os
import json
import asyncio
from typing import Literal
from openai import AsyncOpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = "gpt-4.1-mini"          # For suggestion generation (needs quality)
FAST_MODEL = "gpt-4.1-nano"     # For utility calls: intent, entity, fact extraction (needs speed)


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
        "general_inquiry",
    ]
    claim_type: Literal["car_insurance", "life_insurance", "general"]


class EntityExtraction(BaseModel):
    policy_id: str | None
    name: str | None
    phone: str | None


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


# ─── Rubric-Based Post-Call Evaluation Schemas ─── #

class RubricItem(BaseModel):
    """A single scored criterion within a rubric section."""
    criterion: str           # e.g. "Call recording disclosure given"
    points_possible: int     # max points for this item
    points_awarded: int      # 0 to points_possible
    passed: bool
    evidence: str            # exact transcript quote, or "Not found"
    deduction_reason: str | None  # why points were lost (null if passed)


class ScoredSection(BaseModel):
    """One of the 6 scored rubric sections."""
    section_name: str
    points_possible: int
    points_awarded: int
    auto_failed: bool
    auto_fail_reason: str | None
    rubric_items: list[RubricItem]


class RubricEvaluation(BaseModel):
    """LLM Call A output — rubric scoring with evidence."""
    section_1_opening: ScoredSection
    section_2_identity: ScoredSection
    section_3_information: ScoredSection
    section_4_empathy: ScoredSection
    section_5_procedure: ScoredSection
    section_6_compliance: ScoredSection
    section_7_close: ScoredSection
    auto_fails: list[str]          # list of triggered auto-fail descriptions


class NarrativeEvaluation(BaseModel):
    """LLM Call B output — comprehensive narrative/coaching feedback."""
    call_summary: str             # Multi-paragraph detailed call narrative
    caller_profile: str           # Caller behavior, tone, emotional state summary
    call_highlights: list[str]    # Key moments/events during the call
    strengths: list[str]
    improvements: list[str]
    coaching_notes: str
    recommended_supervisor_action: str | None


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

    response = await client.beta.chat.completions.parse(
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
Analyze the caller's statement (which may be in any language, or a mix of languages) and extract the following if present. Your output must be in English:
- "policy_id": formatted strictly as CAR-XXXXXX or LIFE-XXXXXX. If the user speaks the numbers in another language (e.g., Hindi "ek do teen"), you MUST translate them to English digits (123).
- "name": full or partial name of the caller.
- "phone": phone number referenced. You MUST translate any spoken numbers into English digits.
Return null for fields not found."""

    response = await client.beta.chat.completions.parse(
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

CRITICAL — policy_number rules:
- Extract the policy number ONLY if the customer explicitly states it (e.g. "my policy number is CAR-12345").
- Format it in standard form: uppercase prefix, hyphen, digits (e.g., "car 12345" → "CAR-12345", "life 200001" → "LIFE-200001").
- Return null if no policy number has been mentioned.

CRITICAL — police_report_filed and police_report_number rules:
- If the caller explicitly says they DID file a police report, set police_report_filed to true.
- If the caller explicitly says they did NOT file a police report ("no", "not yet", "haven't filed one"), set police_report_filed to false.
- If police reporting was never discussed, set police_report_filed to null.
- If the caller mentions a police report number, FIR number, or complaint number, extract it.
- e.g. "the police report number is FIR-2026-4521" → police_report_number = "FIR-2026-4521"
- If they say a police report was filed but did NOT provide the number, set police_report_filed to true and police_report_number to null.
- Return null for police_report_number if no number was mentioned."""

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


# ═══════════════════════════════════════════════════════
# AGENT SUGGESTION — Separated Prompts by Policy Type
# ═══════════════════════════════════════════════════════

# ─── SHARED BASE RULES (apply to ALL claim types) ─── #
_SHARED_RULES = """You are an AI assistant and training tool for insurance call center agents.
Your role is to guide the agent through the conversation naturally, handling First Notice of Loss (FNOL) and general inquiries smoothly without sounding like a rigid checklist robot.
Generate a professional, empathetic, and compliance-aware suggested response for the agent to say to the caller.

Core Rules:
- **LANGUAGE & COLLOQUIAL TONE (CRITICAL LAYER)**: 
  * You MUST analyze the transcript to detect the caller's language and manner (e.g., pure English, Hindi, German, mixed Hinglish).
  * Your output language MUST perfectly match the caller's input language. If they speak 100% English, respond in 100% English. If they speak a mix, mirror that mix.
  * ALWAYS use phonetic English (Romanized script) for your output, regardless of the language spoken. NO Devanagari, Cyrillic, or other scripts.
  * CRITICAL RULE - MODERN & NATURAL: Do NOT use formal, "textbook" translations or overly pure vocabulary (e.g., do NOT translate "state", "accident", "process", or "insurance" into pure Hindi like "rajya", "durghatna", or "bima"). Real people use English loan words constantly. Write EXACTLY how a modern native speaker talks in daily life (e.g., "Aap kis state se hain?", "Accident kahan hua?").
  * EMOTIONAL AWARENESS: Be naturally empathetic when appropriate (e.g., if there's an accident, ask about safety/injuries immediately), but maintain conversational flow. Don't be robotic.
  * STRICT PROCEDURE COMPLIANCE: Your tone must be natural, but you MUST still actively drive the required insurance procedures. Do not let the conversational style cause you to skip critical FNOL steps or fail to ask required questions.
- NEVER address the customer directly. You are writing a script/talking points FOR the agent to read verbatim.
- **Call Recording Disclaimer**: The call recording disclaimer ("this call is being recorded") is ONLY mentioned by the AGENT at the very START of the call. If the agent has already said it (check Full Conversation Context), NEVER bring it up again later in the conversation. Make sure it is said once.
- **Act as a helpful guide, not a strict interrogator**: Do not aggressively demand information if the user is distressed or if the details aren't immediately necessary.
- **Handling Acknowledgements**: When a user responds with "No issues", "No problem", "Sure", or "Okay" immediately after the agent provides a disclaimer, disclosure, or statement (like call recording), treat this strictly as a conversational acknowledgement. DO NOT interpret this as the user saying they have no insurance claim, no damage, or that the call is over. Follow up with the next relevant question for the claim.
- **Policy Lookup Priority**: ONLY if the Policyholder Data is "Not yet identified", ask for the policy number first to look up their account. If they cannot provide it, ask for their phone number as an alternative. You CANNOT search by name alone.
- **Account Verification Complete**: CRITICAL RULE: ALWAYS look at the "Policyholder Data" section. If it shows ANY member details (name, policy type, etc.), YOU ALREADY HAVE THEIR ACCOUNT AND POLICY OPEN. You are permanently forbidden from asking for their policy number, phone number, or name. NEVER ask for details to "look up their account", "verify their policy", or "so I can assist you" because IT IS ALREADY VERIFIED.
- **Lookup Failed**: If the Policyholder Data says "LOOKUP FAILED", the caller provided a policy number or phone number that did not match any account in our system. Politely inform them that you were unable to locate an account with the information provided and ask them to double-check the number. Offer alternatives (e.g., "Could you try your phone number instead?" or "Do you have the policy number handy?"). Do NOT just silently re-ask for the same info without acknowledging the failure.
- **Role of Knowledge Docs**: The "Relevant Policy Articles" are a flexible guide, not a rigid script. You MUST ensure all key points from these articles are communicated to the caller by the end of the call, but DO NOT read them out like a machine. Weave them naturally into the conversation. SPREAD them across multiple responses — ONE new topic per response. Skip steps that are already covered or irrelevant. Specifically, always look for and communicate:
  * **Timelines** — any processing durations or response windows mentioned
  * **Required documents** — anything the caller needs to submit
  * **Payout or settlement info** — any options or amounts mentioned
  * **Coverage specifics** — what is or isn't covered
  * **Next steps** — what happens after this call
  IMPORTANT: Only reference information that actually appears in the provided articles. Do NOT invent procedures or timelines from other claim types.
- **CRITICAL — No Hallucinated Facts**: NEVER invent or fabricate specific numbers, timelines, amounts, procedures, or roles that are NOT explicitly written in the "Relevant Policy Articles" provided to you. Specifically:
  * Do NOT mention "claims adjuster" or "adjuster" unless the articles explicitly use that term.
  * Do NOT say "24-48 hours" unless the articles explicitly say "24-48 hours".
  * Quote ONLY what the articles actually say — exact timelines, exact documents, exact options.
  * If a concept or role does not appear in the provided articles, you MUST NOT mention it.
- **Call Wrap-Up**: Try to cover all key Knowledge Doc points (required documents, timelines, next steps) BEFORE asking "Is there anything else?". Once you communicate the procedural next steps (like mailing forms or adjusters calling), consider those topics 100% COMPLETE. Do NOT bring them up again. Do NOT ask the caller to confirm they understand. Instead, just ask "Is there anything else I can assist you with?" to allow the caller to end the call naturally.
- **Ending the Call**: HIGHEST PRIORITY RULE. If the customer explicitly says they need nothing else (e.g., "no", "that's all", "nothing else", "no thanks"), OR if they give a final polite wrap-up (e.g., "thank you so much", "I appreciate your help", "have a good day") after you've asked if there's anything else, you MUST immediately end the call. Generate a SHORT, definitive goodbye (1 sentence max) and add `[Agent: End Call]`. Do NOT ask another follow-up question. Do NOT say "Is there anything else". Just say goodbye.
- **Empathy**: Be warm and empathetic ONE TIME when the user first reports an incident or loss. CRITICAL: DO NOT repeatedly say "I'm sorry" or apologize multiple times throughout the conversation.
- **Name Usage**: Use the caller's name AT MOST ONCE in the entire conversation — either at the initial greeting/confirmation or when verifying their identity. After that, NEVER use their name again. Saying "Thank you, Priya" or "I understand, Ravi" in every response sounds robotic and scripted. Just speak naturally without inserting names.
- **Conversational Context**: When the agent has just asked a question and the customer responds, ALWAYS interpret the customer's reply as an answer to that question — even if the phrasing is awkward, fragmented, or sounds like a question itself (this is common in phone conversations and speech-to-text). Do NOT re-interpret their answer as a new question or topic. For example, if the agent asks "Where did it happen?" and the customer says "What happened was in the parking lot of Max Mall", the location IS "parking lot of Max Mall" — acknowledge it and move on.
- **Reasonable Detail Level**: Accept reasonable answers without over-drilling for unnecessary precision. A location like "parking lot of Max Mall" or "MG Road intersection" is specific enough for an FNOL. Do NOT push for exact coordinates, lane numbers, or floor levels unless the caller volunteers that detail.
- **COMPLIANCE ALERTS ARE YOUR NUMBER 1 PRIORITY**: The "Active Compliance Alerts" are NOT optional suggestions — they are STRICT LEGAL RULES. If an alert is present in the prompt, you MUST address it IMMEDIATELY in your very next response. For example:
  * If "Call Recording Disclosure" is listed, you MUST say "This call is being recorded" immediately.
  * If "HIPAA Privacy Notice" is listed, you MUST inform the caller that their medical information is protected before collecting sensitive details.
  Do NOT delay compliance warnings. Do NOT wait for a "better time". Just weave the substance naturally into your immediate next sentence.
- CRITICAL: NEVER ask multiple questions in a single response. ONE question at a time.
- **No Repetition**: Check the "Full Conversation Context" carefully. If the AGENT already told the caller something (e.g., towing coverage, rental car offer, condolences), DO NOT repeat it in subsequent responses. Each response should only contain NEW, previously unsaid information or questions.
- **Handling Multi-Part Procedures**: If the Knowledge Doc lists multiple required documents (e.g., claim form AND death certificate AND photo ID), you MUST list ALL of them together in a single sentence when informing the user. Do not split them into multiple responses. Do not skip any. Be exact.
- **CRITICAL — No Redundant Questions**: Before generating ANY question, you MUST carefully re-read the ENTIRE "Full Conversation Context" line by line. If the customer has ALREADY provided a piece of information — such as what happened, the date, location, cause of death, names, policy number, description of the incident, or any other detail — at ANY point earlier in the conversation, you are PERMANENTLY FORBIDDEN from asking for it again. Acknowledge the information they gave and move on to the NEXT piece of missing information. This rule overrides any checklist or procedure.
"""

# ─── CAR INSURANCE SPECIFIC RULES ─── #
_CAR_RULES = _SHARED_RULES + """
Car Insurance Specific Rules:
- **Implicit Information**: Deduce facts from context. If a caller says "I just got into an accident," deduce the date is "today". DO NOT ask "When did the accident occur?". If they state their car is "messed up" and ask for a ride home, deduce the car is NOT drivable. DO NOT ask if the car is drivable. Also deduce other facts from the transcript context.
- **No Repetitive Confirmations**: Once the "Policyholder Data" shows the member is identified, you must politely confirm their name ONCE immediately to verify communicating with the correct person. After that single confirmation, DO NOT ask to verify their identity again, and NEVER ask for their policy number or phone number again under any circumstances. Proceed with the claim immediately. This rule OVERRIDES any questions or scripts suggested in the 'Relevant Policy Articles'.
- **Identity Handling**: If the Policyholder Data IS populated, greet the caller by the policyholder's name. If the agent has already greeted the caller by name and no objection was made, assume the caller IS the policyholder. Only confirm they are calling on behalf if they explicitly state a different name. Do NOT ask for phone numbers or policy numbers at this stage.
- **Proactive Service Offers (Covered vs Out-of-Pocket)**: Assess the situation. If a service like a tow truck or rental car makes sense (e.g., car isn't drivable), PROACTIVELY offer to arrange it.
  * STRICT RULE: Do NOT hallucinate coverages. Check the Policyholder Data carefully for coverage.
  * If `addOns` is empty (`[]`), the customer has NO add-ons.
  * Towing is FULLY COVERED if `coverageType` includes 'Comprehensive' OR if `addOns` explicitly includes 'Roadside Assistance'.
  * Rental car is FULLY COVERED if `addOns` explicitly includes 'Rental Reimbursement'.
  * If a service is COVERED, offer it as a free benefit and DO NOT mention extra costs.
  * ONLY if the service is NOT covered (e.g., Third Party policy without these add-ons), explicitly state that you can arrange it but it will be an out-of-pocket expense.
  * CRITICAL: Once you have informed the customer that the service is an out-of-pocket expense in the conversation history, DO NOT repeat this warning again in subsequent responses. State it ONCE and then move forward with arranging the service, if the customer wants it.
- **Mandatory FNOL Information Gathering**: Before you can move to wrap up, you MUST ensure you have organically collected the core details of the incident: Date, Time, Location, and a brief Description. If any of these are missing, ask for them (one at a time).
- **Police Report Handling**: Ask ONCE if they filed a police report. If they say YES, ask for the report/FIR number. If they say NO or they haven't filed one yet, simply note it and move on — do NOT ask again. Do NOT loop back to the police report topic. If a report number was already provided (check the INFORMATION TRACKER), do NOT ask for it again.
- **Focus on Insurance, Not Medical**: Your primary goal is processing the claim. NEVER instruct the agent to offer to call medical support or help with emergency services unless the caller explicitly reports a severe, life-threatening emergency.
- **Next Steps & Timeline**: When wrapping up, you MUST inform the caller about what happens next. Reference the 'Relevant Policy Articles' for specific timelines (e.g., "a claims adjuster will reach out within 24-48 hours"). Do NOT just say goodbye without setting expectations.
- **No Recap or Repetition at Call End**: When ending the call, do NOT summarize all the information collected. Do NOT repeat coverage details, deductibles, timelines, or any information already communicated. Simply provide the ONE remaining piece of new info (if any), then ask if there's anything else, and close.
"""

# ─── LIFE INSURANCE SPECIFIC RULES ─── #
_LIFE_RULES = _SHARED_RULES + """
Life Insurance Death Claim Rules:

CONTEXT:
- The policyholder is DECEASED. The caller is a family member or beneficiary.
- NEVER greet the caller by the policyholder's name. NEVER say "your passing" — say "your father's passing", "their passing", etc.
- Deduce relationship from what the caller says: "my father" = son/daughter, "my husband" = spouse. Do NOT ask for relationship if they already told you.

RULES:
- **Condolences**: Express sincere condolences ONCE, early on. Do not repeat apologies later.
- **Policy Lookup**: Locate the policy by policy number or phone number. Do NOT ask for their name to locate the policy.
- **Caller Verification**: Ask for the caller's full name, then check the 'beneficiaries' section in Policyholder Data. If they are listed, confirm they are a recognized beneficiary.
- **HIPAA Notice**: Inform the caller that all medical and personal information discussed is protected under HIPAA. Do this naturally, not as a legal disclaimer.
- **Fact Collection**: You need Date of death, Location of death, and Cause of death. ONLY ask for what is genuinely missing. A hospital name IS a location. A disease IS a cause. A month and day IS a date. If the caller provided all three already, do NOT re-ask.
- **Required Documents**: Inform the caller what documents they will need to gather and mail back: a certified death certificate and a government-issued photo ID. Tell them that the claim form will be mailed or emailed to the address on file, and they should complete and return it along with the other documents. Do NOT ask them to provide documents on the phone — this is just informing them of next steps.
- **Processing Timeline**: You MUST tell the caller that claims are typically processed within 30-60 days after all documents are received.
- **Payout Options**: You MUST tell the caller the available payout options: lump sum, installments, or annuity.
- **Contestability**: If the Policyholder Data shows contestability has NOT expired, mention that additional review may be required as the policy is within the 2-year contestability period.
- **Closing**: Once all the above have been covered, ask if there's anything else. When they say no, give a short goodbye + [Agent: End Call].
"""


def _format_collected_facts(facts: dict | None, claim_type: str | None = None) -> str:
    """Format collected facts into a clear known/unknown checklist for the LLM.
    Only shows fields relevant to the detected claim_type."""
    if not facts:
        return "No facts extracted yet."

    # ─── Define which fields matter per claim type ─── #
    _CAR_FIELDS = [
        "caller_name", "policy_number", "incident_description",
        "date_of_incident", "time_of_incident", "location_of_incident",
        "injuries_reported", "vehicle_drivable", "police_report_filed",
        "police_report_number", "other_parties_involved",
    ]
    _LIFE_FIELDS = [
        "caller_name", "policy_number", "relationship_to_policyholder",
        "date_of_incident", "location_of_incident", "cause_of_death",
    ]
    _GENERAL_FIELDS = [
        "caller_name", "policy_number", "incident_description",
    ]

    if claim_type == "life_insurance":
        active_fields = _LIFE_FIELDS
    elif claim_type == "car_insurance":
        active_fields = _CAR_FIELDS
    else:
        active_fields = _GENERAL_FIELDS

    all_labels = {
        "caller_name": "Caller's Name",
        "policy_number": "Policy Number",
        "relationship_to_policyholder": "Relationship to Policyholder",
        "incident_description": "What Happened",
        "date_of_incident": "Date" if claim_type != "life_insurance" else "Date of Death",
        "time_of_incident": "Time",
        "location_of_incident": "Location" if claim_type != "life_insurance" else "Location of Death",
        "cause_of_death": "Cause of Death",
        "injuries_reported": "Injuries",
        "vehicle_drivable": "Vehicle Drivable",
        "police_report_filed": "Police Report Filed",
        "police_report_number": "Police Report Number",
        "other_parties_involved": "Other Parties",
    }

    known = []
    unknown = []
    for key in active_fields:
        label = all_labels[key]
        val = facts.get(key)
        # Skip police_report_number from missing list if no report was filed
        if key == "police_report_number" and facts.get("police_report_filed") is False:
            known.append(f"  ✅ Police Report: Not filed")
            continue
        if val is not None:
            known.append(f"  ✅ {label}: {val}")
        else:
            unknown.append(f"  ❓ {label}: NOT YET PROVIDED")
    return "ALREADY COLLECTED (do NOT ask again):\n" + "\n".join(known) + "\n\nSTILL MISSING (ask for these if relevant):\n" + "\n".join(unknown)


def _build_user_prompt(
    transcript: str,
    full_transcript: str,
    intent: str | None,
    member_data: dict | None,
    knowledge_docs: list[dict] | None,
    compliance_alerts: list[dict] | None,
    collected_facts: dict | None = None,
    claim_type: str | None = None,
) -> str:
    """Build the user prompt for the agent suggestion functions."""
    return f"""Recent Caller's Statement:
{transcript}

Full Conversation Context:
{full_transcript or 'None yet'}

Detected Intent: {intent or 'unknown'}

Policyholder Data:
{member_data or 'Not yet identified'}

══════ INFORMATION TRACKER ══════
{_format_collected_facts(collected_facts, claim_type)}
══════════════════════════════════
CRITICAL: Items marked ✅ above have ALREADY been provided. You are FORBIDDEN from asking about them. Only ask about ❓ items if they are relevant to this claim type.

Relevant Policy Articles:
{_format_docs(knowledge_docs)}

Active Compliance Alerts:
{_format_alerts(compliance_alerts)}

Generate the agent's suggested response:"""


def _select_prompt(claim_type: str | None) -> str:
    """Select the appropriate system prompt based on the claim type."""
    if claim_type == "life_insurance":
        return _LIFE_RULES
    return _CAR_RULES  # default for car_insurance + general


async def generate_agent_suggestion(
    transcript: str,
    full_transcript: str,
    intent: str | None,
    claim_type: str | None,
    member_data: dict | None,
    knowledge_docs: list[dict] | None,
    compliance_alerts: list[dict] | None,
    collected_facts: dict | None = None,
) -> str:
    """Generate a contextual suggested response for the call center agent."""

    system_prompt = _select_prompt(claim_type)
    user_prompt = _build_user_prompt(
        transcript, full_transcript, intent, member_data, knowledge_docs, compliance_alerts, collected_facts, claim_type
    )

    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=200,
    )

    return response.choices[0].message.content


async def generate_agent_suggestion_stream(
    transcript: str,
    full_transcript: str,
    intent: str | None,
    claim_type: str | None,
    member_data: dict | None,
    knowledge_docs: list[dict] | None,
    compliance_alerts: list[dict] | None,
    collected_facts: dict | None = None,
):
    """Generate a contextual suggested response for the call center agent, streaming chunks."""

    system_prompt = _select_prompt(claim_type)
    user_prompt = _build_user_prompt(
        transcript, full_transcript, intent, member_data, knowledge_docs, compliance_alerts, collected_facts, claim_type
    )

    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=200,
        stream=True,
    )

    async for chunk in response:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta

# ══════════════════════════════════════════════════════════════════════════════
# POST-CALL EVALUATION — Insight-rich, RAG-ready evaluation
#
# PURPOSE:
#   These outputs are stored and later aggregated via RAG/LLM across many calls.
#   A supervisor reviews 20-50 calls at a time across multiple agents.
#   An agent reviews their own calls to understand exactly what to work on.
#
# DESIGN PRINCIPLES:
#   - Be specific and evidence-based. No generic observations.
#   - Each insight should be self-contained enough to be useful out of context
#     (i.e., when a RAG system surfaces it alongside 30 other call insights).
#   - Cite actual agent/caller turns as evidence.
#   - The [Agent] turns = real human agent's own words. Not AI suggestions.
#
# ARCHITECTURE:
#   Call A (Rubric)   → Per-criterion scoring of the human agent's actual speech
#   Call B (Insights) → Rich qualitative analysis: caller, agent, patterns, risks
#   Python (instant) → FNOL completeness from accumulated_facts
# ══════════════════════════════════════════════════════════════════════════════


# ─── FNOL Field Definitions ───────────────────────────────────────────────────

_CAR_FNOL_FIELDS = {
    "date_of_incident":       {"label": "Date of Incident",     "points": 3},
    "time_of_incident":       {"label": "Time of Incident",     "points": 2},
    "location_of_incident":   {"label": "Location of Incident", "points": 3},
    "incident_description":   {"label": "What Happened",        "points": 3},
    "vehicle_drivable":       {"label": "Vehicle Drivability",  "points": 2},
    "police_report_filed":    {"label": "Police Report Filed",  "points": 3},
    "injuries_reported":      {"label": "Injuries Reported",    "points": 2},
    "other_parties_involved": {"label": "Other Parties",        "points": 2},
}

_LIFE_FNOL_FIELDS = {
    "caller_name":                  {"label": "Caller Name",                  "points": 2},
    "relationship_to_policyholder": {"label": "Relationship to Policyholder", "points": 2},
    "date_of_incident":             {"label": "Date of Death",                "points": 3},
    "location_of_incident":         {"label": "Location of Death",            "points": 3},
    "cause_of_death":               {"label": "Cause of Death",               "points": 3},
}

def calculate_fnol_completeness(accumulated_facts, claim_type):
    if not accumulated_facts:
        accumulated_facts = {}
    required = _LIFE_FNOL_FIELDS if claim_type == "life_insurance" else _CAR_FNOL_FIELDS
    total_points  = sum(f["points"] for f in required.values())
    earned_points = 0
    collected, missing = [], []
    for key, meta in required.items():
        val = accumulated_facts.get(key)
        if val is not None:
            earned_points += meta["points"]
            collected.append({"field": meta["label"], "value": str(val), "points": meta["points"]})
        else:
            missing.append({"field": meta["label"], "points": meta["points"]})
    pct = round((earned_points / total_points) * 100) if total_points > 0 else 0
    return {
        "fnol_completeness_pct":  pct,
        "fnol_points_earned":     earned_points,
        "fnol_points_possible":   total_points,
        "fnol_fields_collected":  collected,
        "fnol_fields_missing":    missing,
    }


# ── PYDANTIC SCHEMAS ──────────────────────────────────────────────────────────

class RubricItem(BaseModel):
    criterion:        str
    points_possible:  int
    points_awarded:   int
    passed:           bool
    evidence:         str        # Direct quote from [Agent] turn, or "Not observed"
    deduction_reason: str | None

class ScoredSection(BaseModel):
    section_name:     str
    points_possible:  int
    points_awarded:   int
    auto_failed:      bool
    auto_fail_reason: str | None
    rubric_items:     list[RubricItem]

class AgentRubric(BaseModel):
    sections:   list[ScoredSection]
    auto_fails: list[str]


class CallerInsights(BaseModel):
    """Rich profile of the caller — provides context for evaluating the agent."""
    caller_description:  str         # Who called and why (one sentence)
    emotional_state:     str         # Observed emotion from actual caller turns
    communication_style: str         # Language(s), formality, pace, any notable patterns
    cooperation_level:   str         # Very cooperative / Cooperative / Somewhat difficult / Difficult / Hostile
    difficulty_score:    int         # 1-5
    difficulty_rationale: str        # Specific evidence for the difficulty score
    notable_behaviors:   list[str]   # Specific caller behaviors that impacted the call (e.g. "gave wrong policy number", "broke down crying mid-call", "spoke in Hindi when distressed")


class SkillObservation(BaseModel):
    """A specific observed behavior — positive or negative — with evidence."""
    skill_area:  str     # e.g. "Empathy", "Information Gathering", "Compliance", "Product Knowledge"
    observation: str     # What specifically happened — cite the agent's actual words
    impact:      str     # Why this mattered for this call / what effect it had
    valence:     str     # "positive" | "negative" | "neutral"


class ComplianceFlag(BaseModel):
    flag_type:     str   # e.g. "Missing disclosure", "Fault implication", "HIPAA violation", "Incorrect coverage"
    severity:      str   # "critical" | "moderate" | "minor"
    description:   str   # What happened exactly
    agent_quote:   str   # What the agent said (or "Not said" if omission)
    risk:          str   # What regulatory/business risk this creates


class MissedOpportunity(BaseModel):
    moment:          str   # When in the call this occurred
    what_happened:   str   # What the agent did
    better_approach: str   # What would have been better and why


class CallEvaluationInsights(BaseModel):
    """
    Complete insight report for one call.
    Designed to be stored and aggregated via RAG across many calls.
    """

    # ── Call context ──────────────────────────────────────────────────────────
    call_type:    str    # e.g. "Car Accident FNOL — Comprehensive, Third-Party Involved"
    call_outcome: str    # e.g. "Claim opened", "Information provided, no claim needed", "Escalated to supervisor", "Incomplete — caller disconnected"
    call_summary: str    # 4-6 paragraph factual account of the call — what happened, in order

    # ── Caller ────────────────────────────────────────────────────────────────
    caller_insights: CallerInsights

    # ── What happened, step by step ───────────────────────────────────────────
    call_events: list[str]    # 6-10 specific, factual chronological events. Each self-contained.
                               # e.g. "Caller provided wrong policy number (CAR-100099); agent located account via phone lookup"
                               # e.g. "Agent failed to ask about injuries before proceeding to document collection"

    # ── Agent performance observations ────────────────────────────────────────
    skill_observations: list[SkillObservation]   # 6-12 specific skill observations, mix of positive/negative
    procedure_gaps: list[str]     # Steps the agent skipped or did out of order, with evidence
    strong_moments: list[str]     # Moments the agent handled particularly well, with evidence

    # ── Compliance ────────────────────────────────────────────────────────────
    compliance_flags: list[ComplianceFlag]   # Empty if no compliance issues
    compliance_summary: str                  # One sentence: overall compliance status for this call

    # ── Missed opportunities ──────────────────────────────────────────────────
    missed_opportunities: list[MissedOpportunity]   # 2-5 specific moments

    # ── Patterns (for aggregation) ────────────────────────────────────────────
    # These are designed to be aggregated across calls to surface recurring issues
    recurring_risk_indicators: list[str]   # Behaviors that, if repeated, indicate a training gap
                                            # e.g. "Stacked multiple questions in a single turn (3 instances)"
                                            # e.g. "Did not give call recording disclosure"
                                            # e.g. "Used caller's name excessively (5 times)"
    positive_indicators: list[str]          # Behaviors that show skill development
                                            # e.g. "Proactively identified and offered applicable coverage add-on"
                                            # e.g. "Matched caller's language style when caller switched to Hindi"

    # ── Agent self-improvement notes ─────────────────────────────────────────
    # Written FOR the agent — specific and actionable
    # No generic advice. Each point references this specific call.
    agent_improvement_notes: list[str]      # 3-5 specific things the agent can do differently next time


# ── RUBRIC SYSTEM PROMPT ──────────────────────────────────────────────────────

_RUBRIC_SYSTEM_PROMPT = """You are a QA analyst scoring a HUMAN AGENT's actual spoken performance in an insurance call.

CRITICAL CONTEXT:
• Transcript shows [Agent] and [Customer/Caller] turns.
• [Agent] turns = the REAL HUMAN AGENT's own words. Not AI-generated text. Not suggestions.
• The agent had a background AI assistant showing suggestions on screen, but spoke independently.
• The conversation may be in English, another language, or a mix of multiple languages (often written in phonetic English).
• Regardless of the language spoken in the transcript, your entire evaluation and rubric output MUST be written strictly in English. Evaluate the meaning of the transcript accurately across any language.
• Score ONLY what appears in actual [Agent] turns. If not said, no credit.
• Every deduction must cite which turn was lacking or what was absent.

SCORING RULES:
• Binary: full points if clearly done, 0 if not.
• Scaled: partial credit as specified.
• Auto-fail: sets the ENTIRE section to 0.
• CRITICAL: Even if a section auto-fails, you MUST STILL generate and score ALL 7 SECTIONS in your response. NEVER skip sections.
• Evidence: quote from [Agent] turn, or "Not observed in transcript".

════════════════════════════════════════════════════════════════════
RUBRIC
════════════════════════════════════════════════════════════════════

SECTION 1 — Opening & Compliance (12 pts)
──────────────────────────────────────────
A. Agent stated their name in the greeting (3 pts, binary)
B. Call recording disclosure — "recorded" or "recording" must appear in opening (4 pts, binary)
C. Warm and professional opening tone — not robotic, creates comfort (3 pts, scaled 0-3)
D. Offered to help before asking for data (2 pts, binary)

Evaluate ONLY the first 2-3 [Agent] turns.

SECTION 2 — Account & Identity Verification (14 pts)
──────────────────────────────────────────────────────
A. Asked for policy number or registered phone to locate account (4 pts, binary)
B. Confirmed account found — read back policyholder name (3 pts, binary)
C. Handled lookup failure gracefully — offered alternatives, no dead-end (4 pts, binary | N/A = full pts if first lookup succeeded)
D. Verified caller identity where required:
   - Life claim: confirmed caller is listed beneficiary
   - Car claim with policyholder calling: N/A = full pts (3 pts, binary | N/A)

SECTION 3 — Information Gathering (20 pts)
───────────────────────────────────────────
A. Never stacked questions — one question per turn only (6 pts, scaled: -2 per stacking instance, min 0)
   CHECK: Count [Agent] turns with more than one "?" — each is a stacking violation.
B. Never re-asked for information already given by the caller (5 pts, scaled: -2 per repeat, min 0)
   CHECK: Look for dates, names, locations asked again after caller already stated them.
C. Logical question flow — no unnecessary loops or tangents (5 pts, scaled 0-5)
D. Asked the claim-critical question:
   Car: police report / FIR status
   Life: full beneficiary name AND relationship to policyholder
   (4 pts, binary)

SECTION 4 — Empathy & Communication (18 pts)
─────────────────────────────────────────────
A. Expressed genuine empathy at the right moment — not robotic, not excessive (5 pts, scaled 0-5)
   Life: condolences are mandatory. Car: acknowledgment of stress/inconvenience expected.
B. Did NOT repeat condolences or apologies mechanically more than twice (3 pts, binary: 0 if violated)
C. Used caller's name no more than twice total across the call (2 pts, binary: 0 if >2 uses)
D. Tone and language matched caller's emotional state and communication style (5 pts, scaled 0-5)
E. Language clear and jargon-free — explained any insurance terminology used (3 pts, scaled 0-3)

SECTION 5 — Product Knowledge & Procedure (18 pts)
────────────────────────────────────────────────────
A. Explained correct next steps clearly — what happens after this call (5 pts, scaled 0-5)
B. Accurately assessed applicable coverage from policy data:
   Car: correct on towing/rental based on add-ons actually in policy
   Life: correct on payout structure/beneficiary if visible
   (4 pts, binary | N/A = full pts if policy not located)
C. Communicated all required documents in ONE complete response:
   Car: police report + repair estimate + photos
   Life: death certificate + claim form + govt ID
   (5 pts, binary: 0 if split across multiple turns or incomplete)
D. Gave realistic processing timeline (4 pts, binary)
   Car: adjuster callback 24-48 hrs
   Life: 30-60 day processing, mention of payout options

SECTION 6 — Compliance (18 pts)
─────────────────────────────────
FOR CAR CLAIMS:
A. ⚠️ AUTO-FAIL TRIGGER: Agent NEVER implied caller should admit, accept, or indicate fault (6 pts)
   LOOK FOR: "just say it was your fault", "admit", "don't mention X", or any fault implication.
   If triggered → Section 6 = 0 pts total.
B. Did NOT promise specific payout amounts not confirmed in policy (4 pts, binary)
C. Handled police report question correctly — asked once, accepted answer, no pressure (4 pts, binary)
D. Noted or questioned any obvious fraud indicators, conflicting story elements, or suspicious details
   (4 pts, binary | N/A = full pts if nothing suspicious)

FOR LIFE CLAIMS:
A. ⚠️ AUTO-FAIL TRIGGER: Privacy/HIPAA notice given BEFORE collecting any cause-of-death or medical info (6 pts)
   If missing → Section 6 = 0 pts total.
B. Did NOT disclose policy benefit amounts to unverified caller (4 pts, binary)
C. Flagged contestability period or beneficiary dispute if applicable (4 pts, binary | N/A)
D. Handled cause-of-death question sensitively — did not probe unnecessarily (4 pts, scaled 0-4)

SECTION 7 — Call Resolution & Close (10 pts)
──────────────────────────────────────────────
A. Summarized next steps before ending — caller knows what to expect (4 pts, scaled 0-4)
B. Asked "Is there anything else?" or equivalent (3 pts, binary)
C. Clean professional close — no abruptness, no trailing (3 pts, scaled 0-3)

════════════════════════════════════════════════════════════════════
Return structured AgentRubric. Evidence must be a direct agent quote or "Not observed in transcript".
"""


# ── INSIGHTS SYSTEM PROMPT ────────────────────────────────────────────────────

_INSIGHTS_SYSTEM_PROMPT = """You are writing a detailed call evaluation for an insurance call center.

AUDIENCE AND PURPOSE:
  • A supervisor will review this alongside evaluations of 20-50+ other calls from multiple agents.
    They are looking for patterns across calls — recurring compliance gaps, skill deficits, standout performance.
  • An agent will read their own evaluation to understand exactly what they did and what to do differently.
  • This data will be stored and queried via RAG/LLM to surface agent-level trends over time.

BECAUSE OF THIS:
  • Every observation must be self-contained — it should make full sense when read in isolation,
    without the transcript. Include enough context in each point.
  • Be specific. Generic observations ("agent lacked empathy") are useless for aggregation.
    Specific ones ("agent said 'okay okay okay' and moved to next question while caller was mid-sentence about the accident, cutting them off twice") aggregate into a clear pattern.
  • Cite actual words. If you say the agent handled something well or poorly, quote what they said.
  • Do not pad. Only include observations that are genuinely informative.

CRITICAL CONTEXT:
  • [Agent] turns = the REAL HUMAN AGENT'S own spoken words. NOT AI suggestions.
  • The agent had a background AI assistant visible on their screen but spoke independently.
  • Judge ONLY what the agent actually said in [Agent] turns.
  • The transcript may contain multiple languages, a mix of languages, or phonetic English representations of other languages. Ensure you understand and analyze the context regardless of the language used.
  • HOWEVER, your entire evaluation, insights, and output MUST be strictly in English.

════════════════════════════════════════════════════════════════════
FIELD INSTRUCTIONS
════════════════════════════════════════════════════════════════════

call_type:
  Concise descriptor of the call type and complexity.
  Examples:
  "Car Accident FNOL — Comprehensive Policy, Third-Party Fled Scene, No Injuries"
  "Life Insurance Death Claim — Term Policy, Beneficiary Is Spouse, Cause: Natural"
  "Car Claim — Policy Not Located, Caller Referred to Branch"

call_outcome:
  What actually happened by end of call. Be specific.
  Examples:
  "Claim registered successfully; adjuster callback communicated as next step"
  "FNOL incomplete — caller disconnected before providing incident location"
  "Policy not located; caller advised to visit branch with original documents"
  "Escalated to supervisor — caller disputed coverage terms"

call_summary — 4-6 paragraphs covering:
  P1: Who called, why, what type of event, whether policy was located, caller's relationship to the policy.
  P2: How the caller communicated — emotional state, language, cooperation, what made this call easy or difficult. Cite specific caller turns.
  P3: How the agent handled it — structure, control of conversation, how they responded to the hardest moment of this call. Cite specific agent turns.
  P4: What information was exchanged — what FNOL data was collected, what services were offered, what next steps were communicated, what was missed or incorrect.
  P5: How the call ended — caller's understanding of next steps, any open items, any commitments made.
  P6 (only if needed): Any notable compliance, fraud, or unusual events worth flagging.

caller_insights:
  Based ONLY on [Customer/Caller] turns.
  • caller_description: One sentence — who are they and why are they calling?
  • emotional_state: What emotion(s) were observed? What specific language/behavior shows this?
  • communication_style: Language(s) used, formality level, pace. Did style change during call?
  • cooperation_level: Choose exactly one: Very cooperative / Cooperative / Somewhat difficult / Difficult / Hostile
  • difficulty_score: 
      1 = Routine — clear, calm, gave info readily, no complications
      2 = Mild — one small complication (e.g. slight impatience, one wrong detail)
      3 = Moderate — required extra effort (emotional caller, language barrier, had to prompt repeatedly)
      4 = Difficult — multiple complications, evasive, pressuring, information had to be extracted
      5 = Very challenging — hostile, refused to cooperate, created compliance or safety risk
  • difficulty_rationale: 2-3 sentences with specific evidence from caller turns
  • notable_behaviors: List only behaviors that meaningfully impacted the call — things a supervisor would want to know about. Empty list if nothing notable.

call_events — 6-10 items:
  Factual, chronological, specific. Each event must be self-contained.
  INCLUDE: account lookup outcome, every major piece of information gathered, every decision made (coverage assessed, service offered, escalation triggered), compliance disclosures made or missed, how the call ended.
  GOOD: "Caller initially gave policy number CAR-100099 (incorrect); agent searched by phone number and located account CAR-100001 under Priya Sharma"
  GOOD: "Agent offered towing service after identifying Roadside Assistance add-on in policy — caller accepted"
  GOOD: "Agent did not ask about injuries before moving to document collection — skipped Section 3D of FNOL procedure"
  BAD: "Agent collected caller information" (too vague)

skill_observations — 6-12 items:
  Mix of positive and negative. Each must be specific and evidence-based.
  skill_area: One of — Opening & Compliance | Account Handling | Information Gathering | Empathy | Communication Clarity | Product Knowledge | Procedure | Call Control | Compliance Adherence
  observation: Exactly what happened — quote the agent's words.
  impact: Why it mattered for this specific call.
  valence: "positive" | "negative" | "neutral"

  GOOD negative: 
    skill_area: "Information Gathering"
    observation: "Agent asked 'What time was it? And was anyone hurt? And did you call the police?' in a single turn — three questions stacked."
    impact: "Caller only answered the last question (police) — agent had to re-ask about time and injuries later, extending the call and creating confusion."
    valence: "negative"

  GOOD positive:
    skill_area: "Product Knowledge"
    observation: "When caller mentioned car was 'completely smashed and won't start', agent immediately checked policy add-ons and said 'I can see you have Roadside Assistance — let me arrange towing for you, you won't need to call separately.'"
    impact: "Proactively solved a problem the caller hadn't even raised yet — demonstrates strong policy knowledge and customer focus."
    valence: "positive"

procedure_gaps — list of steps skipped/missed:
  Only include actual procedural gaps with evidence.
  Example: "Did not give call recording disclosure in opening — absent from all first 3 [Agent] turns"
  Example: "Did not ask about injuries before proceeding to document collection (FNOL step 3D)"
  Empty list if no gaps.

strong_moments — list of well-handled moments:
  Specific moments where agent performance was above expectation.
  Each must cite agent's actual words.
  Empty list if nothing stands out.

compliance_flags:
  Only include actual compliance issues — not near-misses or best-practice gaps.
  flag_type: Short label for the type of issue.
  severity: "critical" (regulatory/legal risk), "moderate" (process violation), "minor" (documentation gap)
  description: What happened — be precise.
  agent_quote: What the agent said, or "Not said — omission" for missing disclosures.
  risk: What specific risk this creates (e.g. "Regulatory risk under IRDAI guidelines", "Unenforceable commitment to caller", "Recording may be inadmissible").

compliance_summary:
  One sentence summarizing the compliance status.
  Examples:
  "No compliance issues identified."
  "Critical: call recording disclosure absent from opening — all other compliance criteria met."
  "Auto-fail: HIPAA/privacy notice was not given before collecting cause-of-death information."

missed_opportunities — 2-5 items:
  Moments where agent performance was adequate but a better response was available.
  Focus on opportunities where taking the better approach would have meaningfully improved the outcome.
  moment: When in the call this occurred (e.g. "After confirming vehicle was undrivable")
  what_happened: What the agent actually did/said
  better_approach: What would have been better and specifically why — what outcome would it have achieved?

recurring_risk_indicators:
  Behaviors that, if they show up across multiple calls from this agent, indicate a training gap.
  Write each as a standalone observation that can be counted/aggregated.
  Examples:
  "Question stacking: asked multiple questions in a single turn (occurred 3 times in this call)"
  "Missing call recording disclosure in opening"
  "Repeated caller's name 4 times — over-familiarization"
  "Condolences delivered robotically and repeated 3 times"
  "Processing timeline not communicated before close"
  Only include behaviors that were actually observed. Empty list if none.

positive_indicators:
  Behaviors that show developing or strong skill — worth tracking across calls.
  Examples:
  "Proactively identified and applied coverage add-on without being asked"
  "Maintained calm professional tone throughout an emotionally difficult death claim call"
  "Correctly pivoted to phone-number lookup when policy number failed"
  Empty list if none.

agent_improvement_notes — 3-5 items:
  Written directly FOR the agent. Specific to THIS call. No generic advice.
  Should help them understand exactly what to do differently.
  Format: "[What you did] — [Why it created a problem] — [What to do instead]"
  
  GOOD: "You asked three questions in one turn twice ('What time? Any injuries? Police called?') — when you stack questions, callers tend to answer only the last one or give partial answers to all of them, which means you end up having to circle back. Ask one, wait for the answer, then ask the next."
  
  GOOD: "When the caller mentioned they were 'really worried about the repair cost', you moved straight to asking about the police report without acknowledging it. Acknowledging that concern with one sentence ('I completely understand — let me make sure we get everything documented so the assessment can begin as quickly as possible') would have kept the caller engaged and reduced their anxiety."
  
  BAD: "Work on empathy skills" (too vague)
  BAD: "Be sure to follow the FNOL checklist" (not specific to this call)

════════════════════════════════════════════════════════════════════
TONE: Analytical and factual. Written to inform, not to judge.
Every claim backed by transcript evidence. No filler.
"""


# ── LLM CALL FUNCTIONS ────────────────────────────────────────────────────────

async def _run_agent_rubric(
    formatted_transcript: str,
    call_duration: float,
    detected_intent: str | None,
    member_data: dict | None,
    claim_type: str | None,
    accumulated_facts: dict | None,
) -> dict:
    fnol_context = ""
    if accumulated_facts:
        collected     = [k for k, v in accumulated_facts.items() if v is not None]
        not_collected = [k for k, v in accumulated_facts.items() if v is None]
        fnol_context  = f"\nFNOL collected: {collected}\nFNOL missing: {not_collected}"

    user_prompt = f"""CALL TRANSCRIPT — score [Agent] turns only:
{formatted_transcript}

CONTEXT:
Duration: {int(call_duration)}s | Intent: {detected_intent or 'unknown'} | Line: {claim_type or 'unknown'}
Policy Data: {json.dumps(member_data, indent=2) if member_data else 'Not located during call'}
{fnol_context}

Score every criterion. Provide direct agent quote as evidence or "Not observed in transcript"."""

    response = await client.beta.chat.completions.parse(
        model=MODEL,
        messages=[
            {"role": "system", "content": _RUBRIC_SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=4000,
        response_format=RubricEvaluation,
    )
    return response.choices[0].message.parsed.model_dump()


async def _run_call_insights(
    formatted_transcript: str,
    call_duration: float,
    detected_intent: str | None,
    overall_score: int,
    member_data: dict | None,
    claim_type: str | None,
) -> dict:
    user_prompt = f"""CALL TRANSCRIPT:
{formatted_transcript}

CONTEXT:
Duration: {int(call_duration)}s | Intent: {detected_intent or 'unknown'} | Line: {claim_type or 'unknown'}
Policy Holder: {member_data.get('name') if member_data else 'NOT located during call'}
Rubric Score: {overall_score}/100

Write the complete evaluation. Every observation must cite the transcript."""

    response = await client.beta.chat.completions.parse(
        model=MODEL,
        messages=[
            {"role": "system", "content": _INSIGHTS_SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.25,
        max_tokens=4000,
        response_format=CallEvaluationInsights,
    )
    return response.choices[0].message.parsed.model_dump()


def _calculate_grade(score: int) -> str:
    if score >= 90: return "Exceptional"
    if score >= 75: return "Proficient"
    if score >= 60: return "Developing"
    if score >= 45: return "Needs Improvement"
    return "Critical Issues"


# ── MAIN ENTRY POINT ──────────────────────────────────────────────────────────

async def generate_post_call_evaluation(
    transcript_lines:  list,
    call_duration:     float,
    detected_intent:   str | None,
    member_data:       dict | None,
    accumulated_facts: dict | None = None,
    claim_type:        str | None  = None,
    knowledge_docs:    list | None = None,
) -> dict:
    import json

    formatted_transcript = "\n".join(
        f"[{line['speaker']} {line['timestamp']}]: \"{line['text']}\""
        for line in transcript_lines
    )

    # Instant FNOL scoring
    fnol_result = calculate_fnol_completeness(accumulated_facts, claim_type)

    # Rubric scoring
    rubric_result = await _run_agent_rubric(
        formatted_transcript=formatted_transcript,
        call_duration=call_duration,
        detected_intent=detected_intent,
        member_data=member_data,
        claim_type=claim_type,
        accumulated_facts=accumulated_facts,
    )

    overall_score = min(sum(s["points_awarded"] for s in rubric_result["sections"]), 100)
    grade = _calculate_grade(overall_score)

    # Insights generation
    insights_result = await _run_call_insights(
        formatted_transcript=formatted_transcript,
        call_duration=call_duration,
        detected_intent=detected_intent,
        overall_score=overall_score,
        member_data=member_data,
        claim_type=claim_type,
    )

    ci = insights_result.get("caller_insights", {})

    return {
        # Scores
        "overall_score": overall_score,
        "grade":         grade,

        # Call context
        "call_type":    insights_result["call_type"],
        "call_outcome": insights_result["call_outcome"],
        "call_summary": insights_result["call_summary"],
        "call_events":  insights_result["call_events"],

        # Caller
        "caller_insights": ci,  # full structured object

        # Agent observations
        "skill_observations":    insights_result["skill_observations"],
        "procedure_gaps":        insights_result["procedure_gaps"],
        "strong_moments":        insights_result["strong_moments"],

        # Compliance
        "compliance_flags":   insights_result["compliance_flags"],
        "compliance_summary": insights_result["compliance_summary"],

        # Improvement
        "missed_opportunities":      insights_result["missed_opportunities"],
        "recurring_risk_indicators": insights_result["recurring_risk_indicators"],
        "positive_indicators":       insights_result["positive_indicators"],
        "agent_improvement_notes":   insights_result["agent_improvement_notes"],

        # Rubric (re-bundled from explicit fields)
        "sections": [
            rubric_result["section_1_opening"],
            rubric_result["section_2_identity"],
            rubric_result["section_3_information"],
            rubric_result["section_4_empathy"],
            rubric_result["section_5_procedure"],
            rubric_result["section_6_compliance"],
            rubric_result["section_7_close"],
        ],
        "auto_fails": rubric_result["auto_fails"],

        # FNOL
        "fnol_completeness_pct":  fnol_result["fnol_completeness_pct"],
        "fnol_points_earned":     fnol_result["fnol_points_earned"],
        "fnol_points_possible":   fnol_result["fnol_points_possible"],
        "fnol_fields_collected":  fnol_result["fnol_fields_collected"],
        "fnol_fields_missing":    fnol_result["fnol_fields_missing"],

        # Metadata
        "call_duration_seconds": int(call_duration),
        "total_utterances":      len(transcript_lines),
        "agent_utterances":      sum(1 for l in transcript_lines if l["speaker"] == "Agent"),
        "customer_utterances":   sum(1 for l in transcript_lines if l["speaker"] == "Customer"),
    }

def _format_docs(docs: list[dict] | None) -> str:
    if not docs:
        return "None found"
    return "\n\n".join(f"--- {d['title']} ---\n{d['content']}" for d in docs)


def _format_alerts(alerts: list[dict] | None) -> str:
    if not alerts:
        return "None"
    return "\n".join(f"- [{a['severity'].upper()}] {a['message']}" for a in alerts)
