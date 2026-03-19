# services/evaluator.py — Post-Call Evaluation System
# Architecture:
#   Call A (Rubric)   → Per-criterion scoring of the human agent's actual speech
#   Call B (Insights) → Rich qualitative analysis: caller, agent, patterns, risks
#   Python (instant)  → FNOL completeness from accumulated_facts

import os
import json
import asyncio
import logging
from typing import Optional
from openai import AsyncOpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("call-intelligence")

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4.1-mini"


# ═══════════════════════════════════════════════════════
# FNOL FIELD DEFINITIONS
# ═══════════════════════════════════════════════════════

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

_MEDICAL_FNOL_FIELDS = {
    "caller_name":                  {"label": "Caller Name",              "points": 2},
    "hospital_name":                {"label": "Hospital Name",            "points": 3},
    "admission_date":               {"label": "Admission Date",           "points": 3},
    "diagnosis":                    {"label": "Diagnosis / Condition",    "points": 3},
    "treating_doctor":              {"label": "Treating Doctor",          "points": 2},
    "cashless_or_reimbursement":    {"label": "In-Network / Out-of-Network", "points": 2},
    "pre_authorization_number":     {"label": "Pre-Authorization Number", "points": 2},
    "discharge_date":               {"label": "Discharge Date",           "points": 1},
}


def calculate_fnol_completeness(accumulated_facts: dict | None, claim_type: str | None) -> dict:
    if not accumulated_facts:
        accumulated_facts = {}
    if claim_type == "life_insurance":
        required = _LIFE_FNOL_FIELDS
    elif claim_type == "medical_insurance":
        required = _MEDICAL_FNOL_FIELDS
    else:
        required = _CAR_FNOL_FIELDS
    total_points = sum(f["points"] for f in required.values())
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
        "fnol_completeness_pct": pct,
        "fnol_points_earned": earned_points,
        "fnol_points_possible": total_points,
        "fnol_fields_collected": collected,
        "fnol_fields_missing": missing,
    }


# ═══════════════════════════════════════════════════════
# PYDANTIC SCHEMAS — Rubric
# ═══════════════════════════════════════════════════════

class RubricItem(BaseModel):
    criterion: str
    points_possible: int
    points_awarded: int
    passed: bool
    evidence: str
    deduction_reason: str | None


class ScoredSection(BaseModel):
    section_name: str
    points_possible: int
    points_awarded: int
    auto_failed: bool
    auto_fail_reason: str | None
    rubric_items: list[RubricItem]


class RubricEvaluation(BaseModel):
    section_1_opening: ScoredSection
    section_2_identity: ScoredSection
    section_3_information: ScoredSection
    section_4_empathy: ScoredSection
    section_5_procedure: ScoredSection
    section_6_compliance: ScoredSection
    section_7_close: ScoredSection
    auto_fails: list[str]


# ═══════════════════════════════════════════════════════
# PYDANTIC SCHEMAS — Insights
# ═══════════════════════════════════════════════════════

class CallerInsights(BaseModel):
    caller_description: str
    emotional_state: str
    communication_style: str
    cooperation_level: str
    difficulty_score: int
    difficulty_rationale: str
    notable_behaviors: list[str]


class SkillObservation(BaseModel):
    skill_area: str
    observation: str
    impact: str
    valence: str


class ComplianceFlag(BaseModel):
    flag_type: str
    severity: str
    description: str
    agent_quote: str
    risk: str


class MissedOpportunity(BaseModel):
    moment: str
    what_happened: str
    better_approach: str


class CallEvaluationInsights(BaseModel):
    call_type: str
    call_outcome: str
    call_summary: str
    caller_insights: CallerInsights
    call_events: list[str]
    skill_observations: list[SkillObservation]
    procedure_gaps: list[str]
    strong_moments: list[str]
    compliance_flags: list[ComplianceFlag]
    compliance_summary: str
    missed_opportunities: list[MissedOpportunity]
    recurring_risk_indicators: list[str]
    positive_indicators: list[str]
    agent_improvement_notes: list[str]


# ═══════════════════════════════════════════════════════
# SYSTEM PROMPTS
# ═══════════════════════════════════════════════════════

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

══════════════════════════════════════════════════════════════════════════
RUBRIC
══════════════════════════════════════════════════════════════════════════

