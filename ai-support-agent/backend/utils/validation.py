"""
utils/validation.py — Input Validation Helpers
================================================

Pure functions that validate inputs and raise typed exceptions on failure.
Separating validation from service logic keeps services readable and makes
validation rules easy to find, read, and update independently.
"""

from core.constants import MIN_AUDIO_BYTES, SUPPORTED_AUDIO_MIME_TYPES
from core.exceptions import VoiceTranscriptionError


def validate_audio_payload(file_bytes: bytes, content_type: str) -> str:
    """
    Validate audio bytes and MIME type, returning the resolved file extension.

    Performs three sequential checks:
      1. The payload is non-empty.
      2. The payload meets the minimum size threshold (not a corrupt/zero-duration file).
      3. The MIME type is on the supported allowlist.

    Args:
        file_bytes   (bytes): Raw audio bytes received from the client.
        content_type (str)  : MIME type string (may include codec parameters,
                              e.g., ``"audio/webm;codecs=opus"``).

    Returns:
        str: The file extension for the validated MIME type (e.g., ``".webm"``).

    Raises:
        VoiceTranscriptionError: With an appropriate ``http_code`` if any
                                  validation check fails.
    """
    if not file_bytes:
        raise VoiceTranscriptionError(
            "The audio recording is empty. Please record a message before submitting.",
            http_code=400,
        )

    if len(file_bytes) < MIN_AUDIO_BYTES:
        raise VoiceTranscriptionError(
            "The audio recording is too short or corrupt. "
            "Please try speaking for longer.",
            http_code=400,
        )

    # Strip codec parameters before looking up the MIME type.
    # e.g. "audio/webm;codecs=opus" → "audio/webm"
    normalized_type = content_type.split(";")[0].strip().lower()
    file_extension = SUPPORTED_AUDIO_MIME_TYPES.get(normalized_type)

    if file_extension is None:
        supported = ", ".join(SUPPORTED_AUDIO_MIME_TYPES.keys())
        raise VoiceTranscriptionError(
            f"Unsupported audio format: '{content_type}'. "
            f"Supported formats: webm, ogg, wav, mp4, m4a, mp3.",
            http_code=415,
        )

    return file_extension
