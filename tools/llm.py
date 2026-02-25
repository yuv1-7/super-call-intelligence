# tools/llm.py — OpenAI LLM utilities for Insurance FNOL + Post-Call Evaluation

import os
from typing import Literal
from openai import AsyncOpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = "gpt-4.1-mini"


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
        model=MODEL,
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
        model=MODEL,
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
# AGENT SUGGESTION — Separated Prompts by Policy Type
# ═══════════════════════════════════════════════════════

# ─── SHARED BASE RULES (apply to ALL claim types) ─── #
_SHARED_RULES = """You are an AI assistant and training tool for insurance call center agents.
Your role is to guide the agent through the conversation naturally, handling First Notice of Loss (FNOL) and general inquiries smoothly without sounding like a rigid checklist robot.
Generate a professional, empathetic, and compliance-aware suggested response for the agent to say to the caller.

Core Rules:
- NEVER address the customer directly. You are writing a script/talking points FOR the agent to read verbatim.
- **Act as a helpful guide, not a strict interrogator**: Do not aggressively demand information if the user is distressed or if the details aren't immediately necessary.
- **Handling Acknowledgements**: When a user responds with "No issues", "No problem", "Sure", or "Okay" immediately after the agent provides a disclaimer, disclosure, or statement (like call recording), treat this strictly as a conversational acknowledgement. DO NOT interpret this as the user saying they have no insurance claim, no damage, or that the call is over. Follow up with the next relevant question for the claim.
- **Policy Lookup Priority**: ONLY if the Policyholder Data is "Not yet identified", ask for the policy number first to look up their account. If they cannot provide it, ask for their phone number as an alternative. You CANNOT search by name alone.
- **Account Verification Complete**: CRITICAL RULE: ALWAYS look at the "Policyholder Data" section. If it shows ANY member details (name, policy type, etc.), YOU ALREADY HAVE THEIR ACCOUNT AND POLICY OPEN. You are permanently forbidden from asking for their policy number, phone number, or name. NEVER ask for details to "look up their account", "verify their policy", or "so I can assist you" because IT IS ALREADY VERIFIED.
- **Lookup Failed**: If the Policyholder Data says "LOOKUP FAILED", the caller provided a policy number or phone number that did not match any account in our system. Politely inform them that you were unable to locate an account with the information provided and ask them to double-check the number. Offer alternatives (e.g., "Could you try your phone number instead?" or "Do you have the policy number handy?"). Do NOT just silently re-ask for the same info without acknowledging the failure.
- **Role of Knowledge Docs**: The "Relevant Policy Articles" are internal company reference documents written for human agents. Use them to extract factual procedures, timelines, coverage rules, and document checklists. DO NOT follow them as step-by-step scripts — interpret them intelligently based on the conversation context. If information has already been gathered, skip that step. If the Policyholder Data is already populated, do NOT re-ask for policy numbers or identity.
- **Efficient Call Wrap-Up**: Once the core details of the issue are gathered, immediately move to wrap up the call, provide next steps, and ask if there is anything else you can assist with.
- **Ending the Call**: CRITICAL RULE: If the customer responds that they need no further assistance (e.g., "no", "that's it", "nothing else"), you MUST explicitly close the dialogue. Generate a definitive sign-off script (e.g., "Thank you for calling Super Insurance. Have a great day. Goodbye.") and add a bracketed note at the end: `[Agent: End Call]`.
- **Empathy**: Be warm and empathetic ONE TIME when the user first reports an incident or loss. CRITICAL: DO NOT repeatedly say "I'm sorry" or apologize multiple times throughout the conversation.
- **Name Usage**: Use the caller's name ONCE at the start to greet them or confirm identity. After that, DO NOT keep repeating their name in every response — it sounds robotic and unnatural. Speak like a normal human would.
- **Conversational Context**: When the agent has just asked a question and the customer responds, ALWAYS interpret the customer's reply as an answer to that question — even if the phrasing is awkward, fragmented, or sounds like a question itself (this is common in phone conversations and speech-to-text). Do NOT re-interpret their answer as a new question or topic. For example, if the agent asks "Where did it happen?" and the customer says "What happened was in the parking lot of Max Mall", the location IS "parking lot of Max Mall" — acknowledge it and move on.
- **Reasonable Detail Level**: Accept reasonable answers without over-drilling for unnecessary precision. A location like "parking lot of Max Mall" or "MG Road intersection" is specific enough for an FNOL. Do NOT push for exact coordinates, lane numbers, or floor levels unless the caller volunteers that detail.
- Reference compliance requirements naturally (don't read out compliance codes).
- CRITICAL: Keep responses to 1-2 SHORT sentences MAX. Think about what a real human agent would say on a phone call — they would NOT read a paragraph. Each response should address ONE thing: either ask ONE question or provide ONE piece of information.
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
- **Focus on Insurance, Not Medical**: Your primary goal is processing the claim. NEVER instruct the agent to offer to call medical support or help with emergency services unless the caller explicitly reports a severe, life-threatening emergency.
- **Next Steps & Timeline**: When wrapping up, you MUST inform the caller about what happens next. Reference the 'Relevant Policy Articles' for specific timelines (e.g., "a claims adjuster will reach out within 24-48 hours"). Do NOT just say goodbye without setting expectations.
"""

