from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import json
import asyncio
import logging
import base64
import time

from app.core.db import AsyncSessionLocal
from app.core.models import User, VoiceProfile, SystemAnalytics
from app.core.security import verify_access_token
from app.core.agents.orchestrator import AgentOrchestrator

router = APIRouter(prefix="/voice", tags=["Voice Platform"])
logger = logging.getLogger("lingosphere.voice")

# ==========================================
# WS AUTHENTICATION HELPER
# ==========================================
async def get_ws_user(token: str, db: AsyncSession) -> User:
    payload = verify_access_token(token)
    if not payload:
        return None
    email = payload.get("sub")
    res = await db.execute(select(User).filter(User.email == email))
    return res.scalars().first()

# ==========================================
# WEBSOCKET STREAMING ENDPOINT
# ==========================================
@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Voice stream WebSocket connected")
    
    user = None
    voice_speed = 1.0
    voice_tone = "default"
    
    db = AsyncSessionLocal()
    
    try:
        # First message must be authentication
        auth_msg = await websocket.receive_text()
        auth_data = json.loads(auth_msg)
        token = auth_data.get("token")
        
        user = await get_ws_user(token, db)
        if not user:
            await websocket.send_json({"event": "error", "message": "Unauthorized token"})
            await websocket.close()
            return
            
        # Get Voice Profile details for synthesis speed/tone adjusting
        prof_res = await db.execute(select(VoiceProfile).filter(VoiceProfile.user_id == user.id))
        voice_prof = prof_res.scalars().first()
        if voice_prof:
            voice_speed = voice_prof.speech_speed
            voice_tone = voice_prof.voice_tone
            logger.info(f"Loaded voice profile for {user.email}: speed={voice_speed}, tone={voice_tone}")
            
        await websocket.send_json({
            "event": "session_ready",
            "voice_preferences": {
                "speed": voice_speed,
                "tone": voice_tone,
                "age_mode": voice_prof.age_mode if voice_prof else "standard"
            }
        })
        
        # Audio streaming loops
        while True:
            # We support both Text configurations and binary audio chunk payloads
            message = await websocket.receive()
            
            start_time = time.time()
            
            if "text" in message:
                data = json.loads(message["text"])
                event = data.get("event")
                
                # Check for interruption command
                if event == "interrupt":
                    logger.info("Speech playback interrupted by user action")
                    await websocket.send_json({"event": "interrupted"})
                    continue
                
                # Process simulated speech text trigger
                if event == "audio_transcript":
                    transcript = data.get("text", "")
                    session_id = data.get("session_id", "default_session")
                    
                    logger.info(f"Received voice transcription: '{transcript}'")
                    
                    # Process query using the multi-agent system
                    agent_res = await AgentOrchestrator.route_and_execute(
                        user_query=transcript,
                        user_id=user.id,
                        session_id=session_id
                    )
                    
                    # Simulate speech synthesis (TTS)
                    # We send a mock low-latency response payload containing:
                    # - The synthesized text
                    # - Mock audio binary representation (base64)
                    # - Time taken (latency metrics)
                    latency = (time.time() - start_time) * 1000.0 # ms
                    
                    # Create simulated sine-wave speech audio frames (just a few bytes for demo stability)
                    mock_audio_bytes = b"MOCK_WAV_AUDIO_HEADER_DATA_STREAM" + (b"\x00\xFF" * 100)
                    mock_audio_b64 = base64.b64encode(mock_audio_bytes).decode("utf-8")
                    
                    # Log voice quality telemetry
                    db.add(SystemAnalytics(
                        event_type="asr_wer",
                        metric_name="asr_simulated_wer",
                        metric_value=0.05, # 5% Word Error Rate
                    ))
                    db.add(SystemAnalytics(
                        event_type="api_latency",
                        metric_name="voice_roundtrip_ms",
                        metric_value=latency,
                    ))
                    await db.commit()
                    
                    # Stream synthesized audio packet
                    await websocket.send_json({
                        "event": "speech_synthesis",
                        "text": agent_res["content"],
                        "audio": mock_audio_b64,
                        "agent": agent_res["routed_agent"],
                        "latency_ms": latency
                    })
                    
            elif "bytes" in message:
                # Received raw audio packet (PCM/WAV)
                audio_chunk = message["bytes"]
                # Simulated low latency ASR processing
                # In a real environment, this chunk feeds into an online speech recognizer
                # For development, we acknowledge receipt of the chunk to simulate active speech detection
                await asyncio.sleep(0.01) # 10ms processing latency simulation
                
    except WebSocketDisconnect:
        logger.info("Voice stream WebSocket disconnected normally")
    except Exception as e:
        logger.error(f"Voice WebSocket Error: {e}")
    finally:
        await db.close()
