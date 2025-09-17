"""
Blob-based streaming transcriber for near real-time audio processing.
Uses WAV blobs from frontend with file upload API quality.
"""

import asyncio
import json
import logging
import time
import io
import base64
from typing import Dict, Optional

from .audio_utils import validate_wav_format
from .normalization import NormalizationPipeline

logger = logging.getLogger(__name__)


class BlobTranscriber:
    """
    Blob-based streaming transcriber that uses WAV blobs for perfect quality.

    Frontend flow: Mic → VAD → WAV blob (2-3s) → WebSocket → File Upload API path
    This gives near real-time transcription with file upload quality.
    """

    def __init__(self, ai_factory, normalization_pipeline: Optional[NormalizationPipeline] = None):
        """
        Initialize blob transcriber.

        Args:
            ai_factory: AI factory instance
            normalization_pipeline: Pipeline for text normalization
        """
        self.ai_factory = ai_factory
        self.normalization_pipeline = normalization_pipeline
        self.active_transcriptions: Dict[str, asyncio.Task] = {}

        logger.info("🎯 BlobTranscriber initialized for near real-time WAV blob processing")

    async def handle_wav_blob(self, client_id: str, audio_message: dict, websocket_manager) -> bool:
        """
        Handle WAV blob using file upload API path for perfect quality.

        Args:
            client_id: Client identifier
            audio_message: Audio message containing WAV blob
            websocket_manager: WebSocket connection manager

        Returns:
            bool: True if transcription was triggered
        """
        try:
            # Extract WAV blob data
            wav_data = self._extract_wav_blob(audio_message)
            if not wav_data:
                await self._send_error(client_id, "No valid WAV blob found", websocket_manager)
                return False

            # Validate WAV format
            is_valid, error_msg, format_info = validate_wav_format(wav_data)
            if not is_valid:
                await self._send_error(client_id, f"Invalid WAV blob: {error_msg}", websocket_manager)
                return False

            duration_ms = format_info.get('duration_ms', 0)
            logger.info(f"🎵 Processing WAV blob for {client_id}: {duration_ms:.0f}ms, {len(wav_data)} bytes")

            # Cancel any existing transcription for this client
            if client_id in self.active_transcriptions:
                if not self.active_transcriptions[client_id].done():
                    self.active_transcriptions[client_id].cancel()

            # Start async transcription using file upload API path
            task = asyncio.create_task(
                self._transcribe_wav_blob(client_id, wav_data, websocket_manager, format_info)
            )
            self.active_transcriptions[client_id] = task

            logger.info(f"🚀 Started WAV blob transcription for {client_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Error handling WAV blob for {client_id}: {e}")
            await self._send_error(client_id, f"WAV blob processing failed: {str(e)}", websocket_manager)
            return False

    def _extract_wav_blob(self, audio_message: dict) -> Optional[bytes]:
        """Extract WAV blob from audio message."""
        # Try different data fields
        for field in ["data", "audio_data", "blob_data"]:
            if field in audio_message:
                data = audio_message[field]

                if isinstance(data, bytes):
                    return data
                elif isinstance(data, str):
                    try:
                        return base64.b64decode(data)
                    except Exception as e:
                        logger.warning(f"Failed to decode base64 from {field}: {e}")
                        continue

        return None

    async def _transcribe_wav_blob(self, client_id: str, wav_data: bytes,
                                  websocket_manager, format_info: dict):
        """
        Transcribe WAV blob using EXACT same logic as file upload API.
        This ensures identical quality and behavior.
        """
        try:
            # Get ASR provider (same as file upload API)
            provider = await self.ai_factory.get_or_create_asr_provider()
            if not provider:
                await self._send_error(client_id, "Transcription service unavailable", websocket_manager)
                return

            # Create audio buffer EXACTLY like file upload API
            audio_buffer = io.BytesIO(wav_data)
            audio_buffer.name = "blob.wav"

            # Get OpenAI prompt from Supabase (EXACT same logic as file upload)
            openai_prompt = ""
            try:
                if hasattr(self.ai_factory, 'data_registry') and self.ai_factory.data_registry:
                    admin_id = self.ai_factory.data_registry.loader.get_admin_id()
                    config_data = await self.ai_factory.data_registry.get_config(admin_id)
                    openai_prompt = config_data.get('openai_prompt', '') if config_data else ''
                    logger.debug(f"✅ Using Supabase openai_prompt: {len(openai_prompt)} chars")
            except Exception as e:
                logger.warning(f"⚠️ Failed to get openai_prompt: {e}")

            # Transcribe with EXACT same parameters as file upload API
            logger.info(f"🎯 Transcribing WAV blob for {client_id} using file upload API path")

            result = await provider.transcribe(
                audio_data=audio_buffer,
                language="nl",
                prompt=None,  # Use openai_prompt from Supabase instead
                openai_prompt=openai_prompt,
                format="wav"
            )

            if not result or not result.text:
                logger.warning(f"Empty transcription result for {client_id}")
                return

            # Apply normalization (EXACT same logic as file upload API)
            raw_text = result.text
            normalized_text = raw_text

            if self.normalization_pipeline:
                try:
                    norm_result = self.normalization_pipeline.normalize(raw_text, language="nl")
                    normalized_text = norm_result.normalized_text
                    logger.debug(f"🔄 Normalized: '{raw_text}' → '{normalized_text}'")
                except Exception as e:
                    logger.warning(f"⚠️ Normalization failed: {e}")

            # Send transcription result (same format as file upload API)
            transcription_message = {
                "type": "transcription_result",
                "text": normalized_text,
                "raw": raw_text,
                "normalized": normalized_text,
                "language": result.language or "nl",
                "duration": result.duration or (format_info.get('duration_ms', 0) / 1000),
                "confidence": 1.0,
                "timestamp": time.time(),
                "source": "blob_streaming",
                "provider": provider.get_info().name if hasattr(provider, 'get_info') else "unknown",
                "blob_size": len(wav_data),
                "blob_duration_ms": format_info.get('duration_ms', 0)
            }

            await websocket_manager.send_personal_message(
                json.dumps(transcription_message),
                client_id
            )

            logger.info(f"📝 Sent blob transcription to {client_id}: '{normalized_text[:50]}...'")

        except asyncio.CancelledError:
            logger.info(f"Transcription cancelled for {client_id}")
        except Exception as e:
            logger.error(f"❌ Error transcribing WAV blob for {client_id}: {e}")
            await self._send_error(client_id, f"Transcription failed: {str(e)}", websocket_manager)

    async def cleanup_client(self, client_id: str):
        """Clean up client transcription tasks."""
        if client_id in self.active_transcriptions:
            task = self.active_transcriptions[client_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.active_transcriptions[client_id]
            logger.info(f"🧹 Cleaned up blob transcription for {client_id}")

    async def _send_error(self, client_id: str, error_message: str, websocket_manager):
        """Send error message to client."""
        try:
            error_msg = {
                "type": "transcription_error",
                "error": error_message,
                "timestamp": time.time()
            }
            await websocket_manager.send_personal_message(
                json.dumps(error_msg),
                client_id
            )
        except Exception as e:
            logger.error(f"Failed to send error message to {client_id}: {e}")

    def get_stats(self) -> dict:
        """Get transcriber statistics."""
        return {
            "active_transcriptions": len(self.active_transcriptions),
            "clients": list(self.active_transcriptions.keys())
        }