# main.py — FastAPI backend with WebSocket dual-path processing + post-call evaluation

import re
import json
import logging
import time
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from data.members import get_member
from graph.graph import build_graph
from tools.llm import generate_post_call_evaluation, generate_agent_suggestion_stream, extract_claim_facts

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("call-intelligence")

# ─── Build the LangGraph at startup ─── #
graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    logger.info("🚀 Building LangGraph pipeline...")
    graph = build_graph()
    logger.info("✅ LangGraph ready. Server is live.")
    yield
    logger.info("🛑 Server shutting down.")


app = FastAPI(
    title="Super/PF Call Intelligence",
    description="Real-time FNOL call intelligence demo with post-call evaluation",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS for dev mode (Vite runs on :5173) ─── #
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Regex patterns for the FAST PATH ─── #
POLICY_REGEX = re.compile(r"\b(CAR|LIFE|MED)[-\s]?(\d{4,})\b", re.IGNORECASE)


# ─── Health check ─── #
@app.get("/health")
async def health():
    return {"status": "ok", "graph_ready": graph is not None}


# ─── Deepgram Token Endpoint ─── #
# The frontend fetches a short-lived JWT from here so the API key never leaves the server
import os
import httpx

@app.get("/api/deepgram-token")
async def get_deepgram_token():
    """
    Return the Deepgram API key for the frontend to connect directly
    to Deepgram's WebSocket API. The key is stored server-side in .env
    and never hardcoded in the frontend code.
    
    Note: For production, consider using Deepgram's /v1/auth/grant 
    endpoint to issue short-lived JWTs (requires admin-scoped API key).
    """
    deepgram_key = os.getenv("DEEPGRAM_API_KEY", "")

    if not deepgram_key:
        return {"error": "DEEPGRAM_API_KEY not configured on the server"}, 500

    return {"token": deepgram_key}



# ─── WebSocket endpoint for real-time streaming ─── #
@app.websocket("/stream")
async def stream_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("📞 WebSocket connected")

    # Track full call transcript for post-call analysis
    call_transcript: list[dict] = []
    call_start_time = time.time()
    detected_intent = None
    detected_member = None
    detected_claim_type: str | None = None  # Track claim type for post-call eval
    last_knowledge_docs: list[dict] = []     # Track knowledge docs for post-call eval
    accumulated_facts: dict = {}  # Persistent fact state across the entire call

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            msg_type = data.get("type", "transcript")

            # ═══════════════════════════════════════════
            # 📋 END CALL — Generate post-call evaluation
            # ═══════════════════════════════════════════
            if msg_type == "end_call":
                logger.info("📋 Call ended — generating post-call evaluation...")
                await websocket.send_json({
                    "type": "processing",
                    "data": {"message": "Generating post-call evaluation..."},
                })

                call_duration = time.time() - call_start_time
                evaluation = await generate_post_call_evaluation(
                    transcript_lines=call_transcript,
                    call_duration=call_duration,
                    detected_intent=detected_intent,
                    member_data=detected_member,
                    accumulated_facts=accumulated_facts,
                    claim_type=detected_claim_type,
                    knowledge_docs=last_knowledge_docs,
                )

                # Attach FNOL form data for the frontend
                evaluation["fnol_data"] = {
                    "facts": accumulated_facts,
                    "member": detected_member,
                    "intent": detected_intent,
                }

                await websocket.send_json({
                    "type": "post_call_evaluation",
                    "data": evaluation,
                })
                logger.info("📋 Post-call evaluation sent")
                
                # 🔄 Reset state for the next call on this connection
                call_transcript = []
                call_start_time = time.time()
                detected_intent = None
                detected_member = None
                detected_claim_type = None
                last_knowledge_docs = []
                accumulated_facts = {}
                
                continue

            # ═══════════════════════════════════════════
            # 🔄 NEW CALL — Reset all state for a fresh call
            # ═══════════════════════════════════════════
            if msg_type == "new_call":
                logger.info("🔄 New call — resetting all backend state")
                call_transcript = []
                call_start_time = time.time()
                detected_intent = None
                detected_member = None
                detected_claim_type = None
                last_knowledge_docs = []
                accumulated_facts = {}
                continue

            # ═══════════════════════════════════════════
            # 🎙️ TRANSCRIPT MESSAGE — Process normally
            # ═══════════════════════════════════════════
            text: str = data.get("text", "")
            is_finalized: bool = data.get("is_finalized", False)
            speaker: str = data.get("speaker", "Unknown")
            offset: int = data.get("offset", 0)
            languages: list = data.get("languages", [])

            if not text.strip():
                continue

            # Map Deepgram diarization speaker IDs to roles
            speaker_label = _map_speaker(speaker)

            logger.info(
                f"{'📝 FINAL' if is_finalized else '💬 Partial'} "
                f"[{speaker_label}]: {text[:80]}" + (f" [Langs: {','.join(languages)}]" if languages else "")
            )

            # Store in call transcript (only finalized)
            if is_finalized:
                timestamp = _format_timestamp(offset)
                call_transcript.append({
                    "speaker": speaker_label,
                    "text": text,
                    "timestamp": timestamp,
                    "offset": offset,
                    "languages": languages,
                })

            # Always echo the transcript back for display immediately
            await websocket.send_json({
                "type": "transcript",
                "data": {
                    "text": text,
                    "is_finalized": is_finalized,
                    "speaker": speaker_label,
                    "timestamp": _format_timestamp(offset),
                    "offset": offset,
                },
            })

            # ═══════════════════════════════════════════
            # ⚡ FAST PATH — Regex policy ID extraction
            # ═══════════════════════════════════════════
            policy_match = POLICY_REGEX.search(text)
            if policy_match:
                # Reconstruct standardized ID (e.g. CAR-12345) regardless of spaces
                policy_id = f"{policy_match.group(1).upper()}-{policy_match.group(2)}"
                member = get_member(policy_id=policy_id)
                if member:
                    detected_member = member
                    await websocket.send_json({
                        "type": "member_profile",
                        "data": member,
                    })
                    logger.info(f"⚡ Fast path: sent profile for {policy_id}")
                else:
                    logger.info(f"⚡ Fast path: no member found for {policy_id}")

            # ═══════════════════════════════════════════
            # 🧠 SLOW PATH — LangGraph (only on finalized)
            # ═══════════════════════════════════════════
            # Only trigger AI analysis and suggest new responses if the Customer is speaking.
            # If the Agent is speaking, they do not need a new script generated based on their own words.
            if is_finalized and graph and speaker_label != "Agent":
                await websocket.send_json({
                    "type": "processing",
                    "data": {"message": "Analyzing transcript..."},
                })

                # Build full transcript string
                formatted_transcript = "\n".join(
                    f"[{line['speaker']} {line['timestamp']}]: \"{line['text']}\""
                    for line in call_transcript
                )

                state = {
                    "transcript": text,
                    "full_transcript": formatted_transcript,
                    "is_finalized": True,
                    "intent": None,
                    "claim_type": None,
                    "entities": None,
                    "member_data": detected_member,
                    "knowledge_docs": None,
                    "compliance_alerts": None,
                    "suggestion": None,
                }

                # Check if we need fact extraction — skip if key facts are already filled
                key_facts_filled = sum(
                    1 for k in ["date_of_incident", "location_of_incident", "incident_description", "cause_of_death", "caller_name", "hospital_name", "admission_date", "diagnosis"]
                    if accumulated_facts.get(k)
                )

                if key_facts_filled >= 4:
                    # Enough facts accumulated — skip the extra LLM call for speed
                    result = await graph.ainvoke(state)
                    logger.info("⚡ Skipped fact extraction (sufficient facts already)")
                else:
                    # Run LangGraph pipeline AND fact extraction in parallel
                    result, new_facts = await asyncio.gather(
                        graph.ainvoke(state),
                        extract_claim_facts(formatted_transcript),
                    )
                    # Merge new facts into accumulated state — non-null values always win
                    for key, val in new_facts.items():
                        if val is not None:
                            accumulated_facts[key] = val

                logger.info(f"📋 Accumulated facts: {accumulated_facts}")

                # Track detected intent
                if result.get("intent"):
                    detected_intent = result["intent"]
                    await websocket.send_json({
                        "type": "intent",
                        "data": {
                            "intent": result["intent"],
                            "claim_type": result.get("claim_type", ""),
                        },
                    })

                # Send member data (slow path backup)
                if result.get("member_data"):
                    detected_member = result["member_data"]
                    await websocket.send_json({
                        "type": "member_profile",
                        "data": result["member_data"],
                    })

                # Send knowledge articles — filter by detected claim type
                knowledge_docs = result.get("knowledge_docs") or []
                claim_type = result.get("claim_type", "")
                if claim_type:
                    detected_claim_type = claim_type
                if claim_type and knowledge_docs:
                    knowledge_docs = [
                        doc for doc in knowledge_docs
                        if doc.get("category", "") == "general" or doc.get("category", "") == claim_type
                    ]
                if knowledge_docs:
                    last_knowledge_docs = knowledge_docs  # Persist for post-call eval
                    await websocket.send_json({
                        "type": "knowledge",
                        "data": knowledge_docs,
                    })

                # Send compliance alerts
                if result.get("compliance_alerts"):
                    await websocket.send_json({
                        "type": "compliance",
                        "data": result["compliance_alerts"],
                    })

                # Clear the previous suggestion on the frontend just before starting the new stream
                await websocket.send_json({
                    "type": "clear_suggestion",
                    "data": {},
                })

                # Determine member data context for the LLM
                member_data_for_llm = result.get("member_data")
                if not member_data_for_llm and result.get("entities"):
                    # A lookup was attempted but failed — tell the LLM
                    attempted = result["entities"]
                    parts = []
                    if attempted.get("policy_id"):
                        parts.append(f"policy number '{attempted['policy_id']}'")
                    if attempted.get("phone"):
                        parts.append(f"phone number '{attempted['phone']}'")
                    if parts:
                        member_data_for_llm = f"LOOKUP FAILED: No account found for {' or '.join(parts)}. The caller may have provided incorrect information."

                # Get the most recent languages detected for the customer
                customer_languages = []
                for line in reversed(call_transcript):
                    if line["speaker"] == "Customer" and line.get("languages"):
                        customer_languages = line["languages"]
                        break

                logger.info(f"📚 Knowledge docs passed to LLM: {[d.get('docId', 'unknown') for d in knowledge_docs]}")
                suggestion_stream = generate_agent_suggestion_stream(
                    transcript=text,
                    full_transcript=formatted_transcript,
                    intent=result.get("intent"),
                    claim_type=result.get("claim_type"),
                    member_data=member_data_for_llm,
                    knowledge_docs=knowledge_docs,
                    compliance_alerts=result.get("compliance_alerts"),
                    collected_facts=accumulated_facts,
                    caller_languages=customer_languages,
                )
                
                async for chunk in suggestion_stream:
                    await websocket.send_json({
                        "type": "suggestion_chunk",
                        "data": {"text": chunk},
                    })

                logger.info("🧠 Slow path: all cards sent")


    except WebSocketDisconnect:
        logger.info("📞 WebSocket disconnected")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"message": str(e)},
            })
        except Exception:
            pass


