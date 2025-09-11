"""
AI provider module for the unified server.
Provides ASR and LLM capabilities with pluggable provider architecture.
"""

from .interfaces import (
    ASRProvider, LLMProvider, TranscriptionResult, TranscriptionSegment,
    ProviderCapabilities, ProviderInfo, ProviderType, ProviderStatus,
    ProviderError, ProviderInitializationError, TranscriptionError
)
from .factory import provider_factory, ProviderFactory
from .config import config_manager, ProviderConfig
from .routes import router as ai_router

__all__ = [
    'ASRProvider', 'LLMProvider', 'TranscriptionResult', 'TranscriptionSegment',
    'ProviderCapabilities', 'ProviderInfo', 'ProviderType', 'ProviderStatus',
    'ProviderError', 'ProviderInitializationError', 'TranscriptionError',
    'provider_factory', 'ProviderFactory',
    'config_manager', 'ProviderConfig',
    'ai_router'
]