"""
AI provider interfaces for the unified server.
Defines abstract base classes for ASR and LLM providers.
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, AsyncIterator, Union
from dataclasses import dataclass
from enum import Enum
import io


class ProviderType(Enum):
    """Types of AI providers."""
    ASR = "asr"  # Automatic Speech Recognition
    LLM = "llm"  # Large Language Model


class ProviderStatus(Enum):
    """Provider status states."""
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


@dataclass
class TranscriptionSegment:
    """Unified segment format for transcription results."""
    text: str
    start: float = 0.0
    end: float = 0.0
    id: int = 0
    seek: int = 0
    tokens: Optional[List[int]] = None
    temperature: float = 0.0
    avg_logprob: float = 0.0
    compression_ratio: float = 0.0
    no_speech_prob: float = 0.0
    words: Optional[List[Dict[str, Any]]] = None


@dataclass
class TranscriptionResult:
    """Result of transcription operation."""
    segments: List[TranscriptionSegment]
    text: str
    language: Optional[str] = None
    duration: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ProviderCapabilities:
    """Capabilities supported by a provider."""
    supports_streaming: bool = False
    supports_batch: bool = False
    supported_languages: List[str] = None
    supported_formats: List[str] = None
    max_audio_length: Optional[int] = None  # seconds
    max_file_size: Optional[int] = None  # bytes
    
    def __post_init__(self):
        if self.supported_languages is None:
            self.supported_languages = []
        if self.supported_formats is None:
            self.supported_formats = []


@dataclass
class ProviderInfo:
    """Provider information and status."""
    name: str
    provider_type: ProviderType
    status: ProviderStatus
    version: Optional[str] = None
    model_name: Optional[str] = None
    capabilities: Optional[ProviderCapabilities] = None
    error_message: Optional[str] = None
    last_updated: Optional[str] = None


class ASRProvider(ABC):
    """Abstract base class for Automatic Speech Recognition providers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._status = ProviderStatus.INITIALIZING
        self._error_message = None
        
    @property
    def status(self) -> ProviderStatus:
        """Current provider status."""
        return self._status
        
    @property
    def error_message(self) -> Optional[str]:
        """Last error message if any."""
        return self._error_message
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the provider.
        Returns True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def transcribe(
        self,
        audio_data: Union[bytes, io.BytesIO],
        language: Optional[str] = None,
        prompt: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        """
        Transcribe audio data.
        
        Args:
            audio_data: Audio data as bytes or BytesIO
            language: Language code (e.g., 'nl', 'en')
            prompt: Context prompt for better accuracy
            **kwargs: Provider-specific options
            
        Returns:
            TranscriptionResult with segments and metadata
        """
        pass
    
    @abstractmethod
    async def stream_transcribe(
        self,
        audio_stream: AsyncIterator[bytes],
        language: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[TranscriptionResult]:
        """
        Stream transcription for real-time processing.
        
        Args:
            audio_stream: Async iterator of audio chunks
            language: Language code
            **kwargs: Provider-specific options
            
        Yields:
            TranscriptionResult objects as they become available
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        """Get provider capabilities."""
        pass
    
    @abstractmethod
    def get_info(self) -> ProviderInfo:
        """Get provider information and status."""
        pass
    
    async def cleanup(self) -> None:
        """Clean up resources. Override if needed."""
        pass


class LLMProvider(ABC):
    """Abstract base class for Large Language Model providers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._status = ProviderStatus.INITIALIZING
        self._error_message = None
        
    @property
    def status(self) -> ProviderStatus:
        """Current provider status."""
        return self._status
        
    @property
    def error_message(self) -> Optional[str]:
        """Last error message if any."""
        return self._error_message
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the provider."""
        pass
    
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate completion for a prompt.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Provider-specific options
            
        Returns:
            Generated text
        """
        pass
    
    @abstractmethod
    async def stream_complete(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream completion for real-time generation.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Provider-specific options
            
        Yields:
            Text chunks as they become available
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        """Get provider capabilities."""
        pass
    
    @abstractmethod
    def get_info(self) -> ProviderInfo:
        """Get provider information and status."""
        pass
    
    async def cleanup(self) -> None:
        """Clean up resources. Override if needed."""
        pass


class ProviderError(Exception):
    """Base exception for provider errors."""
    
    def __init__(self, message: str, provider_name: str = None, error_code: str = None):
        super().__init__(message)
        self.provider_name = provider_name
        self.error_code = error_code


class ProviderInitializationError(ProviderError):
    """Raised when provider initialization fails."""
    pass


class ProviderUnavailableError(ProviderError):
    """Raised when provider is temporarily unavailable."""
    pass


class TranscriptionError(ProviderError):
    """Raised when transcription fails."""
    pass


class LLMError(ProviderError):
    """Raised when LLM operation fails."""
    pass