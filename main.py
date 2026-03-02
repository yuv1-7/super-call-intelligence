# main.py — FastAPI backend with WebSocket dual-path processing + post-call evaluation

import re
import json
import logging
import time
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from data.members import get_member
from agent.graph import build_graph
from services.extractor import extract_claim_facts, classify_intent
from services.evaluator import generate_post_call_evaluation

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
POLICY_REGEX = re.compile(r"\b(CAR|LIFE)[-\s]?(\d{4,})\b", re.IGNORECASE)


# ─── Health check ─── #
@app.get("/health")
async def health():
    return {"status": "ok", "graph_ready": graph is not None}


# ─── Azure Speech Token Endpoint ─── #
# The frontend fetches a short-lived token from here instead of holding the key
import os
import httpx

@app.get("/api/speech-token")
async def get_speech_token():
    """
    Issue a short-lived Azure Speech authorization token.
    The token is valid for 10 minutes. The frontend uses this token
    with SpeechConfig.fromAuthorizationToken() so the API key never
    leaves the server.
    """
    speech_key = os.getenv("AZURE_SPEECH_KEY", "")
    speech_region = os.getenv("AZURE_SPEECH_REGION", "eastus")

    if not speech_key:
        raise HTTPException(status_code=500, detail="AZURE_SPEECH_KEY not configured on the server")

    token_url = f"https://{speech_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            headers={
                "Ocp-Apim-Subscription-Key": speech_key,
                "Content-Length": "0",
            },
        )

    if response.status_code == 200:
        return {
            "token": response.text,
            "region": speech_region,
        }
    else:
        logger.error(f"Failed to fetch speech token: {response.status_code} {response.text}")
        raise HTTPException(status_code=500, detail="Failed to fetch speech token")



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
                accumulated_facts = {}
                continue

            # ═══════════════════════════════════════════
            # 🎙️ TRANSCRIPT MESSAGE — Process normally
            # ═══════════════════════════════════════════
            text: str = data.get("text", "")
            is_finalized: bool = data.get("is_finalized", False)
            speaker: str = data.get("speaker", "Unknown")
            offset: int = data.get("offset", 0)

            if not text.strip():
                continue

            # Map Azure diarization speaker IDs to roles
            speaker_label = _map_speaker(speaker)

            logger.info(
                f"{'📝 FINAL' if is_finalized else '💬 Partial'} "
                f"[{speaker_label}]: {text[:80]}"
            )

            # Store in call transcript (only finalized)
            if is_finalized:
                timestamp = _format_timestamp(offset)
                call_transcript.append({
                    "speaker": speaker_label,
                    "text": text,
                    "timestamp": timestamp,
                    "offset": offset,
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

                # 1. Run intent & fact extraction outside the main graph to feed context
                # (Can be optimized to run natively as tools later, but extracting facts up-front gives a cleaner prompt)
                extracted_data = await asyncio.gather(
                    classify_intent(formatted_transcript),
                    extract_claim_facts(formatted_transcript)
                )
                
                intent_res = extracted_data[0]
                new_facts = extracted_data[1]

                detected_intent = intent_res.get("intent")
                claim_type = intent_res.get("claim_type")

                # Merge new facts into accumulated state — non-null values always win
                for key, val in new_facts.items():
                    if val is not None:
                        accumulated_facts[key] = val

                logger.info(f"📋 Accumulated facts: {accumulated_facts}")

                # Send intent to frontend
                if detected_intent:
                    await websocket.send_json({
                        "type": "intent",
                        "data": {
                            "intent": detected_intent,
                            "claim_type": claim_type,
                        },
                    })

                # 2. Setup state for ReAct Agent
                state = {
                    "transcript": text,
                    "full_transcript": formatted_transcript,
                    "is_finalized": True,
                    "intent": detected_intent,
                    "claim_type": claim_type,
                    "member_data": detected_member,
                    "accumulated_facts": accumulated_facts,
                    "messages": [] # Empty on start, populated by graph iteratively
                }

                # Clear the previous suggestion on the frontend just before starting the new stream
                await websocket.send_json({
                    "type": "clear_suggestion",
                    "data": {},
                })

                logger.info("🧠 Slow path: Starting Agent ReAct loop...")
                
                # 3. Stream native LangGraph events
                # Use v2 for latest LangGraph event schema
                async for event in graph.astream_events(state, version="v2"):
                    event_type = event["event"]
                    name = event.get("name", "")

                    # -- Handle Tokens (Agent Speaking) --
                    if event_type == "on_chat_model_stream":
                        chunk = event["data"]["chunk"]
                        # The chunk could be for a tool call (no content) or for the user (content)
                        if chunk.content:
                            await websocket.send_json({
                                "type": "suggestion_chunk",
                                "data": {"text": chunk.content},
                            })

                    # -- Handle Tool Start (UI Processing updates) --
                    elif event_type == "on_tool_start":
                        # Send friendly processing messages based on tool invoked
                        msg = "Processing..."
                        if name == "lookup_policyholder":
                            msg = "Looking up policy..."
                        elif name == "search_knowledge_base":
                            msg = "Searching knowledge base..."
                        elif name == "check_compliance_rules":
                            msg = "Checking compliance rules..."
                            
                        await websocket.send_json({
                            "type": "processing",
                            "data": {"message": msg},
                        })
                        
                    # -- Handle Tool End (Send Data back to UI) --
                    elif event_type == "on_tool_end":
                        # Output of the tool node is in output
                        tool_output_str = event["data"].get("output", "")
                        
                        try:
                            # Our tools return JSON strings, so we parse them to send structured data to the FE
                            if isinstance(tool_output_str, str):
                                tool_data = json.loads(tool_output_str)
                            else:
                                tool_data = tool_output_str
                                
                            if name == "lookup_policyholder" and tool_data and "status" not in tool_data:
                                # Found a valid member profile
                                detected_member = tool_data
                                await websocket.send_json({
                                    "type": "member_profile",
                                    "data": detected_member,
                                })
                            elif name == "search_knowledge_base" and tool_data.get("results"):
                                await websocket.send_json({
                                    "type": "knowledge",
                                    "data": tool_data["results"],
                                })
                            elif name == "check_compliance_rules" and tool_data.get("alerts"):
                                await websocket.send_json({
                                    "type": "compliance",
                                    "data": tool_data["alerts"],
                                })
                        except Exception as e:
                            logger.error(f"Failed to parse tool output from {name}: {e}")

                logger.info("🧠 Slow path: Stream complete.")

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


def _map_speaker(speaker_id: str) -> str:
    """Map Azure diarization speaker IDs to human-readable labels."""
    mapping = {
        "Guest-1": "Agent",
        "Guest-2": "Customer",
        "Unknown": "Speaker",
    }
    return mapping.get(speaker_id, f"Speaker {speaker_id}")


def _format_timestamp(offset_ticks: int) -> str:
    """Convert Azure Speech offset (in 100-nanosecond ticks) to HH:MM:SS format."""
    if not offset_ticks:
        return "00:00:00"
    total_seconds = offset_ticks / 10_000_000
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


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
