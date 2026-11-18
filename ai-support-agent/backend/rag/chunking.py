"""
rag/chunking.py — Text Chunking Pipeline
==========================================

Splits long document pages into smaller, overlapping text chunks suitable
for embedding and vector-index storage.

Design note: chunking is a pure, stateless text transformation. Given the
same inputs it always produces the same outputs. A function is the right
tool — a class would be artificial overhead.
"""

from typing import Any, Dict, List

from core.constants import RAG_CHUNK_OVERLAP, RAG_CHUNK_SIZE, RAG_MIN_CHUNK_LENGTH
from core.logger import get_logger

logger = get_logger(__name__)


def chunk_documents(
    documents: List[Dict[str, Any]],
    chunk_size: int = RAG_CHUNK_SIZE,
    chunk_overlap: int = RAG_CHUNK_OVERLAP,
) -> List[Dict[str, Any]]:
    """
    Split extracted document pages into overlapping character-level chunks.

    Uses a sliding-window approach where each window advances by
    ``(chunk_size - chunk_overlap)`` characters. Chunk boundaries are
    aligned to whitespace where possible to avoid splitting words mid-stream.

    Args:
        documents     (List[Dict]): Page-level dicts from ``load_documents()``.
        chunk_size    (int)       : Target character length per chunk.
        chunk_overlap (int)       : Overlap between consecutive chunks to
                                    preserve context across boundaries.

    Returns:
        List[Dict[str, Any]]: One dict per chunk, each containing:
            - ``text``     (str) : The chunk text content.
            - ``metadata`` (dict): Source info (source, page, start_char, end_char).
    """
    logger.info(
        "Chunking %d document page(s) | chunk_size=%d | overlap=%d",
        len(documents),
        chunk_size,
        chunk_overlap,
    )

    chunks: List[Dict[str, Any]] = []

    for doc in documents:
        text: str = doc["text"]
        source: str = doc["source"]
        page: int = doc["page"]
        text_len = len(text)
        start = 0

        while start < text_len:
            end = min(start + chunk_size, text_len)

            # Align boundary to the nearest preceding whitespace
            if end < text_len:
                lookback = max(start, end - 50)
                space_idx = text.rfind(" ", lookback, end)
                if space_idx != -1:
                    end = space_idx

            chunk_text = text[start:end].strip()

            if len(chunk_text) > RAG_MIN_CHUNK_LENGTH:
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        "source":     source,
                        "page":       page,
                        "start_char": start,
                        "end_char":   end,
                    },
                })

            start += chunk_size - chunk_overlap

            # Guard against infinite loop if the window fails to advance
            if start >= end:
                start = end

    logger.info("Generated %d chunk(s) from document corpus.", len(chunks))
    return chunks