SECTION 1 — Opening & Compliance (12 pts)
──────────────────────────────────────────────
A. Agent stated their name in the greeting (3 pts, binary)
B. Call recording disclosure — "recorded" or "recording" must appear in opening (4 pts, binary)
C. Warm and professional opening tone — not robotic, creates comfort (3 pts, scaled 0-3)
D. Offered to help before asking for data (2 pts, binary)

Evaluate ONLY the first 2-3 [Agent] turns.

SECTION 2 — Account & Identity Verification (14 pts)
──────────────────────────────────────────────────────────
A. Asked for policy number or registered phone to locate account (4 pts, binary)
B. Confirmed account found — read back policyholder name (3 pts, binary)
C. Handled lookup failure gracefully — offered alternatives, no dead-end (4 pts, binary | N/A = full pts if first lookup succeeded)
D. Verified caller identity where required:
   - Life claim: confirmed caller is listed beneficiary
   - Car claim with policyholder calling: N/A = full pts (3 pts, binary | N/A)

SECTION 3 — Information Gathering (20 pts)
───────────────────────────────────────────────
A. Never stacked questions — one question per turn only (6 pts, scaled: -2 per stacking instance, min 0)
   CHECK: Count [Agent] turns with more than one "?" — each is a stacking violation.
B. Never re-asked for information already given by the caller (5 pts, scaled: -2 per repeat, min 0)
   CHECK: Look for dates, names, locations asked again after caller already stated them.
C. Logical question flow — no unnecessary loops or tangents (5 pts, scaled 0-5)
D. Asked the claim-critical question:
   Car: police report / FIR status
   Life: full beneficiary name AND relationship to policyholder
   Medical: hospital name AND diagnosis
   (4 pts, binary)

SECTION 4 — Empathy & Communication (18 pts)
─────────────────────────────────────────────────
A. Expressed genuine empathy at the right moment — not robotic, not excessive (5 pts, scaled 0-5)
   Life: condolences are mandatory. Car: acknowledgment of stress/inconvenience expected. Medical: acknowledgment of health concern.
B. Did NOT repeat condolences or apologies mechanically more than twice (3 pts, binary: 0 if violated)
C. Used caller's name no more than twice total across the call (2 pts, binary: 0 if >2 uses)
D. Tone and language matched caller's emotional state and communication style (5 pts, scaled 0-5)
E. Language clear and jargon-free — explained any insurance terminology used (3 pts, scaled 0-3)

SECTION 5 — Product Knowledge & Procedure (18 pts)
──────────────────────────────────────────────────────
A. Explained correct next steps clearly — what happens after this call (5 pts, scaled 0-5)
B. Accurately assessed applicable coverage from policy data:
   Car: correct on towing/rental based on add-ons actually in policy
   Life: correct on payout structure/beneficiary if visible
   Medical: correct on in-network/out-of-network status and pre-authorization
   (4 pts, binary | N/A = full pts if policy not located)
C. Communicated all required documents in ONE complete response:
   Car: police report + repair estimate + photos
   Life: death certificate + claim form + govt ID
   Medical: hospital bills + discharge summary + diagnostic reports (out-of-network only)
   (5 pts, binary: 0 if split across multiple turns or incomplete)
D. Gave realistic processing timeline (4 pts, binary)
   Car: adjuster callback 24-48 hrs
   Life: 30-60 day processing, mention of payout options
   Medical: pre-authorization 2-4 hrs / reimbursement 45 days

SECTION 6 — Compliance (18 pts)
─────────────────────────────────────
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

FOR MEDICAL CLAIMS:
A. ⚠️ AUTO-FAIL TRIGGER: Medical privacy notice given BEFORE discussing diagnosis or treatment details (6 pts)
   If missing → Section 6 = 0 pts total.
B. Correctly verified network hospital status and communicated in-network/out-of-network path (4 pts, binary)
C. Communicated pre-authorization requirement for in-network claims (4 pts, binary | N/A if out-of-network)
D. Addressed pre-existing condition waiting period status accurately if applicable (4 pts, binary | N/A = full pts if no PED)

SECTION 7 — Call Resolution & Close (10 pts)
──────────────────────────────────────────────────
A. Summarized next steps before ending — caller knows what to expect (4 pts, scaled 0-4)
B. Asked "Is there anything else?" or equivalent (3 pts, binary)
C. Clean professional close — no abruptness, no trailing (3 pts, scaled 0-3)

