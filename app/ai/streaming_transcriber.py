"""
Streaming Audio Transcription Handler for WebSocket
Manages audio chunks and triggers transcription when enough data is accumulated
"""
import asyncio
import base64
import io
import logging
import time
from typing import Dict, Optional, List
import wave

logger = logging.getLogger(__name__)

class AudioBuffer:
    """Manages audio chunks from WebSocket for streaming transcription (SPSC-style)"""

    def __init__(self, max_duration_ms: int = 500, min_duration_ms: int = 100,
                 file_chunk_threshold: int = 2048, chunk_accumulation_count: int = 3):
        """
        Initialize audio buffer with SPSC-style processing like old server
        Args:
            max_duration_ms: Maximum duration before triggering transcription (ms)
            min_duration_ms: Minimum duration required for transcription (ms)
            file_chunk_threshold: Size threshold for immediate processing (bytes)
            chunk_accumulation_count: Number of small chunks to accumulate before processing
        """
        # SPSC-style pending audio accumulation (like old server)
        self.pending_audio: List[bytes] = []  # Exactly like old server
        self.chunk_counter = 0
        self.total_accumulated_size = 0

        # Timing for safety fallbacks
        self.first_chunk_time = None
        self.last_chunk_time = None
        self.max_duration_ms = max_duration_ms
        self.min_duration_ms = min_duration_ms

        # Audio format
        self.sample_rate = 16000  # Default sample rate
        self.channels = 1         # Mono audio
        self.sample_width = 2     # 16-bit audio

        # SPSC thresholds (exactly like old server)
        self.file_chunk_threshold = file_chunk_threshold
        self.chunk_accumulation_count = chunk_accumulation_count

        logger.info(f"AudioBuffer initialized: file_chunk_threshold={file_chunk_threshold}B, chunk_accumulation_count={chunk_accumulation_count}")

    def should_flush(self) -> bool:
        """Check if we should flush pending audio for any reason"""
        if not self.pending_audio:
            return False

        # Time-based flush (safety mechanism)
        if self.first_chunk_time:
            elapsed_ms = (time.time() * 1000) - self.first_chunk_time
            if elapsed_ms >= self.max_duration_ms:
                logger.debug(f"Time-based flush triggered: {elapsed_ms:.0f}ms >= {self.max_duration_ms}ms")
                return True

        return False

    def flush_pending(self) -> Optional[bytes]:
        """Flush all pending audio and return combined data (like old server)"""
        if not self.pending_audio:
            return None

        combined_data = b''.join(self.pending_audio)
        logger.info(f"Flushing {len(self.pending_audio)} pending chunks ({len(combined_data)} bytes)")

        # Clear state
        self.pending_audio.clear()
        self.total_accumulated_size = 0
        self.first_chunk_time = None
        self.last_chunk_time = None
        self.chunk_counter += 1

        return combined_data

    def add_chunk(self, audio_data: bytes) -> Optional[bytes]:
        """
        Add audio chunk using EXACT old server logic
        Returns combined audio data if ready for transcription, None otherwise
        """
        current_time = time.time() * 1000  # Convert to ms

        logger.debug(f"🔍 Received {len(audio_data)} bytes of audio")

        # Track timing for first chunk
        if not self.pending_audio:
            self.first_chunk_time = current_time

        self.last_chunk_time = current_time

        # EXACT OLD SERVER LOGIC:
        # Process large chunks immediately, buffer small ones
        if len(audio_data) > self.file_chunk_threshold:
            # Large WebSocket chunks (e.g., cockpit 3s chunks) - process immediately as LIVE_MIC
            logger.info(f"Large chunk ({len(audio_data)}B > {self.file_chunk_threshold}B) - processing immediately")

            # If we have pending audio, combine it with this large chunk
            if self.pending_audio:
                combined_data = b''.join(self.pending_audio) + audio_data
                logger.info(f"Combining {len(self.pending_audio)} pending chunks + large chunk = {len(combined_data)} bytes")
                self.pending_audio.clear()
                self.total_accumulated_size = 0
                self.first_chunk_time = None
            else:
                combined_data = audio_data

            self.chunk_counter += 1
            return combined_data

        else:
            # Buffer small chunks for batched processing
            self.pending_audio.append(audio_data)
            self.total_accumulated_size += len(audio_data)

            # Process when enough accumulated
            if len(self.pending_audio) >= self.chunk_accumulation_count:
                logger.info(f"Accumulated {len(self.pending_audio)} chunks ({self.total_accumulated_size}B) - processing batch")

                combined_data = b''.join(self.pending_audio)
                self.pending_audio.clear()
                self.total_accumulated_size = 0
                self.first_chunk_time = None
                self.chunk_counter += 1

                return combined_data

            # Check time-based fallback
            if self.should_flush():
                logger.info(f"Time-based flush: {len(self.pending_audio)} chunks ({self.total_accumulated_size}B)")
                return self.flush_pending()

            logger.debug(f"Buffer: {len(self.pending_audio)} chunks, {self.total_accumulated_size}B - waiting for more")
            return None

    def convert_to_wav(self, pcm_data: bytes) -> Optional[bytes]:
        """Convert raw PCM16LE data to WAV format"""
        if not pcm_data:
            return None

        try:
            # Create WAV file in memory
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(self.channels)      # 1 = mono
                wav_file.setsampwidth(self.sample_width)  # 2 = 16-bit
                wav_file.setframerate(self.sample_rate)   # 16000 Hz
                wav_file.writeframes(pcm_data)            # Write PCM data

            wav_data = wav_buffer.getvalue()
            logger.debug(f"✅ Generated WAV: {len(wav_data)} bytes from {len(pcm_data)} bytes PCM")
            return wav_data

        except Exception as e:
            logger.error(f"Failed to create WAV data: {e}")
            return None

    def combine_wav_chunks(self, wav_chunks: List[bytes]) -> Optional[bytes]:
        """
        Combine multiple WAV chunks into single WAV file with correct headers.
        No PCM conversion needed - direct WAV concatenation.
        """
        if not wav_chunks:
            return None

        try:
            # If we have a single WAV chunk, return it directly
            if len(wav_chunks) == 1:
                logger.debug(f"✅ Single WAV chunk: {len(wav_chunks[0])} bytes")
                return wav_chunks[0]

            # For multiple WAV chunks, extract PCM data and combine
            combined_pcm = bytearray()
            sample_rate = self.sample_rate
            channels = self.channels
            sample_width = self.sample_width

            for i, wav_chunk in enumerate(wav_chunks):
                try:
                    # Read WAV chunk and extract PCM data
                    wav_buffer = io.BytesIO(wav_chunk)
                    with wave.open(wav_buffer, 'rb') as wav_file:
                        # Verify format consistency
                        if wav_file.getframerate() != sample_rate:
                            logger.warning(f"Inconsistent sample rate in chunk {i}: {wav_file.getframerate()} vs {sample_rate}")

                        # Extract PCM frames
                        pcm_frames = wav_file.readframes(wav_file.getnframes())
                        combined_pcm.extend(pcm_frames)

                        logger.debug(f"Extracted {len(pcm_frames)} bytes PCM from WAV chunk {i}")

                except Exception as e:
                    logger.warning(f"Failed to process WAV chunk {i}: {e}")
                    continue

            if not combined_pcm:
                logger.error("No valid PCM data found in WAV chunks")
                return None

            # Create final WAV with combined PCM data
            final_wav_buffer = io.BytesIO()
            with wave.open(final_wav_buffer, 'wb') as final_wav:
                final_wav.setnchannels(channels)
                final_wav.setsampwidth(sample_width)
                final_wav.setframerate(sample_rate)
                final_wav.writeframes(combined_pcm)

            final_wav_data = final_wav_buffer.getvalue()
            duration_ms = (len(combined_pcm) / (sample_rate * sample_width)) * 1000

            logger.info(f"✅ Combined {len(wav_chunks)} WAV chunks into {len(final_wav_data)} bytes ({duration_ms:.0f}ms)")
            return final_wav_data

        except Exception as e:
            logger.error(f"Failed to combine WAV chunks: {e}")
            return None

    def force_flush(self) -> Optional[bytes]:
        """Force flush any pending audio (for connection close, etc.)"""
        if self.pending_audio:
            logger.info(f"Force flushing {len(self.pending_audio)} pending chunks")
            return self.flush_pending()
        return None

    def get_stats(self) -> dict:
        """Get current buffer statistics"""
        return {
            "pending_chunks": len(self.pending_audio),
            "accumulated_bytes": self.total_accumulated_size,
            "chunk_counter": self.chunk_counter,
            "has_pending": bool(self.pending_audio)
        }


