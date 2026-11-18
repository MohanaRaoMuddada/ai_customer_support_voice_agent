"""
core/config.py — Application Configuration Manager
====================================================

ConfigManager loads the .env file once at startup and exposes every
configuration value as a typed, read-only property. All other modules
call ``ConfigManager.get()`` to obtain the shared singleton instance.

Why a class here:
    ConfigManager holds loaded state (the resolved env values) and has a
    well-defined lifecycle (load once, read many times). Encapsulating that
    state in a class prevents accidental mutation and gives callers a clean,
    discoverable interface. A plain dict or module-level globals would not
    provide the same guarantees.

Why a singleton:
    Configuration is process-wide. Creating multiple instances that each
    call load_dotenv() independently would be wasteful and could produce
    inconsistent state if the .env file changed between loads.
"""

import os
from functools import cached_property

from dotenv import load_dotenv

from core.exceptions import ConfigurationError


class ConfigManager:
    """
    Loads environment variables from the .env file and exposes them
    as typed properties.

    Usage:
        config = ConfigManager.get()
        api_key = config.groq_api_key
    """

    _instance: "ConfigManager | None" = None

    def __init__(self) -> None:
        # Resolve the project root: backend/ → ../ → project root
        self._backend_dir: str = os.path.dirname(os.path.abspath(__file__))
        self._backend_dir = os.path.dirname(self._backend_dir)  # up one level to backend/
        self._project_root: str = os.path.dirname(self._backend_dir)

        # Load .env from project root; override=True ensures a restarted
        # server picks up edits without requiring a full system env refresh.
        load_dotenv(
            dotenv_path=os.path.join(self._project_root, ".env"),
            override=True,
        )

        self._validate()

    # ------------------------------------------------------------------
    # Singleton accessor
    # ------------------------------------------------------------------

    @classmethod
    def get(cls) -> "ConfigManager":
        """Return the shared ConfigManager instance, creating it if needed."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Internal validation
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        """Raise ConfigurationError if any required env variable is absent."""
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key or api_key == "your-groq-api-key-here":
            raise ConfigurationError(
                "GROQ_API_KEY is not set. "
                "Create a .env file in the project root with:\n"
                "  GROQ_API_KEY=your-actual-api-key\n"
                "Get your key at: https://console.groq.com/keys"
            )

    # ------------------------------------------------------------------
    # Groq / LLM settings
    # ------------------------------------------------------------------

    @cached_property
    def groq_api_key(self) -> str:
        """Groq Cloud API key loaded from GROQ_API_KEY env variable."""
        return os.environ["GROQ_API_KEY"]

    @cached_property
    def groq_chat_model(self) -> str:
        """Groq model ID used for chat completions."""
        return os.getenv("GROQ_CHAT_MODEL", "openai/gpt-oss-120b")

    @cached_property
    def whisper_model(self) -> str:
        """Groq Whisper model ID used for speech-to-text transcription."""
        return os.getenv("WHISPER_MODEL", "whisper-large-v3-turbo")

    # ------------------------------------------------------------------
    # Embedding settings
    # ------------------------------------------------------------------

    @cached_property
    def embedding_model(self) -> str:
        """HuggingFace SentenceTransformer model name for local embeddings."""
        return os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # ------------------------------------------------------------------
    # Path settings
    # ------------------------------------------------------------------

    @cached_property
    def database_path(self) -> str:
        """Absolute path to the SQLite orders database file."""
        relative = os.getenv("DATABASE_PATH", "orders.db")
        if os.path.isabs(relative):
            return relative
        return os.path.join(self._project_root, relative)

    @cached_property
    def chroma_db_path(self) -> str:
        """Absolute path to the ChromaDB persistent storage directory."""
        relative = os.getenv("CHROMA_DB_PATH", "chroma_db")
        if os.path.isabs(relative):
            return relative
        return os.path.join(self._project_root, relative)

    @cached_property
    def data_dir(self) -> str:
        """Absolute path to the directory containing PDF knowledge-base files."""
        relative = os.getenv("DATA_DIR", "data")
        if os.path.isabs(relative):
            return relative
        return os.path.join(self._project_root, relative)

    @cached_property
    def chroma_collection_name(self) -> str:
        """ChromaDB collection name for the customer support knowledge base."""
        return os.getenv(
            "CHROMA_COLLECTION_NAME", "customer_support_knowledge_base"
        )
