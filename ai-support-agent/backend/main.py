"""
main.py — Application Entry Point
===================================

This file has exactly one job: wire the application together and hand it to
the framework. It creates the FastAPI app, loads configuration, initialises
all services, registers routers, and defines lifecycle hooks.

No business logic, no SQL, no LLM calls, no prompt strings live here.

Startup sequence:
    1. ConfigManager loads .env and validates required variables.
    2. Services are instantiated (dependency wiring).
    3. FastAPI app is created with metadata.
    4. CORS middleware is registered.
    5. Global exception handlers are registered.
    6. Route handlers are registered with their injected dependencies.
    7. Startup event pre-warms the embedding model and ChromaDB.
"""

import os
import sys

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from groq import Groq

# ---------------------------------------------------------------------------
# Path resolution — ensures all sub-packages are importable regardless of
# the working directory from which uvicorn is launched.
# ---------------------------------------------------------------------------
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# ---------------------------------------------------------------------------
# Core infrastructure
# ---------------------------------------------------------------------------
from core.config import ConfigManager
from core.logger import get_logger

# ---------------------------------------------------------------------------
# Service & repository imports
# ---------------------------------------------------------------------------
from database.sqlite_manager import DatabaseManager
from repositories.order_repository import OrderRepository
from repositories.vector_repository import VectorRepository
from services.agent_service import AgentService
from services.embedding_service import EmbeddingService
from services.health_service import HealthService
from services.llm_service import LLMService
from services.rag_service import RAGService
from services.voice_service import VoiceService

# ---------------------------------------------------------------------------
# Route imports
# ---------------------------------------------------------------------------
from api.routes.chat import chat_router, init_chat_router
from api.routes.health import health_router
from api.routes.voice import init_voice_router, voice_router

# ---------------------------------------------------------------------------
# Model imports (for exception handlers)
# ---------------------------------------------------------------------------
from models.response_models import ErrorResponse

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = get_logger("backend.main")

# ---------------------------------------------------------------------------
# Configuration — loaded once, shared across the entire process
# ---------------------------------------------------------------------------
config = ConfigManager.get()

# ---------------------------------------------------------------------------
# Database & schema initialisation
# ---------------------------------------------------------------------------
db_manager = DatabaseManager(db_path=config.database_path)
db_manager.initialize()

# ---------------------------------------------------------------------------
# Repository layer
# ---------------------------------------------------------------------------
order_repo = OrderRepository(db_path=config.database_path)
vector_repo = VectorRepository(
    chroma_db_path=config.chroma_db_path,
    collection_name=config.chroma_collection_name,
)

# ---------------------------------------------------------------------------
# Service layer — dependency wiring
# ---------------------------------------------------------------------------
embedding_svc = EmbeddingService(model_name=config.embedding_model)
llm_svc = LLMService(api_key=config.groq_api_key, model=config.groq_chat_model)
rag_svc = RAGService(vector_repo=vector_repo, embedding_svc=embedding_svc)
agent_svc = AgentService(llm_svc=llm_svc, rag_svc=rag_svc, order_repo=order_repo)
voice_svc = VoiceService(
    groq_client=Groq(api_key=config.groq_api_key),
    model=config.whisper_model,
)
health_svc = HealthService()

# Inject services into route modules
init_chat_router(agent_service=agent_svc)
init_voice_router(voice_service=voice_svc, agent_service=agent_svc)

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI Customer Support Agent API",
    description=(
        "Production-grade backend service powering an AI Customer Support Agent. "
        "Integrates Groq Llama 3 models with a SQLite database to resolve support "
        "inquiries and look up order details dynamically."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# Middleware — CORS
# ---------------------------------------------------------------------------
# Allow all origins for development/integration. In production, restrict this
# to your explicit frontend domain (e.g., ["https://support.mycompany.com"]).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global exception handlers — standardise all error responses
# ---------------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Catch Pydantic validation failures (HTTP 422) and format them using
    the standard ErrorResponse schema so clients always see a consistent shape.
    """
    error_messages = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        message = err.get("msg", "Validation failed")
        error_messages.append(f"[{field}]: {message}")

    combined_detail = "; ".join(error_messages)
    logger.warning("Request validation failed: %s", combined_detail)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=ErrorResponse(
            error="Validation Error",
            detail=combined_detail,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Catch any unhandled server exception (HTTP 500). Prevents raw tracebacks
    from reaching the client while logging the full error for engineers.
    """
    logger.error(
        "Unhandled exception on %s: %s", request.url.path, exc, exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal Server Error",
            detail="An unexpected error occurred. Please contact system support.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ).model_dump(),
    )

# ---------------------------------------------------------------------------
# Startup lifecycle hook
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup_event() -> None:
    """
    Pre-warm the embedding model and ChromaDB collection on server boot.

    Loading these resources at startup eliminates first-request latency —
    the model takes ~2-5 seconds to load and ChromaDB needs an initial
    index scan. Both operations are fast on subsequent calls (cached).
    """
    logger.info("Pre-warming SentenceTransformer model and ChromaDB...")
    try:
        embedding_svc.get_model()
        vector_repo.get_collection()
        logger.info("Pre-warming complete. Server is ready for instant requests.")
    except Exception as exc:
        logger.warning(
            "Startup pre-warming encountered a non-fatal error: %s", exc
        )

# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(voice_router)

# ---------------------------------------------------------------------------
# Development server entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
