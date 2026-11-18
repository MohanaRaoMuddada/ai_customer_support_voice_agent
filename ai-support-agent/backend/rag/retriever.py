"""
rag/retriever.py — Knowledge Base Retrieval
=============================================

Provides the ``retrieve_context`` function used by RAGService to fetch the
most semantically similar document chunks for a given customer query.

Design note: this is a thin orchestration function that composes
``embedding_svc.generate()`` with ``vector_repo.search()``. Keeping it
separate from the service layer means the retrieval strategy (e.g., switching
from ANN to hybrid BM25+vector) can be changed here without touching
RAGService.
"""

from typing import Any, Dict, List

from core.logger import get_logger

logger = get_logger(__name__)


def retrieve_context(
    query: str,
    vector_repo,
    embedding_svc,
    n_results: int = 3,
) -> List[Dict[str, Any]]:
    """
    Embed a query and retrieve the top-N most semantically similar chunks.

    Pipeline:
      1. ``embedding_svc.generate(query)`` → 384-dim query vector.
      2. ``vector_repo.search(vector, n_results)`` → nearest-neighbour results.

    Args:
        query        (str)  : The customer's question or support request.
        vector_repo         : VectorRepository instance.
        embedding_svc       : EmbeddingService instance.
        n_results    (int)  : Number of top chunks to retrieve.

    Returns:
        List[Dict[str, Any]]: Matched chunks, each with ``id``, ``text``,
                              ``metadata``, and ``distance`` keys.
                              Returns an empty list if retrieval fails.
    """
    logger.info(
        "Retrieving context for query: '%s' (top %d results)", query[:80], n_results
    )

    try:
        query_vector = embedding_svc.generate(query)
        results = vector_repo.search(query_vector, n_results=n_results)
        logger.info("Retrieved %d chunk(s) from knowledge base.", len(results))
        return results

    except Exception as exc:
        logger.error("Context retrieval failed: %s", exc, exc_info=True)
        return []
