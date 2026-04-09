# main.py — FastAPI backend with WebSocket dual-path processing + post-call evaluation

import re
import json
import logging
import time
import asyncio
import os
from contextlib import asynccontextmanager
import httpx

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv
load_dotenv()

from data.members import get_member, set_db_available
from agent.graph import build_graph
from services.extractor import extract_claim_facts, classify_intent, generate_stall_response
from services.evaluator import generate_post_call_evaluation
from data.knowledge import search_knowledge, get_compliance_alerts, warmup as warmup_knowledge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("call-intelligence")

# ─── Build the LangGraph at startup ─── #
graph = None

# ─── DB availability flag ─── #
_db_ready = False

# ─── Global HTTP Client for TTS (persisted logic) ─── #
_tts_client = None

DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph, _db_ready, _tts_client
    logger.info("🚀 Building LangGraph pipeline...")
    graph = build_graph()
    logger.info("✅ LangGraph ready.")
    logger.info("🔥 Pre-loading knowledge module...")
    warmup_knowledge()
    
    # Initialize persistent HTTPX client for TTS (improves latency significantly)
    _tts_client = httpx.AsyncClient(timeout=15.0)
    
    logger.info("✅ Server is live.")

    # ─── Initialize PostgreSQL connection pool ─── #
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        try:
            from db.connection import init_pool
            await init_pool()
            _db_ready = True
            set_db_available(True)
            logger.info("✅ PostgreSQL connected and ready")
        except Exception as e:
            logger.warning(f"⚠️ PostgreSQL init failed — running without DB: {e}")
            _db_ready = False
            set_db_available(False)
    else:
        logger.warning("⚠️ DATABASE_URL not set — running with in-memory data only")
        _db_ready = False
        set_db_available(False)

    yield

    # ─── Cleanup ─── #
    if _db_ready:
        from db.connection import close_pool
        await close_pool()
        
    if _tts_client:
        await _tts_client.aclose()
        
    logger.info("🛑 Server shutting down.")