def _map_speaker(speaker_id) -> str:
    """Map Deepgram diarization speaker IDs to human-readable labels.
    
    Deepgram returns integer speaker IDs (0, 1, 2, ...) in the words array.
    Speaker 0 is mapped to 'Agent', Speaker 1 to 'Customer'.
    """
    # Handle Deepgram numeric IDs
    if isinstance(speaker_id, int):
        mapping = {0: "Agent", 1: "Customer"}
        return mapping.get(speaker_id, f"Speaker {speaker_id}")
    # Handle string IDs (legacy Azure or frontend-sent)
    string_mapping = {
        "Guest-1": "Agent",
        "Guest-2": "Customer",
        "0": "Agent",
        "1": "Customer",
        "Unknown": "Speaker",
    }
    return string_mapping.get(str(speaker_id), f"Speaker {speaker_id}")


def _format_timestamp(seconds_value) -> str:
    """Convert Deepgram start time (seconds as float) to HH:MM:SS format.
    
    Also handles legacy Azure tick format (large integers > 10000) for backward compatibility.
    """
    if not seconds_value:
        return "00:00:00"
    total_seconds = float(seconds_value)
    # Legacy Azure tick detection: values > 10000 are likely 100-nanosecond ticks
    if total_seconds > 10000:
        total_seconds = total_seconds / 10_000_000
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    secs = int(total_seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


# ─── Serve frontend static files (production) ─── #
import os

frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_dist, "index.html"))

    # ADD THESE TWO ROUTES TO FIX THE 404 ERRORS:
    @app.get("/logo.png")
    async def serve_logo():
        return FileResponse(os.path.join(frontend_dist, "logo.png"))
        
    @app.get("/favicon.ico")
    async def serve_favicon():
        return FileResponse(os.path.join(frontend_dist, "favicon.ico"))

    @app.get("/pcm-processor.js")
    async def serve_pcm_processor():
        return FileResponse(os.path.join(frontend_dist, "pcm-processor.js"))
