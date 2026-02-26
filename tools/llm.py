# tools/llm.py — OpenAI LLM utilities for Insurance FNOL + Post-Call Evaluation

import os
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


class ScoreDetail(BaseModel):
    score: int
    feedback: str


class EvaluationScores(BaseModel):
    empathy_and_tone: ScoreDetail
    information_gathering: ScoreDetail
    compliance_adherence: ScoreDetail
    process_knowledge: ScoreDetail
    resolution_and_next_steps: ScoreDetail


class PostCallEvaluation(BaseModel):
    overall_score: int
    call_summary: str
    claim_type_detected: str
    scores: EvaluationScores
    strengths: list[str]
    improvements: list[str]
    compliance_violations: list[str]
    coaching_notes: str


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
# ENTITY EXTRACTION — Structured Output
# ═══════════════════════════════════════════════════════

async def extract_entities(transcript: str) -> dict:
    """Use LLM to extract names, phone numbers, and policy IDs from transcript."""
    
    system_prompt = """You are an insurance entity extraction system.
Analyze the caller's statement and extract the following if present:
- "policy_id": formatted as CAR-XXXXXX or LIFE-XXXXXX (fix spacing/hyphens if spoken like "car 12345").
- "name": full or partial name of the caller.
- "phone": phone number referenced. Ensure you capture full or even partial phone numbers spoken.
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
- The transcript comes from speech-to-text and may contain spelling errors, phonetic misspellings, or garbled text.
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
- NEVER address the customer directly. You are writing a script/talking points FOR the agent to read verbatim.
- **Call Recording Disclaimer**: The call recording disclaimer ("this call is being recorded") is ONLY mentioned by the AGENT at the very START of the call. If the agent has already said it (check Full Conversation Context), NEVER bring it up again later in the conversation. Make sure it is said once.
- **Act as a helpful guide, not a strict interrogator**: Do not aggressively demand information if the user is distressed or if the details aren't immediately necessary.
- **Handling Acknowledgements**: When a user responds with "No issues", "No problem", "Sure", or "Okay" immediately after the agent provides a disclaimer, disclosure, or statement (like call recording), treat this strictly as a conversational acknowledgement. DO NOT interpret this as the user saying they have no insurance claim, no damage, or that the call is over. Follow up with the next relevant question for the claim.
- **Policy Lookup Priority**: ONLY if the Policyholder Data is "Not yet identified", ask for the policy number first to look up their account. If they cannot provide it, ask for their phone number as an alternative. You CANNOT search by name alone.
- **Account Verification Complete**: CRITICAL RULE: ALWAYS look at the "Policyholder Data" section. If it shows ANY member details (name, policy type, etc.), YOU ALREADY HAVE THEIR ACCOUNT AND POLICY OPEN. You are permanently forbidden from asking for their policy number, phone number, or name. NEVER ask for details to "look up their account", "verify their policy", or "so I can assist you" because IT IS ALREADY VERIFIED.
- **Lookup Failed**: If the Policyholder Data says "LOOKUP FAILED", the caller provided a policy number or phone number that did not match any account in our system. Politely inform them that you were unable to locate an account with the information provided and ask them to double-check the number. Offer alternatives (e.g., "Could you try your phone number instead?" or "Do you have the policy number handy?"). Do NOT just silently re-ask for the same info without acknowledging the failure.
- **Role of Knowledge Docs**: The "Relevant Policy Articles" are your primary reference for facts and procedures. You MUST ensure all key points from these articles are communicated to the caller by the end of the call, SPREAD across multiple responses — ONE new topic per response. Skip steps that are already covered or irrelevant. Specifically, always look for and communicate:
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
- **Call Wrap-Up**: Try to cover all key Knowledge Doc points (required documents, timelines, next steps) BEFORE asking "Is there anything else?". But once you've asked and the customer is done, END the call — do NOT continue with more info.
- **Ending the Call**: HIGHEST PRIORITY RULE — overrides everything else. If the customer says they need nothing else (e.g., "no", "that's all", "thank you", "nothing else", "I'm good"), you MUST immediately generate a SHORT, definitive goodbye (1 sentence max) and add `[Agent: End Call]`. Do NOT ask another follow-up question, do NOT provide more information, do NOT say "Is there anything else". Just say goodbye. Do NOT summarize or repeat any facts or details already discussed — just a brief warm farewell.
- **Empathy**: Be warm and empathetic ONE TIME when the user first reports an incident or loss. CRITICAL: DO NOT repeatedly say "I'm sorry" or apologize multiple times throughout the conversation.
- **Name Usage**: Use the caller's name AT MOST ONCE in the entire conversation — either at the initial greeting/confirmation or when verifying their identity. After that, NEVER use their name again. Saying "Thank you, Priya" or "I understand, Ravi" in every response sounds robotic and scripted. Just speak naturally without inserting names.
- **Conversational Context**: When the agent has just asked a question and the customer responds, ALWAYS interpret the customer's reply as an answer to that question — even if the phrasing is awkward, fragmented, or sounds like a question itself (this is common in phone conversations and speech-to-text). Do NOT re-interpret their answer as a new question or topic. For example, if the agent asks "Where did it happen?" and the customer says "What happened was in the parking lot of Max Mall", the location IS "parking lot of Max Mall" — acknowledge it and move on.
- **Reasonable Detail Level**: Accept reasonable answers without over-drilling for unnecessary precision. A location like "parking lot of Max Mall" or "MG Road intersection" is specific enough for an FNOL. Do NOT push for exact coordinates, lane numbers, or floor levels unless the caller volunteers that detail.
- **Compliance Alerts Are Mandatory**: The "Active Compliance Alerts" are NOT optional suggestions — they are rules you MUST follow. If a CRITICAL or HIGH severity alert is active, you MUST work it into the conversation naturally at the earliest appropriate moment. For example, if HIPAA is listed, you must inform the caller that their information is protected before collecting sensitive details. Do NOT read out compliance codes or rule IDs — weave the substance naturally.
- CRITICAL: Keep responses to 1-2 sentences MAX. Each response should cover ONE topic: either ask ONE question, OR provide ONE piece of procedural information. Think about what a real agent says on a phone call — short, clear, one thing at a time.
- CRITICAL: NEVER ask multiple questions in a single response. ONE question at a time.
- **No Repetition**: Check the "Full Conversation Context" carefully. If the AGENT already told the caller something (e.g., towing coverage, rental car offer, condolences), DO NOT repeat it in subsequent responses. Each response should only contain NEW, previously unsaid information or questions.
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

# ═══════════════════════════════════════════════════════
# POST-CALL EVALUATION — Structured Output
# ═══════════════════════════════════════════════════════

async def generate_post_call_evaluation(
    transcript_lines: list[dict],
    call_duration: float,
    detected_intent: str | None,
    member_data: dict | None,
) -> dict:
    """
    Generate a comprehensive post-call evaluation scorecard.
    Returns structured JSON with scores and feedback.
    """

    # Format transcript for LLM
    formatted_transcript = "\n".join(
        f"[{line['speaker']} {line['timestamp']}]: \"{line['text']}\""
        for line in transcript_lines
    )

    system_prompt = """You are an insurance call center quality assurance analyst.
