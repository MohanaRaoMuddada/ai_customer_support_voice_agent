"""
services/voice_service.py — Speech-to-Text Transcription Service
=================================================================

VoiceService encapsulates the entire audio transcription pipeline using
the Groq Whisper Large V3 Turbo model. It receives raw audio bytes,
validates them, writes a temporary file, submits to Whisper, and returns
the clean transcription string.

Why a class here:
    VoiceService holds the authenticated Groq client and the Whisper model
    name as instance state. It also manages the temporary file lifecycle
    (create → use → delete), which benefits from a well-defined class
    structure rather than module-level globals.
"""

import time

from groq import Groq

from core.exceptions import VoiceTranscriptionError
from core.logger import get_logger
from utils.file_utils import delete_file, write_temp_file
from utils.text_utils import truncate
from utils.validation import validate_audio_payload

logger = get_logger(__name__)


class VoiceService:
    """
    Manages audio transcription via Groq Whisper Large V3 Turbo.

    Attributes:
        model (str): Whisper model identifier (e.g., ``"whisper-large-v3-turbo"``).
    """

    def __init__(self, groq_client: Groq, model: str) -> None:
        self._client = groq_client
        self.model = model
        logger.info("VoiceService initialised with model: %s", self.model)

    def transcribe(
        self,
        file_bytes: bytes,
        content_type: str,
        original_filename: str = "audio",
    ) -> str:
        """
        Transcribe raw audio bytes into text using Groq Whisper.

        Pipeline:
          1. Validate audio payload (size and MIME type).
          2. Write bytes to a named temporary file.
          3. Submit the temp file to the Groq Whisper API.
          4. Validate the returned transcription is non-empty.
          5. Delete the temporary file.

        Args:
            file_bytes        (bytes): Raw audio data from the client upload.
            content_type      (str)  : MIME type of the audio (e.g., ``"audio/webm"``).
            original_filename (str)  : Original filename for log context only.

        Returns:
            str: Clean transcription text from Whisper. Never empty.

        Raises:
            VoiceTranscriptionError: On validation failure, empty transcript,
                                      or Groq API error.
        """
        request_start = time.perf_counter()
        logger.info(
            "Transcription request | filename='%s' | content_type='%s' | size=%d bytes",
            original_filename,
            content_type,
            len(file_bytes),
        )

        # Step 1: Validate — raises VoiceTranscriptionError on failure
        file_extension = validate_audio_payload(file_bytes, content_type)

        logger.info(
            "Audio validation passed | extension='%s'", file_extension
        )

        # Step 2: Write bytes to temp file
        tmp_path = write_temp_file(
            data=file_bytes,
            suffix=file_extension,
            prefix="voice_upload_",
        )

        try:
            # Step 3: Submit to Groq Whisper
            whisper_start = time.perf_counter()
            logger.info("Submitting to Groq Whisper (model: %s)...", self.model)

            with open(tmp_path, "rb") as audio_file:
                transcription_response = self._client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language="en",
                    response_format="text",
                )

            whisper_elapsed = time.perf_counter() - whisper_start
            transcription_text = str(transcription_response).strip()

            logger.info(
                "Whisper transcription complete | duration=%.2fs | text='%s'",
                whisper_elapsed,
                truncate(transcription_text, max_length=120),
            )

            # Step 4: Guard against empty transcript
            if not transcription_text:
                raise VoiceTranscriptionError(
                    "No speech was detected in the audio. "
                    "Please speak clearly and try again.",
                    http_code=422,
                )

            total_elapsed = time.perf_counter() - request_start
            logger.info(
                "Voice pipeline complete | total_time=%.2fs | transcript_length=%d chars",
                total_elapsed,
                len(transcription_text),
            )
            return transcription_text

        except VoiceTranscriptionError:
            raise

        except Exception as exc:
            elapsed = time.perf_counter() - request_start
            logger.error(
                "Groq Whisper API error after %.2fs: %s", elapsed, exc, exc_info=True
            )
            raise VoiceTranscriptionError(
                "The voice transcription service encountered an error. "
                "Please try again or type your message instead.",
                http_code=502,
            ) from exc

        finally:
            # Step 5: Always clean up the temp file
            delete_file(tmp_path)
