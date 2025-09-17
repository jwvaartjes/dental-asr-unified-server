"""
Real-time transcriber using OpenAI Realtime API with smart endpointing.
Replaces the chunk-based streaming transcriber with continuous audio processing.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Optional, Any
import os

from .providers.openai_realtime_provider import OpenAIRealtimeProvider
from .audio_utils import AudioAnalyzer, calculate_duration_ms, validate_wav_format, wav_to_pcm_chunks
from .normalization import NormalizationPipeline

logger = logging.getLogger(__name__)


class RealtimeTranscriber:
    """
    Real-time transcriber using OpenAI Realtime API with smart endpointing.

    Features:
    - Continuous audio streaming to OpenAI
    - Smart endpointing based on RMS energy and silence detection
    - Configurable timing parameters
    - Normalization pipeline integration
    """

    def __init__(self, ai_factory=None, normalization_pipeline: Optional[NormalizationPipeline] = None):
        """
        Initialize realtime transcriber.

        Args:
            ai_factory: AI factory instance (for compatibility)
            normalization_pipeline: Pipeline for text normalization
        """
        self.ai_factory = ai_factory
        self.normalization_pipeline = normalization_pipeline

        # Client sessions
        self.client_sessions: Dict[str, 'ClientSession'] = {}

        # Endpointing configuration (tunable via environment)
        self.min_chunk_ms = int(os.getenv("REALTIME_MIN_CHUNK_MS", "900"))
        self.max_chunk_ms = int(os.getenv("REALTIME_MAX_CHUNK_MS", "2000"))
        self.silence_ms = int(os.getenv("REALTIME_SILENCE_MS", "400"))

        # Audio analysis thresholds
        self.rms_voice_threshold = float(os.getenv("REALTIME_RMS_VOICE", "0.015"))
        self.rms_silence_threshold = float(os.getenv("REALTIME_RMS_SILENCE", "0.010"))
        self.zcr_max = float(os.getenv("REALTIME_ZCR_MAX", "0.15"))

        logger.info(f"🎙️ RealtimeTranscriber initialized with endpointing: "
                   f"min={self.min_chunk_ms}ms, max={self.max_chunk_ms}ms, silence={self.silence_ms}ms")

    async def handle_wav_audio(self, client_id: str, wav_data: bytes, websocket_manager) -> bool:
        """
        Handle complete WAV audio file using hybrid approach.
        Frontend → VAD → WAV → Server chunks to PCM → Realtime API.

        Args:
            client_id: Client identifier
            wav_data: Complete WAV file as bytes
            websocket_manager: WebSocket connection manager

        Returns:
            bool: True if audio was processed successfully
        """
        try:
            # Validate WAV format first
            is_valid, error_msg, format_info = validate_wav_format(wav_data)
            if not is_valid:
                await self._send_error(client_id, f"Invalid WAV format: {error_msg}", websocket_manager)
                return False

            duration_ms = format_info.get('duration_ms', 0)
            logger.info(f"🎵 Processing WAV audio for {client_id}: "
                       f"{duration_ms:.0f}ms, "
                       f"{format_info.get('frames', 0)} frames")

            # Check minimum duration (OpenAI requires at least 100ms)
            if duration_ms < 100:
                logger.warning(f"⚠️ Audio too short for {client_id}: {duration_ms}ms (minimum 100ms required)")
                await self._send_error(client_id, f"Audio too short: {duration_ms:.0f}ms (minimum 100ms)", websocket_manager)
                return False

            # Create OpenAI Realtime provider for this WAV
            provider = OpenAIRealtimeProvider()
            await provider.initialize()

            # Start Realtime session
            transcription_received = asyncio.Event()
            transcription_result = {"text": "", "deltas": [], "final_text": ""}

            async def handle_transcription(text: str):
                # Accumulate all transcription parts
                transcription_result["deltas"].append(text)

                # Combine all parts into complete text
                complete_text = " ".join(transcription_result["deltas"])
                transcription_result["text"] = complete_text

                logger.info(f"🔄 Transcription part for {client_id}: '{text}' (total: '{complete_text}')")

                # Set event immediately - each transcription part is complete
                transcription_received.set()

            async def handle_error(error: str):
                logger.error(f"❌ Realtime API error for {client_id}: {error}")
                transcription_received.set()

            success = await provider.start_session(
                transcription_handler=handle_transcription,
                error_handler=handle_error
            )

            if not success:
                await self._send_error(client_id, "Failed to start Realtime session", websocket_manager)
                return False

            # Process all audio in one go (no chunking delays)
            chunk_ms = int(os.getenv("REALTIME_WAV_CHUNK_MS", "40"))  # 40ms chunks
            min_buffer_ms = 120  # Minimum 120ms as per OpenAI requirement

            logger.info(f"📤 Streaming all audio with {chunk_ms}ms chunks")

            # Send all chunks first
            chunk_count = 0
            for pcm_chunk in wav_to_pcm_chunks(wav_data, chunk_ms=chunk_ms):
                await provider.append_audio(pcm_chunk)
                chunk_count += 1

                # Small delay every few chunks to avoid overwhelming
                if chunk_count % 10 == 0:
                    await asyncio.sleep(0.005)

            accumulated_ms = chunk_count * chunk_ms

            # Ensure we have enough audio before commit
            if accumulated_ms < min_buffer_ms:
                logger.warning(f"⚠️ Audio too short: {accumulated_ms}ms < {min_buffer_ms}ms minimum")
                await self._send_error(client_id, f"Audio too short for processing", websocket_manager)
                return False

            # Commit all accumulated audio for transcription
            logger.info(f"📤 Committing {accumulated_ms}ms of audio ({chunk_count} chunks)")
            await provider.commit_audio()

            total_audio_ms = chunk_count * chunk_ms
            logger.info(f"📤 Sent {chunk_count} PCM chunks ({chunk_ms}ms each) = {total_audio_ms}ms total to OpenAI for {client_id}")
            logger.info(f"   Expected: {duration_ms}ms, Sent: {total_audio_ms}ms, Coverage: {(total_audio_ms/duration_ms)*100:.1f}%")

            # Wait for transcription result (with timeout)
            try:
                await asyncio.wait_for(transcription_received.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                await self._send_error(client_id, "Transcription timeout", websocket_manager)
                return False

            # Process and send result
            raw_text = transcription_result["text"]
            if not raw_text.strip():
                # Empty transcription - might be silence
                logger.info(f"🤐 Empty transcription for {client_id} (likely silence)")
                return True

            # Apply normalization if available
            normalized_text = raw_text
            if self.normalization_pipeline:
                try:
                    norm_result = self.normalization_pipeline.normalize(raw_text, language="nl")
                    normalized_text = norm_result.normalized_text
                    logger.debug(f"🔄 Normalized: '{raw_text}' → '{normalized_text}'")
                except Exception as e:
                    logger.warning(f"⚠️ Normalization failed: {e}")

            # Send transcription result
            transcription_message = {
                "type": "transcription_result",
                "text": normalized_text,
                "raw": raw_text,
                "normalized": normalized_text,
                "language": "nl",
                "confidence": 1.0,
                "timestamp": time.time(),
                "source": "realtime_wav",
                "format": "wav",
                "duration_ms": format_info.get('duration_ms', 0),
                "chunks_sent": chunk_count
            }

            await websocket_manager.send_personal_message(
                json.dumps(transcription_message),
                client_id
            )

            logger.info(f"📝 Sent WAV transcription to {client_id}: '{normalized_text[:50]}...'")

            # Cleanup
            await provider.stop_session()
            return True

        except Exception as e:
            logger.error(f"❌ Error processing WAV audio for {client_id}: {e}")
            await self._send_error(client_id, f"WAV processing failed: {str(e)}", websocket_manager)
            return False

    async def handle_audio_chunk(self, client_id: str, audio_message: dict, websocket_manager) -> bool:
        """
        Handle incoming audio chunk from WebSocket.

        Args:
            client_id: Client identifier
            audio_message: Audio message from WebSocket
            websocket_manager: WebSocket connection manager

        Returns:
            bool: True if audio was processed
        """
        try:
            # Get or create client session
            if client_id not in self.client_sessions:
                session = await self._create_client_session(client_id, websocket_manager)
                if not session:
                    return False
                self.client_sessions[client_id] = session

            session = self.client_sessions[client_id]

            # Extract audio data
            audio_data = self._extract_audio_data(audio_message)
            if not audio_data:
                return False

            # Process audio through session
            await session.process_audio(audio_data)
            return True

        except Exception as e:
            logger.error(f"❌ Error handling audio chunk for {client_id}: {e}")
            await self._send_error(client_id, f"Audio processing failed: {str(e)}", websocket_manager)
            return False

    def _extract_audio_data(self, audio_message: dict) -> Optional[bytes]:
        """Extract binary audio data from WebSocket message."""
        if "data" in audio_message:
            data = audio_message["data"]
            if isinstance(data, bytes):
                return data
            elif isinstance(data, str):
                # Try base64 decode
                try:
                    import base64
                    return base64.b64decode(data)
                except Exception:
                    logger.warning("Failed to decode base64 audio data")
                    return None

        elif "audio_data" in audio_message:
            # Base64 encoded audio data
            try:
                import base64
                return base64.b64decode(audio_message["audio_data"])
            except Exception as e:
                logger.warning(f"Failed to decode base64 audio_data: {e}")
                return None

        return None

    def _is_wav_format(self, audio_message: dict) -> bool:
        """Check if the audio message indicates WAV format."""
        # Check explicit format field
        format_field = audio_message.get("format", "").lower()
        if format_field in ["wav", "wave"]:
            return True

        # Check if data looks like WAV (starts with RIFF header)
        audio_data = self._extract_audio_data(audio_message)
        if audio_data and len(audio_data) >= 12:
            return audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE'

        return False

    async def handle_audio_message(self, client_id: str, audio_message: dict, websocket_manager) -> bool:
        """
        Handle audio message - routes to appropriate handler based on format.

        Args:
            client_id: Client identifier
            audio_message: Audio message from WebSocket
            websocket_manager: WebSocket connection manager

        Returns:
            bool: True if audio was processed
        """
        logger.info(f"🎯 RealtimeTranscriber.handle_audio_message called for {client_id}")
        logger.info(f"   Message type: {audio_message.get('type')}")
        logger.info(f"   Message format: {audio_message.get('format', 'not specified')}")

        try:
            # Determine if this is WAV format for hybrid approach
            is_wav = self._is_wav_format(audio_message)
            logger.info(f"   WAV format detected: {is_wav}")

            if is_wav:
                logger.info(f"🎵 Detected WAV format for {client_id} - using hybrid approach")
                audio_data = self._extract_audio_data(audio_message)
                if audio_data:
                    logger.info(f"   Extracted audio data: {len(audio_data)} bytes")
                    return await self.handle_wav_audio(client_id, audio_data, websocket_manager)
                else:
                    logger.warning(f"⚠️ Failed to extract WAV data for {client_id}")
                    return False
            else:
                # Use original streaming approach for PCM chunks
                logger.info(f"🔊 Using streaming approach for {client_id}")
                return await self.handle_audio_chunk(client_id, audio_message, websocket_manager)

        except Exception as e:
            logger.error(f"❌ Error handling audio message for {client_id}: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            await self._send_error(client_id, f"Audio message processing failed: {str(e)}", websocket_manager)
            return False

    async def _create_client_session(self, client_id: str, websocket_manager) -> Optional['ClientSession']:
        """Create a new client session with Realtime provider."""
        try:
            # Create OpenAI Realtime provider
            provider = OpenAIRealtimeProvider()
            await provider.initialize()

            # Create client session
            session = ClientSession(
                client_id=client_id,
                provider=provider,
                websocket_manager=websocket_manager,
                transcriber=self
            )

            # Start Realtime session
            success = await session.start()
            if not success:
                logger.error(f"❌ Failed to start session for {client_id}")
                return None

            logger.info(f"✅ Created Realtime session for {client_id}")
            return session

        except Exception as e:
            logger.error(f"❌ Failed to create session for {client_id}: {e}")
            return None

    async def cleanup_client(self, client_id: str, websocket_manager=None) -> None:
        """Clean up client session."""
        if client_id in self.client_sessions:
            session = self.client_sessions[client_id]
            await session.stop()
            del self.client_sessions[client_id]
            logger.info(f"🧹 Cleaned up Realtime session for {client_id}")

    async def force_flush_client(self, client_id: str, websocket_manager) -> bool:
        """Force flush any pending audio for a client."""
        if client_id in self.client_sessions:
            session = self.client_sessions[client_id]
            await session.force_commit()
            return True
        return False

    async def _send_error(self, client_id: str, error_message: str, websocket_manager) -> None:
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


class ClientSession:
    """
    Individual client session managing OpenAI Realtime connection and endpointing logic.
    """

    def __init__(self, client_id: str, provider: OpenAIRealtimeProvider,
                 websocket_manager, transcriber: RealtimeTranscriber):
        """Initialize client session."""
        self.client_id = client_id
        self.provider = provider
        self.websocket_manager = websocket_manager
        self.transcriber = transcriber

        # Audio analysis
        self.audio_analyzer = AudioAnalyzer(
            voice_rms_threshold=transcriber.rms_voice_threshold,
            silence_rms_threshold=transcriber.rms_silence_threshold,
            zcr_max=transcriber.zcr_max
        )

        # Timing state
        self.chunk_start_time = time.time()
        self.last_voice_time = time.time()
        self.accumulated_audio = bytearray()

        # Transcription buffer
        self.current_transcription = ""

    async def start(self) -> bool:
        """Start the Realtime session."""
        try:
            success = await self.provider.start_session(
                transcription_handler=self._handle_transcription,
                error_handler=self._handle_error
            )

            if success:
                self.chunk_start_time = time.time()
                self.last_voice_time = time.time()
                logger.info(f"🚀 Started Realtime session for {self.client_id}")

            return success

        except Exception as e:
            logger.error(f"❌ Failed to start session for {self.client_id}: {e}")
            return False

    async def stop(self) -> None:
        """Stop the Realtime session."""
        try:
            # Final commit if we have pending audio
            if len(self.accumulated_audio) > 0:
                await self.force_commit()

            await self.provider.stop_session()
            logger.info(f"🛑 Stopped Realtime session for {self.client_id}")

        except Exception as e:
            logger.error(f"❌ Error stopping session for {self.client_id}: {e}")

    async def process_audio(self, audio_data: bytes) -> None:
        """
        Process incoming audio with smart endpointing.

        Args:
            audio_data: PCM16LE mono 16kHz audio bytes
        """
        # 1. Append to OpenAI (continuous streaming)
        await self.provider.append_audio(audio_data)
        self.accumulated_audio.extend(audio_data)

        # 2. Analyze audio for endpointing
        analysis = self.audio_analyzer.analyze_frame(audio_data)

        now = time.time()
        elapsed_ms = (now - self.chunk_start_time) * 1000
        idle_ms = (now - self.last_voice_time) * 1000

        # Update voice timing
        if analysis['is_voice']:
            self.last_voice_time = now

        # 3. Decide whether to commit
        should_commit = False

        # Silence-based commit (after minimum duration)
        if (analysis['is_silence'] and
            elapsed_ms >= self.transcriber.min_chunk_ms and
            idle_ms >= self.transcriber.silence_ms):
            should_commit = True
            logger.debug(f"🤐 Silence commit for {self.client_id}: "
                        f"elapsed={elapsed_ms:.0f}ms, idle={idle_ms:.0f}ms")

        # Hard cap commit
        elif elapsed_ms >= self.transcriber.max_chunk_ms:
            should_commit = True
            logger.debug(f"⏰ Max duration commit for {self.client_id}: "
                        f"elapsed={elapsed_ms:.0f}ms")

        # 4. Commit if needed
        if should_commit and len(self.accumulated_audio) > 0:
            await self._commit_audio()

    async def _commit_audio(self) -> None:
        """Commit current audio buffer and request transcription."""
        try:
            # Commit to OpenAI
            await self.provider.commit_audio()

            # Reset timing
            self.chunk_start_time = time.time()
            self.last_voice_time = time.time()

            # Clear buffer
            buffer_size = len(self.accumulated_audio)
            self.accumulated_audio.clear()

            logger.debug(f"📤 Committed {buffer_size} bytes for {self.client_id}")

        except Exception as e:
            logger.error(f"❌ Failed to commit audio for {self.client_id}: {e}")

    async def force_commit(self) -> None:
        """Force commit any pending audio."""
        if len(self.accumulated_audio) > 0:
            await self._commit_audio()

    async def _handle_transcription(self, text: str) -> None:
        """Handle transcription result from OpenAI."""
        try:
            if not text.strip():
                return

            # Apply normalization if pipeline available
            raw_text = text
            normalized_text = raw_text

            if self.transcriber.normalization_pipeline:
                try:
                    norm_result = self.transcriber.normalization_pipeline.normalize(
                        text, language="nl"
                    )
                    normalized_text = norm_result.normalized_text
                    logger.debug(f"🔄 Normalized: '{raw_text}' → '{normalized_text}'")
                except Exception as e:
                    logger.warning(f"⚠️ Normalization failed: {e}")

            # Send transcription result
            transcription_message = {
                "type": "transcription_result",
                "text": normalized_text,
                "raw": raw_text,
                "normalized": normalized_text,
                "language": "nl",
                "confidence": 1.0,
                "timestamp": time.time(),
                "source": "realtime"
            }

            await self.websocket_manager.send_personal_message(
                json.dumps(transcription_message),
                self.client_id
            )

            logger.info(f"📝 Sent transcription to {self.client_id}: '{normalized_text[:50]}...'")

        except Exception as e:
            logger.error(f"❌ Error handling transcription for {self.client_id}: {e}")

    async def _handle_error(self, error_message: str) -> None:
        """Handle error from OpenAI Realtime API."""
        logger.error(f"❌ Realtime API error for {self.client_id}: {error_message}")

        try:
            error_msg = {
                "type": "transcription_error",
                "error": f"Realtime API error: {error_message}",
                "timestamp": time.time()
            }
            await self.websocket_manager.send_personal_message(
                json.dumps(error_msg),
                self.client_id
            )
        except Exception as e:
            logger.error(f"Failed to send error message to {self.client_id}: {e}")