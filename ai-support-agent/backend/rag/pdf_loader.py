"""
rag/pdf_loader.py — PDF Document Loader
=========================================

Responsible for reading PDF files from the data directory and extracting
their text content as a list of page-level document dictionaries.

Design note: this is a pure function — it takes a directory path and returns
a list of dicts. There is no state to manage between calls. A class would
add ceremony with zero benefit here.
"""

import os
from typing import Any, Dict, List

from pypdf import PdfReader

from core.constants import RAG_PDF_FILENAMES
from core.logger import get_logger

logger = get_logger(__name__)


def load_documents(data_dir: str) -> List[Dict[str, Any]]:
    """
    Read target PDF files from ``data_dir`` and extract text by page.

    Scans specifically for ``faq.pdf``, ``policy.pdf``, and ``manual.pdf``.
    Files that are missing or unreadable are skipped with a warning rather
    than crashing the pipeline — a partial knowledge base is better than none.

    Args:
        data_dir (str): Absolute path to the directory containing the PDF files.

    Returns:
        List[Dict[str, Any]]: One dict per non-empty page, each containing:
            - ``text``   (str): Extracted page text.
            - ``source`` (str): PDF filename (e.g., ``"faq.pdf"``).
            - ``page``   (int): 1-based page number.
    """
    documents: List[Dict[str, Any]] = []
    logger.info("Loading documents from: %s", data_dir)

    for filename in RAG_PDF_FILENAMES:
        pdf_path = os.path.join(data_dir, filename)

        if not os.path.exists(pdf_path):
            logger.warning("Document not found, skipping: %s", pdf_path)
            continue

        try:
            logger.info("Parsing: %s", filename)
            reader = PdfReader(pdf_path)
            logger.info("Found %d page(s) in %s", len(reader.pages), filename)

            for page_idx, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    documents.append({
                        "text":   text,
                        "source": filename,
                        "page":   page_idx + 1,
                    })
                else:
                    logger.debug(
                        "Skipped empty page %d in %s", page_idx + 1, filename
                    )

        except Exception as exc:
            logger.error("Failed to parse %s: %s", filename, exc, exc_info=True)

    logger.info("Loaded %d page(s) total from all documents.", len(documents))
    return documents
