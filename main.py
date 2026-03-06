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
POLICY_REGEX = re.compile(r"\b(CAR|LIFE)[-\s]?(\d{4,})\b", re.IGNORECASE)


# ─── Helper functions ─── #
def _map_speaker(speaker_id: str) -> str:
    """Map diarization speaker IDs to human-readable labels.

    Handles Sarvam IDs (SPEAKER_00, SPEAKER_01, ...) and
    old Azure-style IDs (Guest-1, Guest-2, ...).
    """
    if not speaker_id or speaker_id == "Unknown":
        return "Speaker"
    mapping = {
        "Guest-1": "Agent",
        "Guest-2": "Customer",
        "SPEAKER_00": "Agent",
        "SPEAKER_01": "Customer",
    }
    return mapping.get(speaker_id, speaker_id)


def _format_timestamp(offset_ticks: int) -> str:
    """Convert offset (in 100-nanosecond ticks or ms*10000) to HH:MM:SS format."""
    if not offset_ticks:
        return "00:00:00"
    total_seconds = offset_ticks / 10_000_000  # 100ns ticks -> seconds
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


# ─── Health check ─── #
@app.get("/health")
async def health():
    return {"status": "ok", "graph_ready": graph is not None}


# ─── Sarvam AI Real-Time STT WebSocket Proxy ─── #
# Based on official examples: github.com/sarvamai/sarvam-streaming-apis
import os
import base64
import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")


