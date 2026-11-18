"""
core/exceptions.py — Custom Exception Hierarchy
================================================

All application-level exceptions inherit from AgentError so callers
can catch the base class when needed, while still distinguishing
sub-types for granular handling (e.g., returning the correct HTTP code).

Design note: exceptions are kept as plain classes with no business logic.
They carry only contextual data (message, http_code) needed by the caller.
"""


class AgentError(Exception):
    """Base exception for all AI Support Agent errors."""


class ConfigurationError(AgentError):
    """Raised when required environment variables or config values are missing."""


class DatabaseError(AgentError):
    """Raised when a SQLite database operation fails unexpectedly."""


class RAGError(AgentError):
    """Raised when the ChromaDB or embedding pipeline encounters an error."""


class VoiceTranscriptionError(AgentError):
    """
    Raised at any stage of the audio transcription pipeline.

    Carries an http_code so the route handler can return the appropriate
    HTTP status without coupling voice logic to FastAPI internals.

    Attributes:
        message   (str): Human-readable failure description.
        http_code (int): Suggested HTTP status code for the client response.
    """

    def __init__(self, message: str, http_code: int = 422) -> None:
        super().__init__(message)
        self.message = message
        self.http_code = http_code
