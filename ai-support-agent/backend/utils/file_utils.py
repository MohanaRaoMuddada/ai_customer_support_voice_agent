"""
utils/file_utils.py — File I/O Helpers
========================================

Pure, stateless functions for temporary file management.
Extracted from the voice transcription pipeline so that the service layer
does not mix file I/O concerns with transcription orchestration.
"""

import os
import tempfile

from core.logger import get_logger

logger = get_logger(__name__)


def write_temp_file(data: bytes, suffix: str, prefix: str = "upload_") -> str:
    """
    Write bytes to a named temporary file and return its path.

    The file is created with ``delete=False`` so the caller controls
    its deletion — necessary on Windows where open files cannot be removed.

    Args:
        data   (bytes): Raw binary data to write.
        suffix (str)  : File extension including the leading dot (e.g., ``.webm``).
        prefix (str)  : Optional filename prefix for the temp file.

    Returns:
        str: Absolute path to the created temporary file.
    """
    with tempfile.NamedTemporaryFile(
        suffix=suffix,
        prefix=prefix,
        delete=False,
    ) as tmp:
        tmp.write(data)
        path = tmp.name

    logger.debug("Temporary file written: %s (%d bytes)", path, len(data))
    return path


def delete_file(path: str) -> None:
    """
    Delete a file from disk, logging a warning (not raising) on failure.

    Non-fatal cleanup — if deletion fails the OS will reclaim the space
    on the next restart. Calling code should never crash because of this.

    Args:
        path (str): Absolute path of the file to remove.
    """
    if not path or not os.path.exists(path):
        return

    try:
        os.remove(path)
        logger.debug("Deleted temporary file: %s", path)
    except OSError as exc:
        logger.warning("Could not delete temporary file '%s': %s", path, exc)
