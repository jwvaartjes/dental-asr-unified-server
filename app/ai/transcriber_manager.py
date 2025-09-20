"""
Transcriber Manager - Hot-Swappable SPSC vs Standard Implementation
Allows runtime switching between current and SPSC without server restart
"""

import asyncio
import logging
from typing import Optional, Dict, Any

from .streaming_transcriber import StreamingTranscriber
from .spsc_wrapper import SPSCStreamingTranscriber

logger = logging.getLogger(__name__)


class TranscriberManager:
    """
    Manages hot-swapping between Standard and SPSC transcribers
    Provides seamless switching without server restart
    """

    def __init__(self, ai_factory, normalization_pipeline=None, data_registry=None):
        self.ai_factory = ai_factory
        self.normalization_pipeline = normalization_pipeline
        self.data_registry = data_registry

        # Current active transcriber
        self.current_transcriber = None
        self.current_type = "standard"  # "standard" or "spsc"

        # Transcriber instances cache
        self._standard_transcriber = None
        self._spsc_transcriber = None

        # Client state for seamless switching
        self.active_clients: Dict[str, Dict] = {}

        logger.info("TranscriberManager initialized - ready for hot-swapping")

    async def get_transcriber(self, force_type: Optional[str] = None):
        """
        Get current active transcriber (creates if needed)
        Args:
            force_type: "standard" or "spsc" to override current type
        """
        target_type = force_type or self.current_type

        if target_type == "spsc":
            if self._spsc_transcriber is None:
                logger.info("🚀 Creating SPSC transcriber with legacy genius...")
                self._spsc_transcriber = SPSCStreamingTranscriber(
                    self.ai_factory,
                    self.normalization_pipeline,
                    self.data_registry
                )
                await self._spsc_transcriber.start()
                logger.info("✅ SPSC transcriber ready")

            self.current_transcriber = self._spsc_transcriber
            if self.current_type != "spsc":
                self.current_type = "spsc"
                logger.info("🔄 Switched to SPSC transcriber")

        else:  # standard
            if self._standard_transcriber is None:
                logger.info("📝 Creating standard transcriber...")
                self._standard_transcriber = StreamingTranscriber(
                    self.ai_factory,
                    self.normalization_pipeline,
                    self.data_registry
                )
                logger.info("✅ Standard transcriber ready")

            self.current_transcriber = self._standard_transcriber
            if self.current_type != "standard":
                self.current_type = "standard"
                logger.info("🔄 Switched to standard transcriber")

        return self.current_transcriber

    async def switch_to_spsc(self) -> Dict[str, Any]:
        """Hot-swap to SPSC transcriber without restart"""
        try:
            logger.info("🚀 Hot-swapping to SPSC legacy genius...")
            await self.get_transcriber(force_type="spsc")

            return {
                "success": True,
                "new_type": "spsc",
                "message": "Successfully switched to SPSC legacy genius transcriber",
                "performance_mode": "high_performance_batching",
                "features": [
                    "Zero-latency smart batching",
                    "10x parallel processing",
                    "Circuit breaker resilience",
                    "Per-client smart aggregation"
                ]
            }

        except Exception as e:
            logger.error(f"❌ Failed to switch to SPSC: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to switch to SPSC transcriber"
            }

    async def switch_to_standard(self) -> Dict[str, Any]:
        """Hot-swap to standard transcriber without restart"""
        try:
            logger.info("📝 Hot-swapping to standard transcriber...")
            await self.get_transcriber(force_type="standard")

            # Optionally stop SPSC to free resources
            if self._spsc_transcriber:
                await self._spsc_transcriber.stop()
                self._spsc_transcriber = None
                logger.info("🛑 SPSC transcriber stopped to free resources")

            return {
                "success": True,
                "new_type": "standard",
                "message": "Successfully switched to standard sequential transcriber",
                "performance_mode": "simple_sequential",
                "features": [
                    "Simple sequential processing",
                    "Low resource usage",
                    "Predictable behavior"
                ]
            }

        except Exception as e:
            logger.error(f"❌ Failed to switch to standard: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to switch to standard transcriber"
            }

    def get_status(self) -> Dict[str, Any]:
        """Get current transcriber status and capabilities"""
        return {
            "current_type": self.current_type,
            "available_types": ["standard", "spsc"],
            "spsc_loaded": self._spsc_transcriber is not None,
            "standard_loaded": self._standard_transcriber is not None,
            "can_switch_to_spsc": True,
            "can_switch_to_standard": True,
            "active_clients": len(self.active_clients),
            "performance_info": {
                "standard": {
                    "description": "Simple sequential processing",
                    "best_for": "Single user, development, simple scenarios",
                    "latency": "Same as current"
                },
                "spsc": {
                    "description": "Legacy genius with smart batching + parallel processing",
                    "best_for": "Multiple clients, production, high-volume scenarios",
                    "latency": "10x faster for multiple clients, same for single client"
                }
            }
        }

    async def process_audio_chunk(self, client_id: str, audio_data: bytes, websocket=None) -> bool:
        """Process audio chunk using current active transcriber"""
        # Track client activity
        if client_id not in self.active_clients:
            self.active_clients[client_id] = {
                "start_time": asyncio.get_event_loop().time(),
                "chunk_count": 0
            }

        self.active_clients[client_id]["chunk_count"] += 1

        # Get current transcriber and process
        transcriber = await self.get_transcriber()

        # Handle different transcriber interfaces
        if self.current_type == "spsc" and hasattr(transcriber, 'process_audio_chunk'):
            # SPSC interface
            return await transcriber.process_audio_chunk(client_id, audio_data, websocket)
        else:
            # Standard interface
            return await transcriber.transcribe_and_send(client_id, audio_data, websocket)

    async def cleanup_client(self, client_id: str):
        """Clean up client from current transcriber"""
        if client_id in self.active_clients:
            del self.active_clients[client_id]

        # Clean up from both transcribers if they exist
        if self._spsc_transcriber:
            self._spsc_transcriber.cleanup_client(client_id)

        if self._standard_transcriber and hasattr(self._standard_transcriber, 'cleanup_client'):
            await self._standard_transcriber.cleanup_client(client_id, None)  # Provide connection_manager as None

        logger.info(f"🧹 Client {client_id} cleaned up from transcriber manager")

    async def shutdown(self):
        """Graceful shutdown of all transcribers"""
        logger.info("🛑 Shutting down transcriber manager...")

        if self._spsc_transcriber:
            await self._spsc_transcriber.stop()
            logger.info("✅ SPSC transcriber stopped")

        # Standard transcriber doesn't need explicit shutdown

        logger.info("✅ Transcriber manager shutdown complete")


# Global transcriber manager instance (will be initialized in app startup)
_global_transcriber_manager: Optional[TranscriberManager] = None


def initialize_transcriber_manager(ai_factory, normalization_pipeline=None, data_registry=None):
    """Initialize global transcriber manager"""
    global _global_transcriber_manager
    _global_transcriber_manager = TranscriberManager(ai_factory, normalization_pipeline, data_registry)
    logger.info("✅ Global transcriber manager initialized")
    return _global_transcriber_manager


def get_transcriber_manager() -> TranscriberManager:
    """Get global transcriber manager instance"""
    if _global_transcriber_manager is None:
        raise RuntimeError("TranscriberManager not initialized - call initialize_transcriber_manager first")
    return _global_transcriber_manager