app = FastAPI(
    title="CallIQ",
    description="Real-time FNOL call intelligence with post-call evaluation",
    version="3.0.0",
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
    return {"status": "ok", "graph_ready": graph is not None, "db_ready": _db_ready, "dev_mode": DEV_MODE}


# ─── Deepgram Token Endpoint ─── #
import httpx

@app.get("/api/deepgram-token")
async def get_deepgram_token():
    """
    Return the Deepgram API key for the frontend to connect directly
    to Deepgram's WebSocket API.
    """
    deepgram_key = os.getenv("DEEPGRAM_API_KEY", "")
    if not deepgram_key:
        return JSONResponse({"error": "DEEPGRAM_API_KEY not configured on the server"}, status_code=500)
    return {"token": deepgram_key}


# ─── Azure TTS Endpoint ─── #

@app.post("/api/azure-tts")
async def azure_tts(request: Request):
    """
    Synthesize speech using Azure Speech Service.
    Supports Hindi (hi-IN) and English (en-US) with native neural voices.
    Accepts JSON: { "text": "...", "language": "hi" | "en" }
    Returns audio/mpeg stream.
    """
    speech_key = os.getenv("AZURE_SPEECH_KEY", "")
    speech_region = os.getenv("AZURE_SPEECH_REGION", "eastus")

    if not speech_key:
        return JSONResponse({"error": "AZURE_SPEECH_KEY not configured"}, status_code=500)

    body = await request.json()
    text = body.get("text", "").strip()
    language = body.get("language", "en").strip().lower()

    if not text:
        return JSONResponse({"error": "No text provided"}, status_code=400)

    # Select voice and lang tag based on detected language
    if language.startswith("hi"):
        voice_name = "hi-IN-SwaraNeural"
        lang_tag = "hi-IN"
    else:
        voice_name = "en-US-JennyNeural"
        lang_tag = "en-US"

    # Build SSML
    ssml = (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{lang_tag}">'
        f'<voice name="{voice_name}">{text}</voice>'
        f'</speak>'
    )

    endpoint = f"https://{speech_region}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": speech_key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-16khz-32kbitrate-mono-mp3", # Lower bitrate to reduce latency
        "User-Agent": "CallIQ-TTS",
    }

    try:
        if _tts_client:
            resp = await _tts_client.post(endpoint, headers=headers, content=ssml.encode("utf-8"))
        else:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(endpoint, headers=headers, content=ssml.encode("utf-8"))

        if resp.status_code != 200:
            logger.error(f"Azure TTS error: {resp.status_code} — {resp.text[:200]}")
            return JSONResponse(
                {"error": f"Azure TTS failed: {resp.status_code}"},
                status_code=502,
            )

        from fastapi.responses import Response
        return Response(
            content=resp.content,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline"},
        )
    except Exception as e:
        logger.error(f"Azure TTS request error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ══════════════════════════════════════════════
# REST API — User, Calls, Evaluations, Teams
# ══════════════════════════════════════════════

@app.get("/api/me")
async def get_me(request: Request):
    """Get current user profile from Clerk JWT."""
    from middleware.auth import get_current_user
    try:
        user = await get_current_user(request)
        # If DB is ready, upsert the user record
        if _db_ready:
            from db.queries import upsert_user
            await upsert_user(
                clerk_user_id=user["clerk_user_id"],
                name=user["name"],
                email=user["email"],
                role=user["role"],
                team_id=user["team_id"],
            )
        return user
    except Exception as e:
        logger.error(f"Error in /api/me: {e}")
        return JSONResponse({"error": str(e)}, status_code=401)


@app.get("/api/calls")
async def get_calls_endpoint(
    request: Request,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    claim_type: str = Query(default=None),
):
    """Get call history filtered by user role. Optional claim_type filter for pagination."""
    if not _db_ready:
        return JSONResponse({"error": "Database not configured"}, status_code=503)

    from middleware.auth import get_current_user
    from db.queries import get_calls
    user = await get_current_user(request)
    calls = await get_calls(
        agent_id=user["clerk_user_id"],
        team_id=user["team_id"],
        role=user["role"],
        limit=limit,
        offset=offset,
        claim_type=claim_type,
    )
    return {"calls": calls, "total": len(calls)}


@app.get("/api/calls/{call_id}")
async def get_call_detail(call_id: int, request: Request):
    """Get a single call with its full evaluation."""
    if not _db_ready:
        return JSONResponse({"error": "Database not configured"}, status_code=503)

    from middleware.auth import get_current_user
    from db.queries import get_call_with_evaluation
    user = await get_current_user(request)
    call = await get_call_with_evaluation(
        call_id=call_id,
        agent_id=user["clerk_user_id"],
        team_id=user["team_id"],
        role=user["role"],
    )
    if not call:
        return JSONResponse({"error": "Call not found or access denied"}, status_code=404)
    return call


@app.delete("/api/calls/{call_id}")
async def delete_call_endpoint(call_id: int, request: Request):
    """Delete a call and its evaluation. Agents can only delete their own."""
    if not _db_ready:
        return JSONResponse({"error": "Database not configured"}, status_code=503)

    from middleware.auth import get_current_user
    from db.queries import delete_call
    user = await get_current_user(request)
    deleted = await delete_call(
        call_id=call_id,
        agent_id=user["clerk_user_id"],
        role=user["role"],
    )
    if not deleted:
        return JSONResponse({"error": "Call not found or access denied"}, status_code=404)
    return {"success": True}


@app.get("/api/evaluations/summary")
async def get_eval_summary(request: Request):
    """Get aggregate evaluation stats for the current user's scope."""
    if not _db_ready:
        return JSONResponse({"error": "Database not configured"}, status_code=503)

    from middleware.auth import get_current_user
    from db.queries import get_evaluation_summary
    user = await get_current_user(request)
    summary = await get_evaluation_summary(
        agent_id=user["clerk_user_id"],
        team_id=user["team_id"],
        role=user["role"],
    )
    return summary


@app.get("/api/team/members")
async def get_team_members_endpoint(request: Request):
    """Get team members (team_lead / manager only)."""
    if not _db_ready:
        return JSONResponse({"error": "Database not configured"}, status_code=503)

    from middleware.auth import get_current_user
    from db.queries import get_team_members, get_all_teams, get_team_performance
    user = await get_current_user(request)

    if user["role"] == "agent":
        return JSONResponse({"error": "Access denied"}, status_code=403)

    if user["role"] == "manager":
        teams = await get_all_teams()
        performance = await get_team_performance()
        return {"teams": teams, "agents": performance}
    else:
        # Team lead — their team only
        members = await get_team_members(user["team_id"]) if user["team_id"] else []
        performance = await get_team_performance(user["team_id"]) if user["team_id"] else []
        return {"members": members, "agents": performance}


@app.get("/api/team/performance")
async def get_team_performance_endpoint(request: Request, team_id: str = Query(default=None)):
    """Get per-agent performance stats."""
    if not _db_ready:
        return JSONResponse({"error": "Database not configured"}, status_code=503)

    from middleware.auth import get_current_user
    from db.queries import get_team_performance
    user = await get_current_user(request)

    if user["role"] == "agent":
        return JSONResponse({"error": "Access denied"}, status_code=403)

    if user["role"] == "team_lead":
        team_id = user["team_id"]

    performance = await get_team_performance(team_id)
    return {"agents": performance}


@app.get("/api/team/agent/{clerk_id}/calls")
async def get_agent_calls_endpoint(clerk_id: str, request: Request):
    """Get a specific agent's call records and summary stats (team_lead / manager only)."""
    if not _db_ready:
        return JSONResponse({"error": "Database not configured"}, status_code=503)

    from middleware.auth import get_current_user
    from db.queries import get_agent_calls_for_team
    user = await get_current_user(request)

    if user["role"] == "agent":
        return JSONResponse({"error": "Access denied"}, status_code=403)

    team_id = user["team_id"] if user["role"] == "team_lead" else None
    result = await get_agent_calls_for_team(clerk_id, team_id, limit=10)
    return result


# ══════════════════════════════════════════════
# DEV ENDPOINTS — Only available when DEV_MODE=true
# ══════════════════════════════════════════════

@app.post("/api/dev/clear-history")
async def dev_clear_history():
    """Clear all call history and evaluations. Dev mode only."""
    if not DEV_MODE:
        return JSONResponse({"error": "Not found"}, status_code=404)
    if not _db_ready:
        return JSONResponse({"error": "Database not configured"}, status_code=503)

    from db.queries import clear_call_history
    count = await clear_call_history()
    return {"cleared": count, "message": f"Deleted {count} call records and their evaluations"}


@app.post("/api/dev/clear-evaluations")
async def dev_clear_evaluations():
    """Clear all evaluations only. Dev mode only."""
    if not DEV_MODE:
        return JSONResponse({"error": "Not found"}, status_code=404)
    if not _db_ready:
        return JSONResponse({"error": "Database not configured"}, status_code=503)

    from db.queries import clear_evaluations
    count = await clear_evaluations()
    return {"cleared": count, "message": f"Deleted {count} evaluation records"}


@app.get("/api/dev/stats")
async def dev_stats():
    """Get DB table counts. Dev mode only."""
    if not DEV_MODE:
        return JSONResponse({"error": "Not found"}, status_code=404)
    if not _db_ready:
        return JSONResponse({"error": "Database not configured"}, status_code=503)

    from db.queries import get_db_stats
    stats = await get_db_stats()
    return {"stats": stats, "dev_mode": True}


# ─── WebSocket helpers ─── #
async def safe_send(websocket: WebSocket, data: dict) -> bool:
    """Send JSON to WebSocket with error protection. Returns False if connection is lost."""
    try:
        await websocket.send_json(data)
        return True
    except (WebSocketDisconnect, Exception) as e:
        logger.warning(f"WebSocket send failed (client likely disconnected): {e}")
        return False


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
    detected_member = None
    accumulated_facts: dict = {}  # Persistent fact state across the entire call
    proactive_kb_sent = False  # Track whether we already sent knowledge docs to frontend
    last_knowledge_docs: list[dict] = []
    last_compliance_alerts: list[dict] = []  # Track pre-fetched compliance alerts
    intent_stable_count: int = 0  # Counter for early-exit intent classification
    utterance_count: int = 0  # Total finalized customer utterances for periodic re-classification
    ws_alive = True  # Track WebSocket connection state
    agent_clerk_id: str | None = None  # Clerk user ID for the agent on this call
    last_searched_claim_type: str | None = None  # Track when claim type changes to re-search KB

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            msg_type = data.get("type", "transcript")

            # ═══════════════════════════════════════════
            # 🔑 AUTH — Set agent identity for call persistence
            # ═══════════════════════════════════════════
            if msg_type == "auth":
                agent_clerk_id = data.get("clerk_user_id")
                logger.info(f"🔑 Agent authenticated: {agent_clerk_id}")
                continue

            # ═══════════════════════════════════════════
            # 📋 END CALL — Generate post-call evaluation
            # ═══════════════════════════════════════════
            if msg_type == "end_call":
                logger.info("📋 Call ended — generating post-call evaluation...")
                ws_alive = await safe_send(websocket, {
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
                    claim_type=claim_type,
                    knowledge_docs=last_knowledge_docs,
                )

                # Attach FNOL form data for the frontend
                evaluation["fnol_data"] = {
                    "facts": accumulated_facts,
                    "member": detected_member,
                    "intent": detected_intent,
                }

                await safe_send(websocket, {
                    "type": "post_call_evaluation",
                    "data": evaluation,
                })
                logger.info("📋 Post-call evaluation sent")

                # ─── Persist call + evaluation to DB (async, non-blocking) ─── #
                if _db_ready and agent_clerk_id:
                    try:
                        from db.queries import save_call, save_evaluation
                        policy_id = detected_member.get("policyId") if detected_member else None
                        call_id = await save_call(
                            agent_id=agent_clerk_id,
                            policy_id=policy_id,
                            duration_secs=int(call_duration),
                            intent=detected_intent,
                            claim_type=claim_type,
                            transcript=call_transcript,
                            accumulated_facts=accumulated_facts,
                            member_data=detected_member,
                        )
                        await save_evaluation(call_id, evaluation)
                        logger.info(f"💾 Call #{call_id} persisted to database")
                    except Exception as e:
                        logger.error(f"❌ Failed to persist call to DB: {e}")
                
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
                detected_member = None
                proactive_kb_sent = False
                last_knowledge_docs = []
                last_compliance_alerts = []
                accumulated_facts = {}
                intent_stable_count = 0
                utterance_count = 0
                last_searched_claim_type = None
                ws_alive = True
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
            ws_alive = await safe_send(websocket, {
                "type": "transcript",
                "data": {
                    "text": text,
                    "is_finalized": is_finalized,
                    "speaker": speaker_label,
                    "timestamp": _format_timestamp(offset),
                    "offset": offset,
                },
            })
            if not ws_alive:
                break

            # ═══════════════════════════════════════════
            # ⚡ FAST PATH — Regex policy ID / phone extraction
            # ═══════════════════════════════════════════
            policy_match = POLICY_REGEX.search(text)
            if policy_match:
                # Reconstruct standardized ID (e.g. CAR-100001) regardless of spaces
                policy_id = f"{policy_match.group(1).upper()}-{policy_match.group(2)}"
                member = await get_member(policy_id=policy_id)
                if member:
                    detected_member = member
                    await websocket.send_json({
                        "type": "member_profile",
                        "data": member,
                    })
                    logger.info(f"⚡ Fast path: sent profile for {policy_id}")
                else:
                    logger.info(f"⚡ Fast path: no member found for {policy_id}")
                    await safe_send(websocket, {
                        "type": "member_lookup_status",
                        "data": {"status": "failed", "message": f"Could not find policy {policy_id}. Please verify."},
                    })

            # ⚡ Phone number fast path — try regex phone match if no member yet
            if not detected_member:
                phone_match = PHONE_REGEX.search(text)
                if phone_match:
                    phone_raw = phone_match.group(0)
                    member = await get_member(phone=phone_raw)
                    if member:
                        detected_member = member
                        await websocket.send_json({
                            "type": "member_profile",
                            "data": member,
                        })
                        logger.info(f"⚡ Fast path (phone): sent profile for {phone_raw}")
                    else:
                        logger.info(f"⚡ Fast path (phone): no member found for {phone_raw}")
                        await safe_send(websocket, {
                            "type": "member_lookup_status",
                            "data": {"status": "failed", "message": f"Could not find account for phone {phone_raw}."},
                        })

            # ═══════════════════════════════════════════
            # 🧠 SLOW PATH — LangGraph (only on finalized)
            # ═══════════════════════════════════════════
            # Only trigger AI analysis and suggest new responses if the Customer is speaking.
            # If the Agent is speaking, they do not need a new script generated based on their own words.
            if is_finalized and graph and speaker_label != "Agent":
                await safe_send(websocket, {
                    "type": "processing",
                    "data": {"message": "Analyzing transcript..."},
                })

                # ── Stall Agent setup ──
                # Fires in two scenarios:
                #   1. First customer utterance → empathetic filler (before Phase 1)
                #   2. Claim type changes mid-call → transitional filler (after Phase 1)
                # Runs as a parallel task with no shared mutable state.
                # Awaited before ReAct to guarantee no interleaved suggestion_chunks.
                stall_task = None
                stall_text_parts: list[str] = []
                kb_was_cached = proactive_kb_sent  # Snapshot before Phase 1 may flip it

                # Scenario 1: First customer utterance — empathetic stall
                if utterance_count == 0:
                    async def _run_stall(
                        _ws=websocket, _text=text, _parts=stall_text_parts,
                    ):
                        try:
                            await safe_send(_ws, {"type": "suggestion_stale", "data": {}})
                            async for token in generate_stall_response(_text, is_opening=True):
                                _parts.append(token)
                                alive = await safe_send(_ws, {
                                    "type": "suggestion_chunk",
                                    "data": {"text": token},
                                })
                                if not alive:
                                    return
                        except Exception as e:
                            logger.warning(f"⏳ Stall agent error (non-blocking): {e}")

                    stall_task = asyncio.create_task(_run_stall())
                    logger.info("⏳ Stall agent fired — first customer utterance")

                # Build full transcript string
                formatted_transcript = "\n".join(
                    f"[{line['speaker']} {line['timestamp']}]: \"{line['text']}\""
                    for line in call_transcript
                )

                # Build sliding window transcript for fact extraction (last 10 utterances)
                # This keeps input tokens bounded as the call grows longer
                window_size = 10
                windowed_lines = call_transcript[-window_size:]
                windowed_transcript = "\n".join(
                    f"[{line['speaker']} {line['timestamp']}]: \"{line['text']}\""
                    for line in windowed_lines
                )
                # Prepend accumulated facts summary so the extractor has context
                facts_context = ""
                if accumulated_facts:
                    known_facts = [f"{k}: {v}" for k, v in accumulated_facts.items() if v is not None]
                    if known_facts:
                        facts_context = "Previously extracted facts: " + "; ".join(known_facts) + "\n\n"
                windowed_transcript_with_context = facts_context + windowed_transcript

                # ── Phase 1: Intent classification (+ early-exit with periodic re-check) ──
                utterance_count += 1
                should_classify = (
                    intent_stable_count < 3  # Not yet stabilized
                    or utterance_count % 10 == 0  # Periodic re-check every 10th utterance
                )

                if should_classify:
                    intent_res = await classify_intent(formatted_transcript)
                    new_intent = intent_res.get("intent")
                    new_claim_type = intent_res.get("claim_type")
                    
                    if intent_stable_count >= 3:
                        # Re-check after stabilization: only act if intent actually changed
                        if new_intent != detected_intent:
                            logger.info(
                                f"Intent changed from '{detected_intent}' to '{new_intent}' "
                                f"at utterance {utterance_count} -- re-engaging classification"
                            )
                            intent_stable_count = 1
                            detected_intent = new_intent
                            claim_type = new_claim_type
                            proactive_kb_sent = False  # Force KB re-search for new topic
                        else:
                            logger.info(
                                f"Periodic re-check at utterance {utterance_count}: "
                                f"intent unchanged ('{detected_intent}')"
                            )
                    else:
                        # Normal stabilization tracking
                        if new_intent == detected_intent:
                            intent_stable_count += 1
                        else:
                            intent_stable_count = 1
                        
                        detected_intent = new_intent
                        claim_type = new_claim_type
                        
                        # Re-search KB when claim type changes
                        if claim_type and claim_type != last_searched_claim_type:
                            proactive_kb_sent = False
                            logger.info(f"Claim type changed to '{claim_type}' -- will re-search knowledge base")
                        
                        if intent_stable_count >= 3:
                            logger.info(f"Intent stabilized as '{detected_intent}' -- will re-check every 10th utterance")
                else:
                    logger.info(f"Skipping intent classification (stable: {detected_intent}, utterance #{utterance_count})")

                # Scenario 2: Claim type just changed mid-call → transitional stall
                # Detected by: KB was cached before Phase 1 but is no longer (claim type changed)
                if not stall_task and kb_was_cached and not proactive_kb_sent:
                    async def _run_stall_mid(
                        _ws=websocket, _text=text, _parts=stall_text_parts,
                    ):
                        try:
                            await safe_send(_ws, {"type": "suggestion_stale", "data": {}})
                            async for token in generate_stall_response(_text, is_opening=False):
                                _parts.append(token)
                                alive = await safe_send(_ws, {
                                    "type": "suggestion_chunk",
                                    "data": {"text": token},
                                })
                                if not alive:
                                    return
                        except Exception as e:
                            logger.warning(f"⏳ Stall agent error (non-blocking): {e}")

                    stall_task = asyncio.create_task(_run_stall_mid())
                    logger.info("⏳ Stall agent fired — claim type changed, fetching new KB docs")

                # ── Phase 2: Fact extraction, knowledge search, and compliance — in parallel ──
                parallel_tasks = [
                    extract_claim_facts(windowed_transcript_with_context),  # Sliding window
                ]

                # Only search knowledge if we haven't already sent docs to frontend
                if not proactive_kb_sent and claim_type:
                    search_query = f"{claim_type} claim procedures requirements coverage"
                    parallel_tasks.append(
                        asyncio.to_thread(search_knowledge, search_query, claim_type, 5)
                    )
                else:
                    async def _return_cached_knowledge():
                        return last_knowledge_docs
                    parallel_tasks.append(_return_cached_knowledge())

                # Pre-fetch compliance alerts (avoids tool call round-trip in ReAct loop)
                if detected_intent:
                    compliance_query_transcript = text  # Use current utterance for compliance check
                    parallel_tasks.append(
                        asyncio.to_thread(get_compliance_alerts, detected_intent, compliance_query_transcript)
                    )
                else:
                    async def _return_empty_alerts():
                        return []
                    parallel_tasks.append(_return_empty_alerts())

                extracted_data = await asyncio.gather(*parallel_tasks)
                
                new_facts = extracted_data[0]
                knowledge_docs = extracted_data[1]
                compliance_alerts = extracted_data[2]

                # Merge new facts into accumulated state — non-null values always win
                for key, val in new_facts.items():
                    if val is not None:
                        accumulated_facts[key] = val

                # Try to fetch member from accumulated facts if not already detected
                if not detected_member:
                    policy_id = accumulated_facts.get("policy_number")
                    phone = accumulated_facts.get("caller_phone")
                    if policy_id or phone:
                        member = await get_member(policy_id=policy_id, phone=phone)
                        if member:
                            detected_member = member
                            logger.info(f"🧠 Slow path: Found member via accumulated facts")
                            await safe_send(websocket, {
                                "type": "member_profile",
                                "data": member,
                            })

                logger.info(f"📋 Accumulated facts: {accumulated_facts}")
                logger.info(f"📚 Pre-fetched {len(knowledge_docs)} knowledge docs, {len(compliance_alerts)} compliance alerts")

                # Track knowledge/compliance docs for post-call eval
                if knowledge_docs:
                    last_knowledge_docs = knowledge_docs
                if compliance_alerts:
                    last_compliance_alerts = compliance_alerts

                # Send intent to frontend
                if detected_intent:
                    await safe_send(websocket, {
                        "type": "intent",
                        "data": {
                            "intent": detected_intent,
                            "claim_type": claim_type,
                        },
                    })
                    
                    # Send pre-fetched knowledge to frontend immediately
                    if knowledge_docs and not proactive_kb_sent:
                        proactive_kb_sent = True
                        last_searched_claim_type = claim_type
                        await safe_send(websocket, {
                            "type": "knowledge",
                            "data": knowledge_docs,
                        })
                        logger.info(f"⚡ Sent {len(knowledge_docs)} knowledge docs to frontend for {claim_type}.")

                    # Send pre-fetched compliance alerts to frontend
                    if compliance_alerts:
                        await safe_send(websocket, {
                            "type": "compliance",
                            "data": compliance_alerts,
                        })
                        logger.info(f"⚡ Sent {len(compliance_alerts)} compliance alerts to frontend.")

                # Aggregate detected languages across recent customer utterances
                # to avoid STT hallucinations on short words (e.g., "okay" tagged as Spanish).
                # DUAL SIGNAL:
                #   1. Long-term voting (last 10 utterances, ≥30%) — stability
                #   2. Short-term recency (last 3 utterances, ≥2)  — quick adaptation
                lang_counts: dict[str, int] = {}
                recent_langs: list[list[str]] = []   # last 3 utterances' language lists
                customer_utterance_count = 0
                for line in reversed(call_transcript):
                    if line["speaker"] == "Customer" and line.get("languages"):
                        customer_utterance_count += 1
                        if len(recent_langs) < 3:
                            recent_langs.append(line["languages"])
                        for lang in line["languages"]:
                            lang_counts[lang] = lang_counts.get(lang, 0) + 1
                    if customer_utterance_count >= 10:
                        break

                # Signal 1: Long-term — languages in ≥30% of sampled utterances
                threshold = max(1, customer_utterance_count * 0.3)
                longterm_langs = {lang for lang, cnt in lang_counts.items() if cnt >= threshold}

                # Signal 2: Short-term — languages in ≥2 of the last 3 utterances
                recent_counts: dict[str, int] = {}
                for langs in recent_langs:
                    for lang in langs:
                        recent_counts[lang] = recent_counts.get(lang, 0) + 1
                shortterm_langs = {lang for lang, cnt in recent_counts.items() if cnt >= 2}

                # Union of both signals: stable AND responsive to switches
                customer_languages = sorted(
                    longterm_langs | shortterm_langs,
                    key=lambda l: lang_counts.get(l, 0),
                    reverse=True,
                )
                # Always include English as a baseline
                if "en" not in customer_languages:
                    customer_languages.append("en")

                # ── Await stall agent before streaming real suggestion ──
                # The stall (~200ms) is certainly done by now (Phase 1+2 took ~1-2s),
                # but we await explicitly to guarantee no suggestion_chunk interleaving.
                stall_response_text = None
                if stall_task:
                    try:
                        await asyncio.wait_for(stall_task, timeout=3.0)
                    except asyncio.TimeoutError:
                        stall_task.cancel()
                        logger.warning("⏳ Stall agent timed out — proceeding with main suggestion")
                    except Exception:
                        pass  # Stall errors are non-blocking
                    stall_response_text = "".join(stall_text_parts) if stall_text_parts else None
                    if stall_response_text:
                        logger.info(f"⏳ Stall response sent ({len(stall_response_text)} chars) — main suggestion will skip empathy")

                # 2. Setup state for ReAct Agent — knowledge + compliance injected into prompt
                state = {
                    "transcript": text,
                    "full_transcript": formatted_transcript,
                    "is_finalized": True,
                    "intent": detected_intent,
                    "claim_type": claim_type,
                    "member_data": detected_member,
                    "accumulated_facts": accumulated_facts,
                    "knowledge_docs": knowledge_docs,  # Pre-fetched, injected into system prompt
                    "compliance_alerts": compliance_alerts,  # Pre-fetched, injected into system prompt
                    "caller_languages": customer_languages,  # Detected languages for multilingual support
                    "stall_response_sent": stall_response_text,  # Avoid double-empathy in ReAct
                    "messages": []  # Empty on start, populated by graph iteratively
                }

                # Transition from stall → real suggestion:
                # ALWAYS send suggestion_stale before the real suggestion.
                # This tells the frontend to discard the stall filler text from
                # its TTS building ref, so only the real suggestion gets spoken.
                # The stall text served its purpose (visual filler while processing).
                await safe_send(websocket, {
                    "type": "suggestion_stale",
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
                            ws_alive = await safe_send(websocket, {
                                "type": "suggestion_chunk",
                                "data": {"text": chunk.content},
                            })
                            if not ws_alive:
                                break

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
                            
                        await safe_send(websocket, {
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

                            if name == "lookup_policyholder" and tool_data:
                                if "status" not in tool_data:
                                    # Found a valid member profile
                                    detected_member = tool_data
                                    await safe_send(websocket, {
                                        "type": "member_profile",
                                        "data": detected_member,
                                    })
                                else:
                                    # Not found
                                    await safe_send(websocket, {
                                        "type": "member_lookup_status",
                                        "data": {"status": "failed", "message": tool_data.get("message", "Lookup failed. Please verify the information.")}
                                    })
                            elif name == "search_knowledge_base" and tool_data.get("results"):
                                await safe_send(websocket, {
                                    "type": "knowledge",
                                    "data": tool_data["results"],
                                })
                            elif name == "check_compliance_rules" and tool_data.get("alerts"):
                                await safe_send(websocket, {
                                    "type": "compliance",
                                    "data": tool_data["alerts"],
                                })
                        except Exception as e:
                            logger.error(f"Failed to parse tool output from {name}: {e}")

                # Ping frontend that suggestion has fully completed generating
                await safe_send(websocket, {
                    "type": "suggestion_complete",
                    "data": {},
                })

                logger.info("🧠 Slow path: Stream complete.")

    except WebSocketDisconnect:
        logger.info("📞 WebSocket disconnected")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}", exc_info=True)
        try:
            await safe_send(websocket, {
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
    if seconds_value is None:
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
