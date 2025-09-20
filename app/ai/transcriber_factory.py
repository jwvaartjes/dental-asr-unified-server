"""
Transcriber Factory - A/B Testing Between Current and SPSC Implementation
Allows safe testing of legacy SPSC genius performance optimizations
"""

import logging
import os
from typing import Optional

from .streaming_transcriber import StreamingTranscriber
from .spsc_wrapper import SPSCStreamingTranscriber

logger = logging.getLogger(__name__)


class TranscriberFactory:
    """Factory for creating the appropriate transcriber based on configuration"""

    @staticmethod
    async def create_transcriber(ai_factory, normalization_pipeline=None, data_registry=None, use_spsc: Optional[bool] = None):
        """
        Create transcriber based on configuration

        Args:
            ai_factory: AI factory for transcription
            normalization_pipeline: Text normalization pipeline
            data_registry: Data registry for prompts
            use_spsc: Override for SPSC usage (None = use environment)

        Returns:
            StreamingTranscriber or SPSCStreamingTranscriber
        """

        # Determine which implementation to use
        if use_spsc is None:
            # Check environment variable for A/B testing
            use_spsc = os.getenv('USE_SPSC_TRANSCRIBER', 'false').lower() in ('true', '1', 'yes')

        if use_spsc:
            logger.info("🚀 Creating SPSC Transcriber with legacy genius optimizations")
            transcriber = SPSCStreamingTranscriber(ai_factory, normalization_pipeline, data_registry)
            await transcriber.start()
            return transcriber
        else:
            logger.info("📝 Creating standard StreamingTranscriber (current implementation)")
            return StreamingTranscriber(ai_factory, normalization_pipeline, data_registry)

    @staticmethod
    def get_transcriber_type() -> str:
        """Get current transcriber type from environment"""
        use_spsc = os.getenv('USE_SPSC_TRANSCRIBER', 'false').lower() in ('true', '1', 'yes')
        return "SPSC_LEGACY_GENIUS" if use_spsc else "STANDARD_SEQUENTIAL"

    @staticmethod
    async def create_performance_comparison(ai_factory, normalization_pipeline=None, data_registry=None):
        """
        Create both transcribers for performance comparison testing
        """
        standard = StreamingTranscriber(ai_factory, normalization_pipeline, data_registry)

        spsc = SPSCStreamingTranscriber(ai_factory, normalization_pipeline, data_registry)
        await spsc.start()

        return {
            "standard": standard,
            "spsc": spsc,
            "comparison_mode": True
        }


# Convenience functions for easy integration
async def create_smart_transcriber(ai_factory, normalization_pipeline=None, data_registry=None):
    """Create the best available transcriber (SPSC if enabled, otherwise standard)"""
    return await TranscriberFactory.create_transcriber(ai_factory, normalization_pipeline, data_registry)


async def create_spsc_transcriber(ai_factory, normalization_pipeline=None, data_registry=None):
    """Force create SPSC transcriber for testing"""
    return await TranscriberFactory.create_transcriber(ai_factory, normalization_pipeline, data_registry, use_spsc=True)


async def create_standard_transcriber(ai_factory, normalization_pipeline=None, data_registry=None):
    """Force create standard transcriber for comparison"""
    return await TranscriberFactory.create_transcriber(ai_factory, normalization_pipeline, data_registry, use_spsc=False)