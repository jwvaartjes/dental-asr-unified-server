"""
OpenAI Realtime API provider for streaming transcription.
Provides persistent WebSocket connection to OpenAI's Realtime API for continuous audio processing.
"""

import asyncio
import json
import logging
import os
import time
from typing import Optional, Dict, Any, Callable, Awaitable
import websockets
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosed, WebSocketException

from ..interfaces import ASRProvider, TranscriptionResult, TranscriptionSegment, ProviderStatus
from ..interfaces import TranscriptionError, ProviderUnavailableError

logger = logging.getLogger(__name__)


class OpenAIRealtimeProvider(ASRProvider):
    """OpenAI Realtime API provider for streaming transcription."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-realtime-preview-2024-12-17"):
        """
        Initialize OpenAI Realtime provider.

        Args:
            api_key: OpenAI API key (if None, will use OPENAI_API_KEY env var)
            model: Realtime model to use
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self._status = ProviderStatus.NOT_INITIALIZED
        self._error_message: Optional[str] = None

        # WebSocket connection
        self._websocket: Optional[WebSocketClientProtocol] = None
        self._connection_lock = asyncio.Lock()
        self._session_id: Optional[str] = None

        # Event handlers
        self._transcription_handler: Optional[Callable[[str], Awaitable[None]]] = None
        self._error_handler: Optional[Callable[[str], Awaitable[None]]] = None
        self._completion_handler: Optional[Callable[[], Awaitable[None]]] = None

        # Transcription accumulation for WAV processing
        self._accumulated_text = ""

        # Configuration - letterlijke, smalle prompt (geen rol, geen domein-druk)
        self.instructions = "Transcribeer wat je hoort."

    async def initialize(self) -> bool:
        """Initialize the Realtime provider."""
        if not self.api_key:
            self._status = ProviderStatus.ERROR
            self._error_message = "OpenAI API key not provided"
            return False

        try:
            # Test connection by creating a temporary session
            test_ws = await self._create_websocket_connection()
            await test_ws.close()

            self._status = ProviderStatus.READY
            self._error_message = None
            logger.info(f"✅ OpenAI Realtime provider initialized (model: {self.model})")
            return True

        except Exception as e:
            self._status = ProviderStatus.ERROR
            self._error_message = f"Failed to initialize: {str(e)}"
            logger.error(f"❌ OpenAI Realtime provider initialization failed: {e}")
            return False

    async def _create_websocket_connection(self) -> WebSocketClientProtocol:
        """Create WebSocket connection to OpenAI Realtime API."""
        url = f"wss://api.openai.com/v1/realtime?model={self.model}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1"
        }

        # Convert headers to list format expected by websockets
        header_list = [(key, value) for key, value in headers.items()]

        try:
            websocket = await websockets.connect(url, additional_headers=header_list)
            logger.debug(f"🔗 Connected to OpenAI Realtime API: {url}")
            return websocket
        except Exception as e:
            logger.error(f"❌ Failed to connect to OpenAI Realtime API: {e}")
            raise

    async def start_session(self,
                           transcription_handler: Callable[[str], Awaitable[None]],
                           error_handler: Optional[Callable[[str], Awaitable[None]]] = None,
                           completion_handler: Optional[Callable[[], Awaitable[None]]] = None) -> bool:
        """
        Start a new Realtime session.

        Args:
            transcription_handler: Callback for transcription results
            error_handler: Callback for errors

        Returns:
            bool: True if session started successfully
        """
        async with self._connection_lock:
            if self._websocket:
                logger.warning("Session already active, closing previous session")
                await self.stop_session()

            try:
                # Create new WebSocket connection
                self._websocket = await self._create_websocket_connection()
                self._transcription_handler = transcription_handler
                self._error_handler = error_handler
                self._completion_handler = completion_handler

                # Reset accumulation
                self._accumulated_text = ""

                # Send session configuration
                await self._send_session_update()

                # Start listening for events
                asyncio.create_task(self._event_listener())

                logger.info("🚀 OpenAI Realtime session started")
                return True

            except Exception as e:
                logger.error(f"❌ Failed to start Realtime session: {e}")
                if self._error_handler:
                    await self._error_handler(f"Failed to start session: {str(e)}")
                return False

    async def stop_session(self) -> None:
        """Stop the current Realtime session."""
        async with self._connection_lock:
            if self._websocket:
                try:
                    await self._websocket.close()
                    logger.info("🛑 OpenAI Realtime session stopped")
                except Exception as e:
                    logger.warning(f"Error closing WebSocket: {e}")
                finally:
                    self._websocket = None
                    self._session_id = None
                    self._transcription_handler = None
                    self._error_handler = None
                    self._completion_handler = None
                    self._accumulated_text = ""

    async def _send_session_update(self) -> None:
        """Send session configuration to OpenAI."""
        if not self._websocket:
            return

        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text"],
                "instructions": self.instructions,
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "gpt-4o-transcribe",
                    "language": "nl"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.999,          # praktisch nooit 'voice'
                    "silence_duration_ms": 1500,  # Max 10000ms allowed, gebruik 1500ms
                    "prefix_padding_ms": 0
                },
                "tools": [],
                "tool_choice": "none",
                "temperature": 0.6
            }
        }

        await self._send_event(session_config)

    async def _send_event(self, event: Dict[str, Any]) -> None:
        """Send event to OpenAI Realtime API."""
        if not self._websocket:
            raise RuntimeError("WebSocket not connected")

        try:
            await self._websocket.send(json.dumps(event))
        except Exception as e:
            logger.error(f"❌ Failed to send event: {e}")
            raise

    async def _event_listener(self) -> None:
        """Listen for events from OpenAI Realtime API."""
        if not self._websocket:
            return

        try:
            async for message in self._websocket:
                try:
                    event = json.loads(message)
                    await self._handle_event(event)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {message}")
                except Exception as e:
                    logger.error(f"Error handling event: {e}")

        except ConnectionClosed:
            logger.info("🔌 OpenAI Realtime connection closed")
        except Exception as e:
            logger.error(f"❌ Event listener error: {e}")
            if self._error_handler:
                await self._error_handler(f"Connection error: {str(e)}")

    async def _handle_event(self, event: Dict[str, Any]) -> None:
        """Handle events from OpenAI Realtime API."""
        event_type = event.get("type")

        if event_type == "session.created":
            self._session_id = event.get("session", {}).get("id")
            logger.info(f"✅ Realtime session created: {self._session_id}")

        elif event_type == "conversation.item.input_audio_transcription.completed":
            # This is the real transcription event for STT-only
            # Extract transcript from different possible locations
            transcript = event.get("transcript")

            if not transcript:
                # Try nested under 'item'
                item = event.get("item") or {}
                for content in item.get("content", []):
                    if "transcript" in content:
                        transcript = content["transcript"]
                        break

            logger.info(f"✅ Audio transcription completed: '{transcript or 'NO_TRANSCRIPT'}'")

            if transcript and self._transcription_handler:
                await self._transcription_handler(transcript)

            if self._completion_handler:
                await self._completion_handler()

        elif event_type == "conversation.item.input_audio_transcription.failed":
            # Transcription failed
            error_msg = event.get("error", {}).get("message", "Transcription failed")
            logger.error(f"❌ Audio transcription failed: {error_msg}")
            if self._error_handler:
                await self._error_handler(error_msg)

        elif event_type == "input_audio_buffer.committed":
            # Buffer was committed successfully
            logger.debug("📤 Audio buffer committed successfully")

        elif event_type == "response.text.delta":
            # Ignore assistant response deltas (we don't want chatbot responses)
            logger.debug("🤖 Ignoring assistant response delta (STT-only mode)")

        elif event_type == "response.text.done":
            # Ignore assistant response completion (we don't want chatbot responses)
            logger.debug("🤖 Ignoring assistant response completion (STT-only mode)")

        elif event_type == "response.done":
            # Ignore assistant response done (we don't want chatbot responses)
            logger.debug("🤖 Ignoring assistant response done (STT-only mode)")

        elif event_type == "input_audio_buffer.speech_started":
            logger.debug("🎤 Speech started")

        elif event_type == "input_audio_buffer.speech_stopped":
            logger.debug("🤐 Speech stopped")

        elif event_type == "error":
            error_msg = event.get("error", {}).get("message", "Unknown error")
            logger.error(f"❌ OpenAI Realtime error: {error_msg}")
            if self._error_handler:
                await self._error_handler(error_msg)

        else:
            logger.debug(f"📨 Unhandled event type: {event_type}")

    async def append_audio(self, audio_data: bytes) -> None:
        """
        Append audio data to the input buffer.

        Args:
            audio_data: PCM16LE mono 16kHz audio bytes
        """
        if not self._websocket:
            raise RuntimeError("Session not started")

        # Convert to base64
        import base64
        audio_base64 = base64.b64encode(audio_data).decode("ascii")

        # Send append event
        event = {
            "type": "input_audio_buffer.append",
            "audio": audio_base64
        }

        await self._send_event(event)

    async def commit_audio(self) -> None:
        """Commit the current audio buffer and request transcription."""
        if not self._websocket:
            raise RuntimeError("Session not started")

        # Commit the buffer - this will trigger transcription events
        await self._send_event({"type": "input_audio_buffer.commit"})

        # NO response.create for STT-only!
        # We listen for conversation.item.input_audio_transcription.completed instead

    async def clear_audio_buffer(self) -> None:
        """Clear the input audio buffer."""
        if not self._websocket:
            raise RuntimeError("Session not started")

        await self._send_event({"type": "input_audio_buffer.clear"})

    # ASRProvider interface methods (legacy compatibility)
    async def transcribe(self, audio_data, language="nl", prompt=None, **kwargs) -> TranscriptionResult:
        """Legacy transcribe method for compatibility."""
        raise NotImplementedError("Use Realtime session methods instead")

    async def stream_transcribe(self, audio_stream, language="nl", prompt=None, **kwargs):
        """Legacy stream transcribe method for compatibility."""
        raise NotImplementedError("Use Realtime session methods instead")

    def get_capabilities(self) -> Dict[str, Any]:
        """Get provider capabilities."""
        return {
            "supports_streaming": True,
            "supports_batch": False,
            "supported_languages": ["nl", "en", "de", "fr", "es", "it", "pt", "ru", "zh", "ja", "ko"],
            "supported_formats": ["pcm16"],
            "max_audio_length": None,  # No limit for streaming
            "max_file_size": None,     # No file size limit
            "realtime": True
        }

    def get_info(self) -> Dict[str, Any]:
        """Get provider information."""
        return {
            "name": "OpenAI Realtime",
            "provider_type": "realtime_asr",
            "status": self._status.value,
            "version": "1.0.0",
            "model_name": self.model,
            "capabilities": self.get_capabilities(),
            "error_message": self._error_message,
            "session_active": self._websocket is not None,
            "session_id": self._session_id
        }

    async def cleanup(self) -> None:
        """Clean up provider resources."""
        await self.stop_session()
        logger.info("🧹 OpenAI Realtime provider cleaned up")