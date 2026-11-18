"""
models/response_models.py — Outbound API Response Schemas
=========================================================

Declaring response models separately from request models enforces clear
boundaries: the server's output contract is never accidentally coupled to
its input contract. FastAPI uses these models to filter and serialise
route return values into JSON.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatResponse(BaseModel):
    """
    Payload returned by the POST /chat and POST /voice endpoints.

    Attributes:
        response   (str)        : The AI-generated answer to the customer's query.
        session_id (str | None) : Echoed session ID from the request, if provided.
        sources    (List[str])  : Knowledge-base sources referenced in generating the answer.
        timestamp  (datetime)   : UTC timestamp of when the response was generated.
    """

    response: str = Field(
        ...,
        description="The AI-generated answer to the user's question.",
        example="To reset your password, navigate to Settings → Security → Reset Password.",
    )

    session_id: Optional[str] = Field(
        default=None,
        description="The session ID associated with this conversation.",
        example="sess_abc123xyz",
    )

    # default_factory=list creates a fresh empty list per instance.
    # Never use default=[] for mutable defaults — all instances would share
    # the same list object, a classic Python gotcha.
    sources: List[str] = Field(
        default_factory=list,
        description="Knowledge-base sources referenced to generate this response.",
        example=["FAQ #42 - Password Reset", "Help Center Article: Account Security"],
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of when the response was generated.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "response": "To reset your password, go to Settings → Security → Reset Password.",
                    "session_id": "sess_abc123xyz",
                    "sources": ["FAQ #42 - Password Reset"],
                    "timestamp": "2024-01-15T10:30:00.123456",
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    """
    Response model for the GET /health endpoint.

    Used by load balancers, Kubernetes liveness probes, and monitoring
    dashboards to confirm the service is operational.

    Attributes:
        status    (str)      : Service health state, typically ``"healthy"``.
        version   (str)      : Current API version string.
        timestamp (datetime) : UTC time of the health check response.
    """

    status: str = Field(
        default="healthy",
        description="Current health status of the API service.",
    )

    version: str = Field(
        default="1.0.0",
        description="The current version of the API.",
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of the health check.",
    )


class ErrorResponse(BaseModel):
    """
    Standardised error envelope returned for all non-2xx responses.

    Consistent error schemas allow API consumers to handle failures
    programmatically without parsing free-form text.

    Attributes:
        error       (str)      : Short, human-readable error title.
        detail      (str|None) : Optional detailed explanation of the failure cause.
        status_code (int)      : HTTP status code associated with this error.
    """

    error: str = Field(
        ...,
        description="A brief description of the error.",
        example="Validation Error",
    )

    detail: Optional[str] = Field(
        default=None,
        description="Additional detail about the error cause.",
        example="The 'message' field cannot be empty.",
    )

    status_code: int = Field(
        ...,
        description="HTTP status code associated with this error.",
        example=422,
    )
