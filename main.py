# main.py — FastAPI backend with WebSocket dual-path processing + post-call evaluation

import re
import json
import logging
import time
import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

from data.members import get_member
from agent.graph import build_graph
from services.extractor import extract_claim_facts, classify_intent
from services.evaluator import generate_post_call_evaluation
from data.knowledge import search_knowledge, warmup as warmup_knowledge

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
    logger.info("✅ LangGraph ready.")
    logger.info("🔥 Pre-loading knowledge module...")
    warmup_knowledge()
    logger.info("✅ Server is live.")
    yield
    logger.info("🛑 Server shutting down.")


app = FastAPI(
    title="CallIQ",
    description="Real-time FNOL call intelligence with post-call evaluation",
    version="2.0.0",
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
POLICY_REGEX = re.compile(r"\b(NS|CAR|LIFE|MED)[-\s]?(\d{4,})\b", re.IGNORECASE)
PHONE_REGEX = re.compile(r"(?:\b|\()\d{3}\)?[-\s.]?\d{3}[-\s.]?\d{4}\b")


# ─── Health check ─── #
@app.get("/health")
async def health():
    return {"status": "ok", "graph_ready": graph is not None}


# ─── Deepgram Token Endpoint ─── #
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
        return JSONResponse({"error": "DEEPGRAM_API_KEY not configured on the server"}, status_code=500)

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
    claim_type = None
    detected_claim_type: str | None = None
    detected_member = None
    accumulated_facts: dict = {}  # Persistent fact state across the entire call
    proactive_kb_sent = False  # Track whether we already sent knowledge docs to frontend
    last_knowledge_docs: list[dict] = []

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
                
                continue

            # ═══════════════════════════════════════════
            # 🔄 NEW CALL — Reset all state for a fresh call
            # ═══════════════════════════════════════════
            if msg_type == "new_call":
                logger.info("🔄 New call — resetting all backend state")
                call_transcript = []
                call_start_time = time.time()
                detected_intent = None
                claim_type = None
                detected_claim_type = None
                detected_member = None
                proactive_kb_sent = False
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
            # ⚡ FAST PATH — Regex policy ID / phone extraction
            # ═══════════════════════════════════════════
            policy_match = POLICY_REGEX.search(text)
            if policy_match:
                # Reconstruct standardized ID (e.g. CAR-100001) regardless of spaces
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

            # ⚡ Phone number fast path — try regex phone match if no member yet
            if not detected_member:
                phone_match = PHONE_REGEX.search(text)
                if phone_match:
                    phone_raw = phone_match.group(0)
                    member = get_member(phone=phone_raw)
                    if member:
                        detected_member = member
                        await websocket.send_json({
                            "type": "member_profile",
                            "data": member,
                        })
                        logger.info(f"⚡ Fast path (phone): sent profile for {phone_raw}")
                    else:
                        logger.info(f"⚡ Fast path (phone): no member found for {phone_raw}")

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

                # 1. Run intent, fact extraction, AND knowledge search ALL in parallel
                extracted_data = await asyncio.gather(
                    classify_intent(formatted_transcript),
                    extract_claim_facts(formatted_transcript),
                    asyncio.to_thread(search_knowledge, "procedures requirements timeline coverage documents", claim_type, 5),
                )
                
                intent_res = extracted_data[0]
                new_facts = extracted_data[1]
                knowledge_docs = extracted_data[2]  # Pre-fetched knowledge articles

                detected_intent = intent_res.get("intent")
                claim_type = intent_res.get("claim_type")
                if claim_type:
                    detected_claim_type = claim_type

                # Merge new facts into accumulated state — non-null values always win
                for key, val in new_facts.items():
                    if val is not None:
                        accumulated_facts[key] = val

                # Try to fetch member from accumulated facts if not already detected
                if not detected_member and accumulated_facts.get("policy_number"):
                    policy_id = accumulated_facts["policy_number"]
                    member = get_member(policy_id=policy_id)
                    if member:
                        detected_member = member
                        logger.info(f"🧠 Slow path: Found member {policy_id} via accumulated facts")
                        await websocket.send_json({
                            "type": "member_profile",
                            "data": member,
                        })

                logger.info(f"📋 Accumulated facts: {accumulated_facts}")
                logger.info(f"📚 Pre-fetched {len(knowledge_docs)} knowledge docs in parallel")

                # Track knowledge docs for post-call eval
                if knowledge_docs:
                    last_knowledge_docs = knowledge_docs

                # Send intent to frontend
                if detected_intent:
                    await websocket.send_json({
                        "type": "intent",
                        "data": {
                            "intent": detected_intent,
                            "claim_type": claim_type,
                        },
                    })
                    
                    # Send pre-fetched knowledge to frontend immediately
                    if knowledge_docs and not proactive_kb_sent:
                        proactive_kb_sent = True
                        await websocket.send_json({
                            "type": "knowledge",
                            "data": knowledge_docs,
                        })
                        logger.info(f"⚡ Sent {len(knowledge_docs)} knowledge docs to frontend for {claim_type}.")

                # Get the most recent languages detected for the customer
                customer_languages = []
                for line in reversed(call_transcript):
                    if line["speaker"] == "Customer" and line.get("languages"):
                        customer_languages = line["languages"]
                        break

                # 2. Setup state for ReAct Agent — knowledge_docs injected directly into prompt
                state = {
                    "transcript": text,
                    "full_transcript": formatted_transcript,
                    "is_finalized": True,
                    "intent": detected_intent,
                    "claim_type": claim_type,
                    "member_data": detected_member,
                    "accumulated_facts": accumulated_facts,
                    "knowledge_docs": knowledge_docs,  # Pre-fetched, injected into system prompt
                    "caller_languages": customer_languages,  # Detected languages for multilingual support
                    "messages": []  # Empty on start, populated by graph iteratively
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
                        output = event["data"].get("output")
                        
                        if hasattr(output, "content"):
                            tool_output_str = output.content
                        elif isinstance(output, list):
                            tool_output_str = output[0].content if output else ""
                        else:
                            tool_output_str = str(output)
                        
                        try:
                            # Our tools return JSON strings, so we parse them to send structured data to the FE
                            tool_data = json.loads(tool_output_str) if isinstance(tool_output_str, str) else tool_output_str
                            
                            logger.info(f"🔧 Tool {name} finished. Received tool_data keys: {tool_data.keys() if isinstance(tool_data, dict) else type(tool_data)}")

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
frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_dist, "index.html"))

    @app.get("/logo.png")
    async def serve_logo():
        return FileResponse(os.path.join(frontend_dist, "logo.png"))
        
    @app.get("/favicon.ico")
    async def serve_favicon():
        return FileResponse(os.path.join(frontend_dist, "favicon.ico"))

    @app.get("/pcm-processor.js")
    async def serve_pcm_processor():
        return FileResponse(os.path.join(frontend_dist, "pcm-processor.js"))