══════════════════════════════════════════════════════════════════════════
Return structured RubricEvaluation. Evidence must be a direct agent quote or "Not observed in transcript".
"""


_INSIGHTS_SYSTEM_PROMPT = """You are writing a detailed call evaluation for an insurance call center.

AUDIENCE AND PURPOSE:
  • A supervisor will review this alongside evaluations of 20-50+ other calls from multiple agents.
    They are looking for patterns across calls — recurring compliance gaps, skill deficits, standout performance.
  • An agent will read their own evaluation to understand exactly what they did and what to do differently.
  • This data will be stored and queried via RAG/LLM to surface agent-level trends over time.

BECAUSE OF THIS:
  • Every observation must be self-contained — it should make full sense when read in isolation, without the transcript.
  • Be specific. Generic observations ("agent lacked empathy") are useless for aggregation.
  • Cite actual words. If you say the agent handled something well or poorly, quote what they said.
  • Do not pad. Only include observations that are genuinely informative.

CRITICAL CONTEXT:
  • [Agent] turns = the REAL HUMAN AGENT'S own spoken words. NOT AI suggestions.
  • The agent had a background AI assistant visible on their screen but spoke independently.
  • Judge ONLY what the agent actually said in [Agent] turns.
  • The transcript may contain multiple languages, a mix of languages, or phonetic English representations of other languages.
  • Your entire evaluation, insights, and output MUST be strictly in English.

══════════════════════════════════════════════════════════════════════════
FIELD INSTRUCTIONS
══════════════════════════════════════════════════════════════════════════

call_type: Concise descriptor of the call type and complexity.

call_outcome: What actually happened by end of call.

call_summary — 4-6 paragraphs covering:
  P1: Who called, why, what type of event, whether policy was located.
  P2: How the caller communicated — emotional state, language, cooperation.
  P3: How the agent handled it — structure, control, hardest moment.
  P4: What information was exchanged — FNOL data collected, services offered.
  P5: How the call ended — caller's understanding of next steps.
  P6 (only if needed): Notable compliance, fraud, or unusual events.

caller_insights: Based ONLY on customer turns.
  • difficulty_score: 1=Routine, 2=Mild, 3=Moderate, 4=Difficult, 5=Very challenging
  • cooperation_level: Very cooperative / Cooperative / Somewhat difficult / Difficult / Hostile

skill_observations — 6-12 items, mix of positive and negative with evidence.

compliance_flags: Only actual compliance issues, not near-misses.

missed_opportunities — 2-5 specific moments.

recurring_risk_indicators: Behaviors to track across calls.

agent_improvement_notes — 3-5 items, specific to THIS call.

══════════════════════════════════════════════════════════════════════════
TONE: Analytical and factual. Written to inform, not to judge.
Every claim backed by transcript evidence. No filler.
"""


# ═══════════════════════════════════════════════════════
# LLM CALL FUNCTIONS
# ═══════════════════════════════════════════════════════

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
        collected = [k for k, v in accumulated_facts.items() if v is not None]
        not_collected = [k for k, v in accumulated_facts.items() if v is None]
        fnol_context = f"\nFNOL collected: {collected}\nFNOL missing: {not_collected}"

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
            {"role": "user", "content": user_prompt},
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
    caller_context: str = "",
) -> dict:
    user_prompt = f"""CALL TRANSCRIPT:
{formatted_transcript}

CONTEXT:
Duration: {int(call_duration)}s | Intent: {detected_intent or 'unknown'} | Line: {claim_type or 'unknown'}
Policy Holder: {member_data.get('name') if member_data else 'NOT located during call'}
Rubric Score: {overall_score}/100
{caller_context}

IMPORTANT: When describing who called and the caller's identity, use the verified policyholder 
and caller names provided above (not raw transcript text which may contain speech-to-text errors).
If the caller IS the policyholder, refer to them by the verified policyholder name.
If someone else called on behalf of the policyholder, use the caller name from the conversation.

