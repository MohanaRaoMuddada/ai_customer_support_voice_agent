"""
services/agent_service.py — AI Support Agent Orchestration
===========================================================

AgentService is the central reasoning engine of the application. It
receives a raw customer message, decides how to route it (order lookup vs.
knowledge-base search), assembles the correct LLM prompt, and returns the
AI-generated response alongside the data sources used.

Why a class here:
    AgentService coordinates three injected dependencies: LLMService,
    RAGService, and OrderRepository. Holding them as instance state enables
    dependency injection, which makes the service independently testable
    and fully decoupled from concrete implementations (Dependency Inversion
    Principle). The agent's routing logic also benefits from being encapsulated
    behind a clean ``process()`` interface.
"""

from typing import List, Optional, Tuple

from core.logger import get_logger
from prompts.prompt_templates import build_order_prompt, build_rag_prompt
from prompts.system_prompt import SYSTEM_PROMPT
from utils.helpers import format_order_result
from utils.text_utils import extract_order_id

logger = get_logger(__name__)


class AgentService:
    """
    AI customer support reasoning engine.

    Implements the ReAct (Reason → Act → Observe → Respond) pattern:
      - Order queries: detect ID → fetch from DB → build prompt → call LLM
      - General queries: RAG search → build prompt → call LLM

    Attributes:
        llm_svc     : LLMService instance for chat completions.
        rag_svc     : RAGService instance for knowledge-base retrieval.
        order_repo  : OrderRepository instance for SQLite order lookups.
    """

    def __init__(self, llm_svc, rag_svc, order_repo) -> None:
        self._llm = llm_svc
        self._rag = rag_svc
        self._order_repo = order_repo

    def process(self, message: str) -> Tuple[str, List[str]]:
        """
        Process a customer support query end-to-end.

        This is the single public entry point called by the route handlers.
        It validates the message, routes it to the correct pipeline, assembles
        the LLM prompt, and returns the generated response with source metadata.

        Decision tree:
            message contains 4-digit number?
              YES → fetch order from DB → build order prompt → LLM
              NO  → RAG search → build RAG prompt → LLM

        Args:
            message (str): Raw customer message string from the API request.

        Returns:
            Tuple[str, List[str]]:
                - Response text (str)      : The AI-generated reply.
                - Sources (List[str])      : Data sources used to generate the answer.

        Note:
            This function never raises — all errors are caught and converted
            to safe, user-friendly fallback responses. A support agent must
            always respond.
        """
        message = message.strip()
        logger.info("Processing query | preview: '%s'", message[:100])

        if not message:
            logger.warning("Empty message received — returning early.")
            return (
                "I didn't receive a message. Could you please repeat your question?",
                [],
            )

        order_id: Optional[int] = extract_order_id(message)

        if order_id is not None:
            return self._handle_order_query(message, order_id)
        return self._handle_general_query(message)

    # ------------------------------------------------------------------
    # Private routing methods
    # ------------------------------------------------------------------

    def _handle_order_query(
        self, message: str, order_id: int
    ) -> Tuple[str, List[str]]:
        """
        Handle order-specific queries by fetching live data from SQLite.

        Args:
            message  (str): The original customer message.
            order_id (int): The detected order ID from the message.

        Returns:
            Tuple[str, List[str]]: LLM response and source labels.
        """
        logger.info("Order query detected | order_id=%d", order_id)

        order = self._order_repo.get_by_id(order_id)

        if order is not None:
            tool_result = format_order_result(order)
        else:
            tool_result = (
                f"No order found with ID {order_id}. "
                "Please verify the order number and try again. "
                "Valid order IDs are typically 4-digit numbers like 1001."
            )

        logger.info("Tool result: %s", tool_result)

        prompt = build_order_prompt(
            system_prompt=SYSTEM_PROMPT,
            tool_result=tool_result,
            customer_message=message,
        )

        response = self._llm.complete(prompt)
        sources = ["SQLite Database (Order Ledger)"]

        logger.info("Order query processed | response_length=%d chars", len(response))
        return response, sources

    def _handle_general_query(self, message: str) -> Tuple[str, List[str]]:
        """
        Handle general support queries using RAG knowledge-base retrieval.

        Args:
            message (str): The original customer message.

        Returns:
            Tuple[str, List[str]]: LLM response and source labels.
        """
        logger.info("General query — performing RAG search.")

        try:
            context_text, source_labels = self._rag.search(message, n_results=3)
        except Exception as exc:
            logger.error("RAG search failed inside agent: %s", exc, exc_info=True)
            context_text = "No additional context found in the Company Knowledge Base."
            source_labels = ["Company Knowledge Base (Fallback)"]

        prompt = build_rag_prompt(
            system_prompt=SYSTEM_PROMPT,
            context_text=context_text,
            customer_message=message,
        )

        response = self._llm.complete(prompt)

        logger.info("General query processed | response_length=%d chars", len(response))
        return response, source_labels