@app.websocket("/sarvam-stream")
async def sarvam_stream(websocket: WebSocket):
    """WebSocket proxy: Browser → Backend → Sarvam AI STT → Backend → Browser."""
    await websocket.accept()
    logger.info("🎙️ Sarvam STT: client connected")

    if not SARVAM_API_KEY or SARVAM_API_KEY == "your_sarvam_api_key_here":
        await websocket.send_json({"type": "error", "text": "SARVAM_API_KEY not configured"})
        await websocket.close()
        return

    logger.info(f"🎙️ Sarvam STT: API key loaded ({SARVAM_API_KEY[:8]}...)")

    # ── Sarvam V3 streaming WebSocket ──
    # Ref: sarvamai SDK v0.1.25 speech_to_text_streaming/client.py
    # with_diarization & num_speakers: SDK response model supports diarized_transcript
    # but connect() doesn't expose these params yet. Passing them as URL query params
    # since the API server may accept them (batch API equivalent: with_diarization=True).
    sarvam_url = (
        f"wss://api.sarvam.ai/speech-to-text/ws"
        f"?language-code=unknown"
        f"&model=saaras:v3"
        f"&mode=translit"
        f"&with_diarization=true"
        f"&num_speakers=2"
    )

    logger.info(f"🎙️ Sarvam STT: connecting to {sarvam_url}")

    sarvam_ws = None
    utterance_counter = 0  # Monotonically increasing offset for unique utterance IDs
    try:
        sarvam_ws = await websockets.connect(
            sarvam_url,
            additional_headers={"api-subscription-key": SARVAM_API_KEY},
        )
        logger.info("🎙️ Sarvam STT: connected to Sarvam API ✅")

        async def relay_sarvam_to_client():
            """Read messages from Sarvam and forward to browser.

            Key insight from Pipecat source & SDK: ALL Sarvam 'data' messages
            are FINAL utterances — there are no partial/interim results.
            The API also sends 'events' messages for VAD signals.
            """
            nonlocal utterance_counter
            try:
                async for msg in sarvam_ws:
                    try:
                        parsed = json.loads(msg) if isinstance(msg, str) else msg
                        msg_type = parsed.get("type", "")

                        # Log full response for debugging diarization
                        logger.info(f"🔍 Sarvam raw response: type={msg_type}, keys={list(parsed.get('data', {}).keys()) if isinstance(parsed.get('data'), dict) else 'N/A'}")

                        if msg_type == "data" and parsed.get("data"):
                            data = parsed["data"]
                            transcript = data.get("transcript", "")

                            if transcript and transcript.strip():
                                # Extract speaker from diarized_transcript if available
                                # SDK model: DiarizedTranscript has entries: List[DiarizedEntry]
                                # DiarizedEntry: {transcript, speaker_id, start_time_seconds, end_time_seconds}
                                speaker_id = None
                                diarized = data.get("diarized_transcript")
                                logger.info(f"🎯 diarized_transcript value: {json.dumps(diarized) if diarized else 'None/empty'}")
                                if diarized and isinstance(diarized, dict):
                                    # diarized_transcript may be {entries: [{speaker_id, transcript, ...}]}
                                    entries = diarized.get("entries")
                                    if entries and isinstance(entries, list) and len(entries) > 0:
                                        # Use the speaker_id from the first (or majority) entry
                                        speaker_id = entries[0].get("speaker_id")

                                # All Sarvam data messages are final (no partials)
                                utterance_counter += 1
                                await websocket.send_json({
                                    "type": "transcript",
                                    "text": transcript,
                                    "is_final": True,
                                    "speaker_id": speaker_id,
                                    "language_code": data.get("language_code", "unknown"),
                                    "utterance_id": utterance_counter,
                                })

                                logger.info(
                                    f"📝 FINAL #{utterance_counter} "
                                    f"[speaker={speaker_id or 'unknown'}]: "
                                    f"{transcript[:100]}"
                                )

                        elif msg_type == "events" and parsed.get("data"):
                            # VAD signals: START_SPEECH / END_SPEECH
                            signal = parsed["data"].get("signal_type", "")
                            logger.info(f"🔊 VAD signal: {signal}")
                            await websocket.send_json({
                                "type": "vad",
                                "signal": signal.lower(),
                            })

                        else:
                            # Forward errors etc.
                            await websocket.send_json(parsed)

                    except json.JSONDecodeError:
                        logger.warning(f"Sarvam non-JSON: {str(msg)[:100]}")
            except ConnectionClosedOK:
                logger.info("Sarvam STT: connection closed OK")
            except ConnectionClosed as e:
                logger.info(f"Sarvam STT: connection closed ({e.code})")
            except Exception as e:
                logger.error(f"Sarvam relay error: {e}", exc_info=True)

        # Start the relay task in the background
        relay_task = asyncio.create_task(relay_sarvam_to_client())

        # Read audio chunks from browser and forward to Sarvam
        # Audio format: raw PCM s16le 16kHz mono, base64-encoded
        chunk_count = 0
        try:
            while True:
                try:
                    raw_audio = await websocket.receive_bytes()
                except WebSocketDisconnect:
                    break

                chunk_count += 1
                audio_b64 = base64.b64encode(raw_audio).decode("utf-8")
                await sarvam_ws.send(json.dumps({
                    "audio": {
                        "data": audio_b64,
                        "sample_rate": 16000,
                        "encoding": "audio/wav",
                    }
                }))
                if chunk_count <= 3 or chunk_count % 50 == 0:
                    logger.info(f"Sent chunk #{chunk_count} ({len(raw_audio)} bytes)")
        finally:
            relay_task.cancel()

    except Exception as e:
        logger.error(f"🎙️ Sarvam STT error: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "text": str(e)})
        except Exception:
            pass
    finally:
        if sarvam_ws:
            try:
                await sarvam_ws.close()
            except Exception:
                pass
        logger.info(f"Sarvam STT: client disconnected (sent {chunk_count if 'chunk_count' in dir() else '?'} chunks)")



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
                
                # 🔄 Reset state for the next call on this connection
                call_transcript = []
                call_start_time = time.time()
                detected_intent = None
                detected_member = None
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
                    1 for k in ["date_of_incident", "location_of_incident", "incident_description", "cause_of_death", "caller_name"]
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
                if claim_type and knowledge_docs:
                    knowledge_docs = [
                        doc for doc in knowledge_docs
                        if doc.get("category", "") == "general" or doc.get("category", "") == claim_type
                    ]
                if knowledge_docs:
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


# _map_speaker and _format_timestamp are defined above (near line 60)


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
