"""
api/routes/voice.py — POST /voice Route
=========================================

Responsibility: read the uploaded audio file, delegate to VoiceService for
transcription, delegate to AgentService for the AI response, and return the
ChatResponse. Zero business logic lives here.

Design note: defined as ``def`` (not ``async def``) because both the Groq
Whisper call and the agent are synchronous blocking operations. FastAPI
offloads sync routes to a thread pool automatically.
"""

import time

from fastapi import APIRouter, File, UploadFile, status
from fastapi.responses import JSONResponse

from core.exceptions import VoiceTranscriptionError
from core.logger import get_logger
from models.response_models import ChatResponse, ErrorResponse

logger = get_logger(__name__)

voice_router = APIRouter()

# Injected at startup by main.py
_voice_service = None
_agent_service = None


def init_voice_router(voice_service, agent_service) -> None:
    """Inject VoiceService and AgentService dependencies after startup wiring."""
    global _voice_service, _agent_service
    _voice_service = voice_service
    _agent_service = agent_service


@voice_router.post(
    "/voice",
    response_model=ChatResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Empty or too-short recording",
        },
        415: {"model": ErrorResponse, "description": "Unsupported audio format"},
        422: {"model": ErrorResponse, "description": "No speech detected"},
        status.HTTP_502_BAD_GATEWAY: {
            "model": ErrorResponse,
            "description": "Whisper API failure",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "Voice service unavailable",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error",
        },
    },
    status_code=status.HTTP_200_OK,
    summary="Voice Query — Speech-to-Text + AI Agent",
    description=(
        "Accepts an audio file upload (webm, ogg, wav, mp4, m4a, mp3), "
        "transcribes it with Groq Whisper Large V3 Turbo, passes the transcription "
        "to the AI Support Agent, and returns a natural-language response. "
        "Voice output is handled client-side via the Browser SpeechSynthesis API."
    ),
)
def voice_endpoint(
    audio: UploadFile = File(
        ..., description="Recorded audio file from the browser MediaRecorder API"
    ),
) -> ChatResponse:
    """
    Voice pipeline endpoint. Bridges audio input to the text-based AI agent.

    Flow:
        1. Read audio bytes from the uploaded file.
        2. Delegate to VoiceService for Groq Whisper STT.
        3. Delegate to AgentService for the AI response.
        4. Return ChatResponse — same schema as POST /chat.
    """
    request_start = time.perf_counter()
    filename = audio.filename or "audio_upload"
    content_type = audio.content_type or "audio/webm"

    logger.info(
        "Voice request received | filename='%s' | content_type='%s'",
        filename,
        content_type,
    )

    # Step 1: Read audio bytes
    try:
        audio_bytes = audio.file.read()
    except Exception as read_err:
        logger.error("Failed to read uploaded audio file: %s", read_err, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error="File Read Error",
                detail="Failed to read the uploaded audio file. Please try again.",
                status_code=status.HTTP_400_BAD_REQUEST,
            ).model_dump(),
        )

    # Step 2: Transcribe via VoiceService
    try:
        transcription = _voice_service.transcribe(
            file_bytes=audio_bytes,
            content_type=content_type,
            original_filename=filename,
        )
    except VoiceTranscriptionError as vte:
        logger.warning("Voice transcription failed: %s", vte.message)
        return JSONResponse(
            status_code=vte.http_code,
            content=ErrorResponse(
                error="Transcription Error",
                detail=vte.message,
                status_code=vte.http_code,
            ).model_dump(),
        )

    logger.info("Transcription complete. Passing to agent: '%s'", transcription[:100])

    # Step 3: Process transcription through AgentService
    agent_start = time.perf_counter()
    response_text, sources = _agent_service.process(transcription)
    agent_elapsed = time.perf_counter() - agent_start
    total_elapsed = time.perf_counter() - request_start

    logger.info(
        "Voice pipeline complete | agent_time=%.2fs | total_time=%.2fs | sources=%s",
        agent_elapsed,
        total_elapsed,
        sources,
    )

    # Step 4: Return the standard ChatResponse
    return ChatResponse(
        response=response_text,
        session_id=None,   # Voice requests are stateless (no session tracking)
        sources=sources,
    )
