"""
SPSC Wrapper - Easy integration for testing legacy SPSC performance
Provides same interface as StreamingTranscriber but with SPSC genius underneath
"""

import asyncio
import logging
import time
from typing import Dict, Optional

from .spsc_transcriber import SPSCAudioProcessor, AudioChunk, ChunkType

logger = logging.getLogger(__name__)


class SPSCStreamingTranscriber:
    """
    Wrapper around SPSCAudioProcessor to provide StreamingTranscriber-compatible interface
    Enables easy A/B testing between current and SPSC implementation
    """

    def __init__(self, ai_factory, normalization_pipeline=None, data_registry=None):
        self.ai_factory = ai_factory
        self.normalization_pipeline = normalization_pipeline
        self.data_registry = data_registry

        # Initialize SPSC processor with all legacy genius
        self.spsc_processor = SPSCAudioProcessor(
            ai_factory=ai_factory,
            normalization_pipeline=normalization_pipeline,
            data_registry=data_registry
        )

        # Track active clients
        self.active_clients: Dict[str, Dict] = {}

        logger.info("SPSCStreamingTranscriber initialized with legacy SPSC genius")

    async def start(self):
        """Start the SPSC processing system"""
        await self.spsc_processor.start()
        logger.info("SPSC: Streaming transcriber started")

    async def stop(self):
        """Stop the SPSC processing system"""
        await self.spsc_processor.stop()
        logger.info("SPSC: Streaming transcriber stopped")

    async def process_audio_chunk(self, client_id: str, audio_data: bytes, websocket=None) -> bool:
        """
        Process audio chunk using SPSC genius architecture
        Compatible interface with StreamingTranscriber
        """
        try:
            # Create AudioChunk for SPSC processing
            chunk = AudioChunk(
                client_id=client_id,
                audio_data=audio_data,
                chunk_id=f"chunk_{int(time.time() * 1000)}_{client_id}",
                timestamp=time.time(),
                chunk_type=ChunkType.BUFFERED,  # Default priority
                websocket=websocket
            )

            # Track client
            if client_id not in self.active_clients:
                self.active_clients[client_id] = {
                    'start_time': time.time(),
                    'chunk_count': 0
                }

            self.active_clients[client_id]['chunk_count'] += 1

            # Produce to SPSC queue (with genius backpressure control)
            success = await self.spsc_processor.produce(chunk)

            if not success:
                logger.warning(f"SPSC: Audio chunk dropped for {client_id} due to backpressure")

            return success

        except Exception as e:
            logger.error(f"SPSC: Failed to process audio chunk for {client_id}: {e}")
            return False

    async def process_realtime_chunk(self, client_id: str, audio_data: bytes, websocket=None) -> bool:
        """
        Process high-priority realtime chunk (skips batching for low latency)
        """
        try:
            # Create high-priority chunk
            chunk = AudioChunk(
                client_id=client_id,
                audio_data=audio_data,
                chunk_id=f"realtime_{int(time.time() * 1000)}_{client_id}",
                timestamp=time.time(),
                chunk_type=ChunkType.REALTIME,  # Highest priority
                websocket=websocket
            )

            # Produce with high priority
            return await self.spsc_processor.produce(chunk)

        except Exception as e:
            logger.error(f"SPSC: Failed to process realtime chunk for {client_id}: {e}")
            return False

    async def finalize_session(self, client_id: str, websocket=None):
        """Finalize transcription session for client"""
        try:
            # Create final chunk to trigger aggregator completion
            final_chunk = AudioChunk(
                client_id=client_id,
                audio_data=b'',  # Empty audio
                chunk_id=f"final_{int(time.time() * 1000)}_{client_id}",
                timestamp=time.time(),
                chunk_type=ChunkType.REALTIME,  # High priority for final
                websocket=websocket
            )

            await self.spsc_processor.produce(final_chunk)
            logger.info(f"SPSC: Session finalized for {client_id}")

        except Exception as e:
            logger.error(f"SPSC: Failed to finalize session for {client_id}: {e}")

    def cleanup_client(self, client_id: str):
        """Clean up client resources"""
        # Clean up from SPSC processor
        self.spsc_processor.cleanup_client(client_id)

        # Remove from active tracking
        if client_id in self.active_clients:
            del self.active_clients[client_id]

        logger.info(f"SPSC: Client {client_id} cleaned up")

    def get_performance_metrics(self) -> Dict:
        """Get comprehensive performance metrics"""
        spsc_metrics = self.spsc_processor.get_metrics()

        return {
            "spsc_metrics": spsc_metrics,
            "active_clients": len(self.active_clients),
            "client_details": self.active_clients,
            "performance_summary": {
                "chunks_processed": spsc_metrics['chunks_processed'],
                "batches_processed": spsc_metrics['batches_processed'],
                "avg_processing_time_ms": spsc_metrics['avg_processing_time'] * 1000,
                "queue_utilization": spsc_metrics['queue_size'] / spsc_metrics['max_queue_size'] * 100,
                "drop_rate": spsc_metrics['chunks_dropped'] / max(1, spsc_metrics['chunks_processed']) * 100
            }
        }

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()


# Factory function for easy integration
async def create_spsc_transcriber(ai_factory, normalization_pipeline=None, data_registry=None) -> SPSCStreamingTranscriber:
    """Create and start SPSC streaming transcriber"""
    transcriber = SPSCStreamingTranscriber(ai_factory, normalization_pipeline, data_registry)
    await transcriber.start()
    return transcriber