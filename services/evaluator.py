import os
from openai import AsyncOpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = "gpt-4.1-mini"

# ═══════════════════════════════════════════════════════
# PYDANTIC SCHEMAS
# ═══════════════════════════════════════════════════════

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
# POST-CALL EVALUATION LOGIC
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
    formatted_transcript = "\\n".join(
        f"[{line['speaker']} {line['timestamp']}]: \\\"{line['text']}\\\""
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
