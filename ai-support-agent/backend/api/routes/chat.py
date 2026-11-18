"""
api/routes/chat.py — POST /chat Route
=======================================

Responsibility: validate the incoming ChatRequest, call AgentService.process(),
return the ChatResponse. Zero business logic lives here.

Design note: defined as ``def`` (not ``async def``) because AgentService calls
blocking I/O (Groq API, SQLite). FastAPI automatically offloads synchronous
route handlers to an internal thread pool, keeping the async event loop free
for concurrent requests.
"""

from fastapi import APIRouter, status

from core.logger import get_logger
from models.request_models import ChatRequest
from models.response_models import ChatResponse, ErrorResponse

logger = get_logger(__name__)

chat_router = APIRouter()

# Injected at startup by main.py
_agent_service = None


def init_chat_router(agent_service) -> None:
    """Inject the AgentService dependency after startup wiring."""
    global _agent_service
    _agent_service = agent_service


@chat_router.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": ErrorResponse,
            "description": "Validation failure",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error",
        },
    },
    status_code=status.HTTP_200_OK,
    summary="Process Customer Inquiry",
    description=(
        "Receives a customer support message, routes it through the AI agent "
        "(order lookup or RAG knowledge-base search), and returns a natural-language response."
    ),
)
def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """
    Public chat interface. Delegates entirely to AgentService.

    The route handler's only responsibilities are:
      1. Receive and validate the request (handled by Pydantic).
      2. Call the service.
      3. Build and return the response.
    """
    logger.info(
        "Chat request received | session_id='%s' | message_preview='%s'",
        request.session_id,
        request.message[:80],
    )

    response_text, sources = _agent_service.process(request.message)

    return ChatResponse(
        response=response_text,
        session_id=request.session_id,
        sources=sources,
    )
