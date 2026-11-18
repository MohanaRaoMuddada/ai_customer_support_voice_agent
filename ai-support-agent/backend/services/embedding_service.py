"""
services/embedding_service.py — Local SentenceTransformer Embedding Service
=============================================================================

EmbeddingService wraps the HuggingFace SentenceTransformer model and manages
its lazy-loading lifecycle. Callers never interact with the model directly —
they call ``generate()`` and receive a list of floats.

Why a class here:
    EmbeddingService holds the model instance as private state and manages
    lazy-loading (load on first use, reuse afterwards). This lifecycle
    management is the defining use case for a class. It also makes
    the service easily injectable and mockable in tests.
"""

from typing import List

from sentence_transformers import SentenceTransformer

from core.logger import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """
    Manages the SentenceTransformer model lifecycle and text embedding generation.

    The model is loaded from disk on the first call to ``generate()`` and
    cached for the lifetime of the instance. Subsequent calls reuse the
    cached model with no reloading overhead.

    Attributes:
        model_name (str): HuggingFace model identifier (e.g., ``"all-MiniLM-L6-v2"``).
    """

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model: SentenceTransformer | None = None

    def get_model(self) -> SentenceTransformer:
        """
        Return the loaded SentenceTransformer model, loading it on first access.

        Attempts to load from local cached files first to avoid a network call.
        Falls back to a full download if the local cache is unavailable.

        Returns:
            SentenceTransformer: The loaded embedding model.
        """
        if self._model is None:
            logger.info("Loading SentenceTransformer model: %s", self.model_name)
            try:
                self._model = SentenceTransformer(
                    self.model_name, local_files_only=True
                )
            except Exception:
                logger.info(
                    "Local cache miss — downloading model: %s", self.model_name
                )
                self._model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully.")
        return self._model

    def generate(self, text: str) -> List[float]:
        """
        Generate a 384-dimensional dense vector embedding for the given text.

        Args:
            text (str): Non-empty input string to embed.

        Returns:
            List[float]: A list of 384 floating-point numbers representing
                         the semantic meaning of the input text.

        Raises:
            ValueError: If the input text is empty or not a string.
        """
        if not text or not isinstance(text, str):
            raise ValueError("Input text must be a non-empty string.")

        model = self.get_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
