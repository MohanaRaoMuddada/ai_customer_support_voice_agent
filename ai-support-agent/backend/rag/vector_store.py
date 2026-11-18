"""
rag/vector_store.py — Embedding Generation and Vector Index Population
=======================================================================

Orchestrates the batch process of turning text chunks into embeddings and
writing them to the ChromaDB vector store.

Design note: this is a pure orchestration function — it accepts the
repository and embedding service as arguments (dependency injection) rather
than importing them directly. This makes it easy to test and swap
implementations without touching this file.
"""

import os
from typing import Any, Dict, List

from core.logger import get_logger

logger = get_logger(__name__)


def store_embeddings(
    chunks: List[Dict[str, Any]],
    vector_repo,
    embedding_svc,
    clear_existing: bool = True,
) -> None:
    """
    Generate embeddings for each chunk and write them to the vector database.

    For each chunk:
      1. Derives a deterministic, human-readable chunk ID.
      2. Calls ``embedding_svc.generate()`` to produce a 384-dim vector.
      3. Batches IDs, texts, vectors, and metadata.
      4. Writes the full batch to the vector store in a single call.

    Args:
        chunks         (List[Dict])      : Chunks from ``chunk_documents()``.
        vector_repo                      : VectorRepository instance.
        embedding_svc                    : EmbeddingService instance.
        clear_existing (bool)            : If ``True``, drop and recreate the
                                           collection before writing (full rebuild).
    """
    if not chunks:
        logger.warning("No chunks provided to store_embeddings. Aborting.")
        return

    logger.info("Preparing to index %d chunk(s) into vector store.", len(chunks))

    if clear_existing:
        collection = vector_repo.clear_and_create()
    else:
        collection = vector_repo.get_collection()

    ids: List[str] = []
    documents: List[str] = []
    embeddings: List[List[float]] = []
    metadatas: List[Dict[str, Any]] = []

    for idx, chunk in enumerate(chunks):
        chunk_text = chunk["text"]
        meta = chunk["metadata"]

        source_basename = os.path.basename(meta["source"])
        chunk_id = f"{source_basename}_p{meta['page']}_c{idx}"

        try:
            vector = embedding_svc.generate(chunk_text)
            ids.append(chunk_id)
            documents.append(chunk_text)
            embeddings.append(vector)
            metadatas.append(meta)

            if (idx + 1) % 50 == 0:
                logger.info("Processed %d / %d chunks...", idx + 1, len(chunks))

        except Exception as exc:
            logger.error(
                "Embedding failed for chunk %d: %s", idx, exc, exc_info=True
            )

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    logger.info(
        "Vector store populated. Indexed %d record(s).", collection.count()
    )