Write the complete evaluation. Every observation must cite the transcript."""

    response = await client.beta.chat.completions.parse(
        model=MODEL,
        messages=[
            {"role": "system", "content": _INSIGHTS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
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


# ═══════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════

async def generate_post_call_evaluation(
    transcript_lines: list,
    call_duration: float,
    detected_intent: str | None,
    member_data: dict | None,
    accumulated_facts: dict | None = None,
    claim_type: str | None = None,
    knowledge_docs: list | None = None,
) -> dict:
    formatted_transcript = "\n".join(
        f"[{line['speaker']} {line['timestamp']}]: \"{line['text']}\""
        for line in transcript_lines
    )

    # Instant FNOL scoring
    fnol_result = calculate_fnol_completeness(accumulated_facts, claim_type)

    # Step 1: Run rubric scoring first to get the actual score
    rubric_result = await _run_agent_rubric(
        formatted_transcript=formatted_transcript,
        call_duration=call_duration,
        detected_intent=detected_intent,
        member_data=member_data,
        claim_type=claim_type,
        accumulated_facts=accumulated_facts,
    )

    # Extract the 7 sections and compute normalized score (max = 110 pts → percentage)
    extracted_sections = [
        rubric_result["section_1_opening"],
        rubric_result["section_2_identity"],
        rubric_result["section_3_information"],
        rubric_result["section_4_empathy"],
        rubric_result["section_5_procedure"],
        rubric_result["section_6_compliance"],
        rubric_result["section_7_close"],
    ]
    MAX_RUBRIC_POINTS = 110  # 12+14+20+18+18+18+10
    raw_points = sum(s["points_awarded"] for s in extracted_sections)
    overall_score = round((raw_points / MAX_RUBRIC_POINTS) * 100)
    grade = _calculate_grade(overall_score)

    # Build caller identity context so insights LLM uses verified names, not STT errors
    caller_context = ""
    if member_data:
        caller_context += f"\nPolicyholder Name (verified): {member_data.get('name', 'Unknown')}"
    if accumulated_facts:
        caller_name = accumulated_facts.get('caller_name')
        relationship = accumulated_facts.get('relationship_to_policyholder')
        if caller_name:
            caller_context += f"\nCaller Name (from conversation): {caller_name}"
        if relationship:
            caller_context += f"\nRelationship to Policyholder: {relationship}"

    # Step 2: Run insights with the actual computed score and caller context
    insights_result = await _run_call_insights(
        formatted_transcript=formatted_transcript,
        call_duration=call_duration,
        detected_intent=detected_intent,
        overall_score=overall_score,
        member_data=member_data,
        claim_type=claim_type,
        caller_context=caller_context,
    )

    ci = insights_result.get("caller_insights", {})

    return {
        # Scores
        "overall_score": overall_score,
        "grade": grade,

        # Call context
        "call_type": insights_result["call_type"],
        "call_outcome": insights_result["call_outcome"],
        "call_summary": insights_result["call_summary"],
        "call_events": insights_result["call_events"],

        # Caller
        "caller_insights": ci,

        # Agent observations
        "skill_observations": insights_result["skill_observations"],
        "procedure_gaps": insights_result["procedure_gaps"],
        "strong_moments": insights_result["strong_moments"],

        # Compliance
        "compliance_flags": insights_result["compliance_flags"],
        "compliance_summary": insights_result["compliance_summary"],

        # Improvement
        "missed_opportunities": insights_result["missed_opportunities"],
        "recurring_risk_indicators": insights_result["recurring_risk_indicators"],
        "positive_indicators": insights_result["positive_indicators"],
        "agent_improvement_notes": insights_result["agent_improvement_notes"],

        # Rubric (re-bundled from explicit fields)
        "sections": extracted_sections,
        "auto_fails": rubric_result["auto_fails"],

        # FNOL
        "fnol_completeness_pct": fnol_result["fnol_completeness_pct"],
        "fnol_points_earned": fnol_result["fnol_points_earned"],
        "fnol_points_possible": fnol_result["fnol_points_possible"],
        "fnol_fields_collected": fnol_result["fnol_fields_collected"],
        "fnol_fields_missing": fnol_result["fnol_fields_missing"],

        # Metadata
        "call_duration_seconds": int(call_duration),
        "total_utterances": len(transcript_lines),
        "agent_utterances": sum(1 for l in transcript_lines if l["speaker"] == "Agent"),
        "customer_utterances": sum(1 for l in transcript_lines if l["speaker"] == "Customer"),
    }