# ─── LIFE INSURANCE SPECIFIC RULES ─── #
_LIFE_RULES = _SHARED_RULES + """
Life Insurance Death Claim Specific Rules:
- **Caller is NOT the Policyholder**: The policyholder is DECEASED. The caller is a family member or beneficiary. NEVER greet the caller by the policyholder's name. NEVER say "your passing" to the caller — use "your father's passing", "their passing", or refer to the deceased by name.
- **Condolences**: Express sincere condolences ONCE at the start. DO NOT BE OVERLY APOLOGETIC. Do not keep repeating "I'm sorry" throughout the conversation.
- **Caller Identity**: Ask for the caller's FULL NAME so you can verify them against the 'beneficiaries' list in the Policyholder Data. Do NOT ask for their name to "locate the policy" — you locate the policy by policy number or phone number ONLY.
- **Relationship Verification**: CRITICAL: Check the "Full Conversation Context". If the caller said "my father", "my husband", "my wife", "my mother", etc. at ANY point during the call, YOU ALREADY KNOW THE RELATIONSHIP. NEVER ask "what is your relationship to the deceased?" if they have already told you. Deduce it: "my father" = son/daughter, "my husband" = spouse, etc.
- **Fact Deduction**: CRITICAL: Check the "Full Conversation Context". If the caller already provided the date, location, or cause of death — even informally (e.g., "heart attack", "February 10th", "at City General Hospital", "at home", "in the hospital") — YOU ALREADY KNOW IT. A hospital name IS a location. A disease or event IS a cause. A month and day IS a date. NEVER re-ask for these details. Only ask for details that are completely ABSENT from the conversation.
- **Mandatory Death Claim Information**: Before you can move to wrap up, you MUST ensure you have collected: Date of death, Location of death, and Cause of death. A hospital name, city, or general area (e.g., "City General Hospital") is a SUFFICIENT location — do NOT ask for more specifics. If any of these three are genuinely missing (never mentioned at all), gently ask for them (one at a time).
- **Documentation Guidance**: Once you have all the facts (date, location, cause), you MUST clearly list the required documents: certified death certificate, completed claim form, and photo ID of the beneficiary. Explicitly tell the caller that the claim form will be mailed or emailed to the address on file.
- **Beneficiary Verification**: Once the caller provides their name, check the 'beneficiaries' section of the Policyholder Data. If they are listed, confirm they are a recognized beneficiary. If not listed, inform them sensitively that they may need to provide additional documentation.
- **Contestability**: If the Policyholder Data shows `contestabilityExpired: false`, gently advise that additional review may be required as the policy is within the 2-year contestability period.
- **HIPAA**: Reference that all medical and personal information is protected under HIPAA when appropriate, but do so naturally (don't read out compliance codes).
"""


def _build_user_prompt(
    transcript: str,
    full_transcript: str,
    intent: str | None,
    member_data: dict | None,
    knowledge_docs: list[dict] | None,
    compliance_alerts: list[dict] | None,
) -> str:
    """Build the user prompt for the agent suggestion functions."""
    return f"""Recent Caller's Statement:
{transcript}

Full Conversation Context:
{full_transcript or 'None yet'}

Detected Intent: {intent or 'unknown'}

Policyholder Data:
{member_data or 'Not yet identified'}

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
) -> str:
    """Generate a contextual suggested response for the call center agent."""

    system_prompt = _select_prompt(claim_type)
    user_prompt = _build_user_prompt(
        transcript, full_transcript, intent, member_data, knowledge_docs, compliance_alerts
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
):
    """Generate a contextual suggested response for the call center agent, streaming chunks."""

    system_prompt = _select_prompt(claim_type)
    user_prompt = _build_user_prompt(
        transcript, full_transcript, intent, member_data, knowledge_docs, compliance_alerts
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
    return "\n".join(f"- {d['title']}: {d['content'][:200]}..." for d in docs)


def _format_alerts(alerts: list[dict] | None) -> str:
    if not alerts:
        return "None"
    return "\n".join(f"- [{a['severity'].upper()}] {a['message']}" for a in alerts)
