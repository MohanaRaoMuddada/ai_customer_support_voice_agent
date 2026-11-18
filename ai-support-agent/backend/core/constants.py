"""
core/constants.py — Application-wide Constants
===============================================

This module holds immutable values that are referenced across multiple
layers of the application but do not belong to environment configuration.

Rule: If a value never changes between environments (dev/staging/prod),
it belongs here. If it CAN change per environment, it belongs in config.py.
"""

import re

# ---------------------------------------------------------------------------
# Audio validation
# ---------------------------------------------------------------------------

# MIME type → file extension mapping used by the voice transcription pipeline.
# The Groq SDK infers audio codec from the temp file extension, so the mapping
# must be kept in sync with what Groq Whisper actually supports.
SUPPORTED_AUDIO_MIME_TYPES: dict[str, str] = {
    "audio/webm":  ".webm",   # Chrome / Edge MediaRecorder default
    "audio/ogg":   ".ogg",    # Firefox MediaRecorder default
    "audio/wav":   ".wav",    # PCM WAV
    "audio/wave":  ".wav",    # WAV alias
    "audio/x-wav": ".wav",    # WAV alias
    "audio/mp4":   ".mp4",    # Safari MediaRecorder default
    "audio/x-m4a": ".m4a",    # Apple M4A
    "audio/mpeg":  ".mp3",    # MP3
    "audio/mp3":   ".mp3",    # MP3 alias
}

# Minimum acceptable audio payload size (bytes).
# Files below this threshold are almost certainly corrupt or zero-duration.
MIN_AUDIO_BYTES: int = 1_024

# ---------------------------------------------------------------------------
# Order number detection
# ---------------------------------------------------------------------------

# Pre-compiled regex for matching 4-digit order numbers in customer messages.
# Word boundaries (\b) ensure "10021" does not yield a false "1002" match.
# Compiled once at import time — safe to reuse across concurrent requests.
ORDER_NUMBER_PATTERN: re.Pattern = re.compile(r"\b(\d{4})\b")

# ---------------------------------------------------------------------------
# RAG pipeline
# ---------------------------------------------------------------------------

# Default number of knowledge-base chunks to retrieve per query.
RAG_DEFAULT_N_RESULTS: int = 3

# Chunking defaults for the PDF ingestion pipeline.
RAG_CHUNK_SIZE: int = 500
RAG_CHUNK_OVERLAP: int = 50

# Minimum character length for a chunk to be worth indexing.
RAG_MIN_CHUNK_LENGTH: int = 20

# PDF filenames expected inside the data/ directory.
RAG_PDF_FILENAMES: list[str] = ["faq.pdf", "policy.pdf", "manual.pdf"]
