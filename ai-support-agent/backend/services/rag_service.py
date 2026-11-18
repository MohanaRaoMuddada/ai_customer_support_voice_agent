"""
services/rag_service.py — Retrieval-Augmented Generation Service
=================================================================

RAGService composes the EmbeddingService and VectorRepository to provide a
single, clean interface for knowledge-base retrieval. Callers receive a list
of matching document chunks and a deduplicated list of source labels.

Why a class here:
    RAGService holds two injected dependencies (embedding_svc and vector_repo)
    as instance state. Dependency injection makes the service independently
    testable — swap out real ChromaDB with an in-memory mock without
    touching AgentService.
"""

from typing import Any, Dict, List, Tuple

from core.logger import get_logger
from rag.retriever import retrieve_context

logger = get_logger(__name__)


class RAGService:
    """
    Orchestrates knowledge-base retrieval for general customer support queries.

    Delegates embedding generation to EmbeddingService and vector search to
    VectorRepository via the ``retrieve_context`` pipeline function.

    Attributes:
        vector_repo    : VectorRepository instance for ChromaDB access.
        embedding_svc  : EmbeddingService instance for text embedding.
    """

    def __init__(self, vector_repo, embedding_svc) -> None:
        self._vector_repo = vector_repo
        self._embedding_svc = embedding_svc

    def search(
        self,
        query: str,
        n_results: int = 3,
    ) -> Tuple[str, List[str]]:
        """
        Retrieve the most relevant knowledge-base chunks for a customer query.

        Args:
            query     (str): The customer's question.
            n_results (int): Maximum number of chunks to retrieve.

        Returns:
            Tuple[str, List[str]]:
                - ``context_text``   (str)      : Concatenated chunk texts with
                                                  source labels, ready for prompt injection.
                - ``source_labels``  (List[str]): Deduplicated list of source references
                                                  for the ``sources`` field of the API response.
        """
        logger.info("RAGService: searching knowledge base for: '%s'", query[:80])

        results = retrieve_context(
            query=query,
            vector_repo=self._vector_repo,
            embedding_svc=self._embedding_svc,
            n_results=n_results,
        )

        if not results:
            logger.warning("RAG search returned no results for query: '%s'", query[:80])
            return (
                "No additional context found in the Company Knowledge Base.",
                ["Company Knowledge Base (Fallback)"],
            )

        context_blocks: List[str] = []
        source_labels: List[str] = []

        for result in results:
            source = result["metadata"].get("source", "Unknown")
            page = result["metadata"].get("page", "Unknown")
            context_blocks.append(f"Source: {source} (Page {page}):\n{result['text']}")

            label = f"Company Knowledge Base ({source})"
            if label not in source_labels:
                source_labels.append(label)

        context_text = "\n\n".join(context_blocks)
        logger.info(
            "RAG search complete. %d chunk(s), %d unique source(s).",
            len(results),
            len(source_labels),
        )
        return context_text, source_labels
