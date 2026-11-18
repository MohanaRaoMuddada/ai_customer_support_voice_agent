"""
models/request_models.py — Inbound API Request Schemas
=======================================================

Pydantic models represent the contract between the API surface and its
callers. FastAPI automatically validates incoming JSON bodies against these
models, returning HTTP 422 with a structured error if validation fails —
no manual validation code required.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """
    Payload sent by the client to the POST /chat endpoint.

    Attributes:
        message    (str)           : The customer's question or support request.
        session_id (str | None)    : Optional session identifier for conversation tracking.
        language   (str)           : ISO 639-1 language code. Defaults to ``"en"``.
    """

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's question or support request.",
        example="How do I reset my account password?",
    )

    session_id: Optional[str] = Field(
        default=None,
        description="Optional session ID for tracking conversation history.",
        example="sess_abc123xyz",
    )

    language: str = Field(
        default="en",
        description="The preferred language for the AI's response (ISO 639-1 code).",
        example="en",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "How do I reset my account password?",
                    "session_id": "sess_abc123xyz",
                    "language": "en",
                }
            ]
        }
    }