class StreamingTranscriber:
    """Manages streaming transcription for WebSocket connections"""

    def __init__(self, ai_factory, normalization_pipeline=None):
        """
        Initialize streaming transcriber
        Args:
            ai_factory: AI factory instance for creating transcription providers
            normalization_pipeline: Pipeline for text normalization
        """
        self.ai_factory = ai_factory
        self.normalization_pipeline = normalization_pipeline
        self.client_buffers: Dict[str, AudioBuffer] = {}
        self.transcription_tasks: Dict[str, asyncio.Task] = {}

    async def handle_audio_chunk(self, client_id: str, audio_message: dict, websocket_manager) -> bool:
        """
        Handle incoming audio chunk from WebSocket (simplified like old server)
        Returns True if transcription was triggered
        """
        try:
            # Get or create audio buffer for client (with config from message if available)
            if client_id not in self.client_buffers:
                # Load thresholds from config if available
                config_thresholds = await self._get_streaming_config()
                self.client_buffers[client_id] = AudioBuffer(
                    file_chunk_threshold=config_thresholds.get('file_chunk_threshold_bytes', 2048),
                    chunk_accumulation_count=config_thresholds.get('chunk_accumulation_count', 3)
                )
                logger.info(f"Created audio buffer for client {client_id} with thresholds: {config_thresholds}")

            buffer = self.client_buffers[client_id]

            # Extract raw audio data (simplified logic like old server)
            audio_data = None

            if "audio_data" in audio_message:
                # Base64 encoded audio data (for JSON text messages)
                try:
                    audio_data = base64.b64decode(audio_message["audio_data"])
                    logger.debug(f"✅ Decoded base64 audio: {len(audio_data)} bytes")
                except Exception as e:
                    logger.error(f"Failed to decode base64 audio: {e}")
                    return False

            elif "data" in audio_message:
                # Raw binary data (most common case for desktop streaming)
                data = audio_message["data"]
                if isinstance(data, bytes):
                    # Direct bytes from WebSocket binary message - this is what we want!
                    audio_data = data
                    logger.debug(f"✅ Using raw binary data: {len(audio_data)} bytes")
                elif isinstance(data, str):
                    # Try base64 first, then give up
                    try:
                        audio_data = base64.b64decode(data)
                        logger.debug(f"✅ Decoded base64 string: {len(audio_data)} bytes")
                    except:
                        logger.warning(f"Cannot decode string data as base64 from {client_id}")
                        return False
                else:
                    logger.warning(f"Unsupported data type {type(data)} from {client_id}")
                    return False

            if not audio_data or not isinstance(audio_data, bytes):
                logger.warning(f"No valid audio data found in message from {client_id}")
                return False

            # Add chunk using SPSC logic - returns combined data if ready for transcription
            combined_audio_data = buffer.add_chunk(audio_data)

            if combined_audio_data:
                # We have audio ready for transcription
                logger.info(f"Processing {len(combined_audio_data)} bytes of combined audio for {client_id}")

                # Cancel any existing transcription task for this client
                if client_id in self.transcription_tasks:
                    if not self.transcription_tasks[client_id].done():
                        self.transcription_tasks[client_id].cancel()

                # Start async transcription with the combined data
                task = asyncio.create_task(
                    self._transcribe_audio_data(client_id, combined_audio_data, websocket_manager)
                )
                self.transcription_tasks[client_id] = task
                logger.info(f"Started transcription task for client {client_id}")
                return True

            else:
                # Audio is buffered, waiting for more chunks
                stats = buffer.get_stats()
                logger.debug(f"Audio buffered for {client_id}: {stats}")
                return False

        except Exception as e:
            logger.error(f"Error handling audio chunk from {client_id}: {e}")
            return False

    async def _get_streaming_config(self) -> dict:
        """Get streaming configuration from data registry (like old server)"""
        try:
            if hasattr(self.ai_factory, 'data_registry') and self.ai_factory.data_registry:
                config_data = await self.ai_factory.data_registry.get_admin_config()
                if config_data and 'streaming' in config_data:
                    return config_data['streaming']
        except Exception as e:
            logger.warning(f"Failed to get streaming config: {e}")

        # Optimized defaults for better streaming (2048 bytes = 64ms @ 16kHz)
        return {
            'file_chunk_threshold_bytes': 2048,
            'chunk_accumulation_count': 3
        }

    async def _transcribe_audio_data(self, client_id: str, pcm_data: bytes, websocket_manager):
        """Transcribe combined PCM audio data for client (SPSC-style)"""
        try:
            if client_id not in self.client_buffers:
                logger.warning(f"No buffer found for client {client_id}")
                return

            buffer = self.client_buffers[client_id]

            # Convert raw PCM to WAV format
            wav_data = buffer.convert_to_wav(pcm_data)
            if not wav_data:
                logger.warning(f"Failed to convert PCM to WAV for client {client_id}")
                return

            logger.info(f"Starting transcription for client {client_id}: {len(wav_data)} bytes WAV from {len(pcm_data)} bytes PCM")

            # Create transcription provider
            provider = await self.ai_factory.get_or_create_asr_provider()

            if not provider:
                logger.error("No transcription provider available")
                await self._send_error(client_id, "Transcription service unavailable", websocket_manager)
                return

            # Create BytesIO buffer from WAV data (like the working /api/ai/transcribe endpoint)
            logger.debug(f"🔍 Creating BytesIO from wav_data: type={type(wav_data)}, len={len(wav_data)} bytes")
            audio_buffer = io.BytesIO(wav_data)
            audio_buffer.name = "audio.wav"
            logger.debug(f"✅ Created audio_buffer: type={type(audio_buffer)}, name={audio_buffer.name}")

            # Get OpenAI prompt from config (exactly like legacy server)
            openai_prompt = ""
            try:
                # Try to get prompt from data registry if available
                if hasattr(self.ai_factory, 'data_registry') and self.ai_factory.data_registry:
                    # Use identical logic as file upload endpoint
                    admin_id = self.ai_factory.data_registry.loader.get_admin_id()
                    config_data = await self.ai_factory.data_registry.get_config(admin_id)
                    openai_prompt = config_data.get('openai_prompt', '') if config_data else ''
                    logger.debug(f"✅ Using Supabase openai_prompt: {len(openai_prompt)} chars")
                    if not openai_prompt:
                        logger.warning("⚠️ No openai_prompt found in Supabase config")
                else:
                    logger.warning("⚠️ No data_registry available for prompt retrieval")
            except Exception as e:
                logger.warning(f"⚠️ Failed to get openai_prompt from config: {e}")

            # Transcribe with provider (pass openai_prompt exactly like legacy server)
            logger.debug(f"🚀 Calling provider.transcribe with openai_prompt")
            result = await provider.transcribe(
                audio_data=audio_buffer,
                language="nl",  # Dutch
                prompt=None,  # Don't override with generic prompt
                openai_prompt=openai_prompt,  # Pass Supabase prompt as kwarg
                format="wav"
            )

            if not result or not result.text:
                logger.warning(f"Empty transcription result for client {client_id}")
                return

            logger.info(f"Transcription completed for {client_id}: '{result.text[:100]}...'")

            # Apply normalization (consistent with file upload endpoint)
            raw_text = result.text
            normalized_text = raw_text  # Default fallback

            if self.normalization_pipeline:
                try:
                    norm_result = self.normalization_pipeline.normalize(result.text, language="nl")
                    normalized_text = norm_result.normalized_text
                    logger.debug(f"Normalized: '{result.text}' -> '{normalized_text}'")
                except Exception as e:
                    logger.warning(f"Normalization failed: {e}")

            # Send transcription result via WebSocket (both raw and normalized)
            transcription_message = {
                "type": "transcription_result",
                "text": normalized_text,  # Main text field (normalized)
                "raw": raw_text,  # Raw OpenAI transcription
                "normalized": normalized_text,  # Explicit normalized field
                "language": result.language or "nl",
                "duration": getattr(result, 'duration', 0),
                "confidence": getattr(result, 'confidence', 1.0),
                "timestamp": time.time()
            }

            import json
            await websocket_manager.send_personal_message(
                json.dumps(transcription_message),
                client_id
            )

            logger.info(f"Sent transcription result to client {client_id}")

        except asyncio.CancelledError:
            logger.info(f"Transcription cancelled for client {client_id}")
        except Exception as e:
            logger.error(f"Transcription error for client {client_id}: {e}")
            await self._send_error(client_id, f"Transcription failed: {str(e)}", websocket_manager)

    async def _send_error(self, client_id: str, error_message: str, websocket_manager):
        """Send error message to client"""
        try:
            import json
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

    async def cleanup_client(self, client_id: str, websocket_manager=None):
        """Clean up resources for disconnected client (with final flush like old server)"""
        try:
            # Process any remaining pending audio before cleanup (like old server)
            if client_id in self.client_buffers:
                buffer = self.client_buffers[client_id]
                final_audio = buffer.force_flush()

                if final_audio and websocket_manager:
                    logger.info(f"Processing final audio chunk for {client_id} before cleanup")
                    # Process final chunk
                    task = asyncio.create_task(
                        self._transcribe_audio_data(client_id, final_audio, websocket_manager)
                    )
                    # Give it a moment to process
                    try:
                        await asyncio.wait_for(task, timeout=2.0)
                    except asyncio.TimeoutError:
                        logger.warning(f"Final transcription timeout for {client_id}")
                        task.cancel()

            # Cancel transcription task
            if client_id in self.transcription_tasks:
                if not self.transcription_tasks[client_id].done():
                    self.transcription_tasks[client_id].cancel()
                del self.transcription_tasks[client_id]

            # Remove audio buffer
            if client_id in self.client_buffers:
                stats = self.client_buffers[client_id].get_stats()
                logger.info(f"Final buffer stats for {client_id}: {stats}")
                del self.client_buffers[client_id]

            logger.info(f"Cleaned up streaming resources for client {client_id}")

        except Exception as e:
            logger.error(f"Error during cleanup for {client_id}: {e}")

    async def force_flush_client(self, client_id: str, websocket_manager):
        """Manually flush any pending audio for a client (like old server 'flush_audio' command)"""
        try:
            if client_id not in self.client_buffers:
                logger.warning(f"No buffer found for client {client_id} to flush")
                return False

            buffer = self.client_buffers[client_id]
            pending_audio = buffer.force_flush()

            if pending_audio:
                logger.info(f"Manual flush: Processing {len(pending_audio)} bytes for {client_id}")
                task = asyncio.create_task(
                    self._transcribe_audio_data(client_id, pending_audio, websocket_manager)
                )
                self.transcription_tasks[client_id] = task
                return True
            else:
                logger.info(f"Manual flush: No pending audio for {client_id}")
                return False

        except Exception as e:
            logger.error(f"Error during manual flush for {client_id}: {e}")
            return False