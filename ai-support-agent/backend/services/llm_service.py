"""
services/llm_service.py — Groq LLM Completion Service
=======================================================

LLMService wraps the Groq Chat Completions API and provides a single
``complete()`` method that any service can call. All Groq SDK interactions
live here and nowhere else.

Why a class here:
    LLMService holds the authenticated Groq client and model name as instance
    state. This is the natural home for future cross-cutting concerns such as
    retry logic, token-usage tracking, rate-limit handling, or provider
    swapping — all without changing any calling code.
"""

from groq import Groq

from core.logger import get_logger

logger = get_logger(__name__)


class LLMService:
    """
    Thin, stateful wrapper around the Groq Chat Completions SDK.

    Provides a clean ``complete(prompt)`` interface so the rest of the
    application never imports or instantiates the Groq SDK directly.

    Attributes:
        model (str): Groq model identifier (e.g., ``"llama-3.3-70b-versatile"``).
    """

    def __init__(self, api_key: str, model: str) -> None:
        self._client = Groq(api_key=api_key)
        self.model = model
        logger.info("LLMService initialised with model: %s", self.model)

    def complete(self, prompt: str) -> str:
        """
        Send a prompt to Groq and return the generated text response.

        The prompt is sent as a single ``user`` message. This approach keeps
        the calling code simple — prompt construction (system instructions,
        context injection, user message) is handled upstream by the prompt
        template builders.

        Args:
            prompt (str): The fully assembled prompt string to send to the LLM.

        Returns:
            str: The AI-generated text response. Falls back to a safe,
                 user-friendly message if the API call fails.
        """
        logger.info(
            "Calling Groq API | model=%s | prompt_length=%d chars",
            self.model,
            len(prompt),
        )

        try:
            completion = self._client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
            )
            response_text: str = completion.choices[0].message.content
            logger.info(
                "Groq API response received | length=%d chars", len(response_text)
            )
            return response_text

        except Exception as exc:
            logger.error(
                "Groq API call failed: %s", exc, exc_info=True
            )
            return (
                "I'm sorry, I'm experiencing a technical issue right now. "
                "Please try again in a moment, or contact support@company.com."
            )