Evaluate the agent's performance organically based on the flow and context of the conversation. Do not penalize the agent for missing rigid checklist items if they were not relevant or if the agent naturally deduced them from the caller's context.

Scoring criteria:
- Empathy: Did the agent show appropriate concern and maintain a professional, helpful tone without sounding robotic?
- Information Gathering: Did they efficiently collect necessary details without aggressively interrogating the customer? Did they deduce implicit info correctly?
- Compliance: Did they adhere to policy coverages (e.g., verifying towing coverage) and provide necessary disclosures naturally?
- Process Knowledge: Did the agent understand the insurance processes and guide the caller effectively?
- Resolution: Did the agent transition out of the call smoothly once core details were gathered without dragging it out?

Scores use a 1-10 scale per category and 1-100 overall."""

    user_prompt = f"""Call Transcript:
{formatted_transcript}

Call Duration: {int(call_duration)} seconds
Detected Claim Type: {detected_intent or 'unknown'}
Policyholder Identified: {member_data.get('name') if member_data else 'Not identified'}

Evaluate this agent's performance:"""

    response = await client.beta.chat.completions.parse(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=800,
        response_format=PostCallEvaluation,
    )

    evaluation = response.choices[0].message.parsed.model_dump()

    # Add metadata
    evaluation["call_duration_seconds"] = int(call_duration)
    evaluation["total_utterances"] = len(transcript_lines)
    evaluation["agent_utterances"] = sum(1 for l in transcript_lines if l["speaker"] == "Agent")
    evaluation["customer_utterances"] = sum(1 for l in transcript_lines if l["speaker"] == "Customer")

    return evaluation


def _format_docs(docs: list[dict] | None) -> str:
    if not docs:
        return "None found"
    return "\n\n".join(f"--- {d['title']} ---\n{d['content']}" for d in docs)


def _format_alerts(alerts: list[dict] | None) -> str:
    if not alerts:
        return "None"
    return "\n".join(f"- [{a['severity'].upper()}] {a['message']}" for a in alerts)
