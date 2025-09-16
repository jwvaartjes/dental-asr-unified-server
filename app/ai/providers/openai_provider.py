"""
OpenAI ASR provider implementation.
Supports OpenAI's gpt-4o-transcribe model with dental terminology prompts.
"""
import os
import io
import logging
from typing import Optional, Dict, Any, List, Union, AsyncIterator
from datetime import datetime

from ..interfaces import (
    ASRProvider, TranscriptionResult, TranscriptionSegment, 
    ProviderCapabilities, ProviderInfo, ProviderType, ProviderStatus,
    ProviderInitializationError, TranscriptionError, ProviderUnavailableError
)

logger = logging.getLogger(__name__)


class OpenAIASRProvider(ASRProvider):
    """OpenAI ASR provider using gpt-4o-transcribe model."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = None
        self.model_name = config.get('model', 'gpt-4o-transcribe')
        self.api_key = config.get('api_key') or os.getenv('OPENAI_API_KEY')
        
        # Default fallback prompt (matches legacy server fallback)
        self.fallback_prompt = "Dit is een tandheelkundige opname met Nederlandse termen."
        
    async def initialize(self) -> bool:
        """Initialize OpenAI client."""
        try:
            if not self.api_key:
                raise ProviderInitializationError(
                    "OpenAI API key not found in config or environment",
                    provider_name="openai"
                )
            
            # Import OpenAI here to avoid import errors if not installed
            try:
                import openai
                self.client = openai.AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ProviderInitializationError(
                    "OpenAI package not installed. Run: pip install openai",
                    provider_name="openai"
                )
            
            # Test API connectivity with a minimal request
            try:
                await self._test_connection()
                self._status = ProviderStatus.READY
                logger.info("OpenAI ASR provider initialized successfully")
                return True
                
            except Exception as e:
                self._status = ProviderStatus.ERROR
                self._error_message = f"OpenAI API test failed: {str(e)}"
                logger.error(f"OpenAI initialization failed: {e}")
                return False
                
        except Exception as e:
            self._status = ProviderStatus.ERROR
            self._error_message = str(e)
            logger.error(f"OpenAI provider initialization error: {e}")
            return False
    
    async def _test_connection(self):
        """Test OpenAI API connectivity."""
        try:
            # Create a minimal audio buffer for testing (silence)
            test_audio = b'\x00' * 1024  # 1KB of silence
            test_buffer = io.BytesIO(test_audio)
            test_buffer.name = "test.wav"
            
            # This will fail but should give us API connectivity info
            try:
                await self.client.audio.transcriptions.create(
                    model="whisper-1",  # Use smaller model for test
                    file=test_buffer,
                    response_format="text"
                )
            except Exception as e:
                # Expected to fail with invalid audio, but should not be auth error
                error_str = str(e).lower()
                if "authentication" in error_str or "api key" in error_str:
                    raise ProviderInitializationError(
                        "OpenAI API authentication failed. Check API key.",
                        provider_name="openai"
                    )
                elif "rate limit" in error_str:
                    raise ProviderUnavailableError(
                        "OpenAI API rate limit exceeded",
                        provider_name="openai"  
                    )
                # Other errors are expected for invalid test audio
                logger.debug(f"OpenAI test connection completed (expected error): {e}")
                
        except (ProviderInitializationError, ProviderUnavailableError):
            raise
        except Exception as e:
            logger.warning(f"OpenAI connection test inconclusive: {e}")
            # Don't fail initialization for test connection issues
    
    async def transcribe(
        self,
        audio_data: Union[bytes, io.BytesIO],
        language: Optional[str] = None,
        prompt: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe audio using OpenAI API."""
        if self._status != ProviderStatus.READY:
            raise TranscriptionError(
                f"Provider not ready: {self._error_message}",
                provider_name="openai"
            )
        
        try:
            # Prepare audio buffer
            logger.debug(f"🔍 OpenAI provider received audio_data: type={type(audio_data)}, len={len(audio_data) if hasattr(audio_data, '__len__') else 'N/A'}")

            if isinstance(audio_data, bytes):
                logger.debug("✅ Processing bytes audio data")
                audio_buffer = io.BytesIO(audio_data)
                audio_buffer.name = "audio.wav"
            elif isinstance(audio_data, io.BytesIO):
                logger.debug("✅ Processing BytesIO audio data")
                audio_buffer = audio_data
                if not hasattr(audio_buffer, 'name'):
                    audio_buffer.name = "audio.wav"
            else:
                logger.error(f"❌ Unsupported audio data type: {type(audio_data)} - Expected bytes or BytesIO")
                raise TranscriptionError(
                    f"Unsupported audio data type: {type(audio_data)}",
                    provider_name="openai"
                )

            logger.debug(f"✅ Created audio_buffer for OpenAI: type={type(audio_buffer)}, name={getattr(audio_buffer, 'name', 'no name')}")
            
            # Prepare transcription parameters (exactly like legacy server)
            language_code = language or "nl"  # Default to Dutch

            # Get OpenAI-specific prompt from kwargs or use fallback (matches legacy logic)
            openai_prompt = kwargs.get('openai_prompt', self.fallback_prompt)

            # Use the passed prompt if provided, otherwise use openai_prompt (like legacy)
            final_prompt = prompt if prompt else openai_prompt

            logger.debug(f"OpenAI prompt strategy: passed_prompt={bool(prompt)}, openai_prompt_len={len(openai_prompt)}")
            logger.debug(f"Final prompt: {final_prompt[:100]}..." if len(final_prompt) > 100 else f"Final prompt: {final_prompt}")
            
            # Make API call
            logger.debug(f"Transcribing audio with OpenAI (model: {self.model_name}, language: {language_code})")
            
            # Reset buffer position (exactly like legacy server)
            audio_buffer.seek(0)

            response = await self.client.audio.transcriptions.create(
                model=self.model_name,
                file=("audio.wav", audio_buffer, "audio/wav"),  # File tuple format like legacy
                response_format="text",
                language=language_code,
                prompt=final_prompt,
                temperature=0.0  # Deterministic temperature for consistency (like legacy)
            )
            
            # Handle response format variations
            if isinstance(response, str):
                text = response.strip()
            elif hasattr(response, 'text'):
                text = response.text.strip()
            elif isinstance(response, dict) and 'text' in response:
                text = response['text'].strip()
            else:
                text = str(response).strip()
            
            # Create unified segment format
            segment = TranscriptionSegment(
                text=text,
                start=0.0,
                end=kwargs.get('duration', 0.0),
                id=0
            )
            
            result = TranscriptionResult(
                segments=[segment],
                text=text,
                language=language_code,
                duration=kwargs.get('duration'),
                metadata={
                    'provider': 'openai',
                    'model': self.model_name,
                    'prompt_used': final_prompt,
                    'temperature': 0.0,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
            
            logger.debug(f"OpenAI transcription completed: {len(text)} characters")
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"OpenAI transcription failed: {error_msg}")
            
            # Classify error types
            if "rate limit" in error_msg.lower():
                raise ProviderUnavailableError(
                    f"OpenAI rate limit exceeded: {error_msg}",
                    provider_name="openai",
                    error_code="rate_limit"
                )
            elif "authentication" in error_msg.lower():
                raise TranscriptionError(
                    f"OpenAI authentication failed: {error_msg}",
                    provider_name="openai", 
                    error_code="auth_failed"
                )
            else:
                raise TranscriptionError(
                    f"OpenAI transcription error: {error_msg}",
                    provider_name="openai"
                )
    
    async def stream_transcribe(
        self,
        audio_stream: AsyncIterator[bytes],
        language: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[TranscriptionResult]:
        """
        Stream transcription - OpenAI doesn't support true streaming,
        so we batch chunks and transcribe them.
        """
        if self._status != ProviderStatus.READY:
            raise TranscriptionError(
                f"Provider not ready: {self._error_message}",
                provider_name="openai"
            )
        
        logger.warning("OpenAI doesn't support streaming transcription, using batch processing")
        
        # Collect audio chunks
        audio_chunks = []
        async for chunk in audio_stream:
            audio_chunks.append(chunk)
            
            # Process when we have enough data (e.g., every 5 seconds of audio)
            total_size = sum(len(chunk) for chunk in audio_chunks)
            if total_size >= 80000:  # ~5 seconds at 16kHz mono
                combined_audio = b''.join(audio_chunks)
                
                try:
                    result = await self.transcribe(
                        combined_audio,
                        language=language,
                        duration=total_size / 32000,  # Approximate duration
                        **kwargs
                    )
                    yield result
                except Exception as e:
                    logger.error(f"Stream transcription chunk failed: {e}")
                    # Continue with next chunk
                
                audio_chunks.clear()
        
        # Process remaining chunks
        if audio_chunks:
            combined_audio = b''.join(audio_chunks)
            try:
                result = await self.transcribe(
                    combined_audio,
                    language=language,
                    duration=len(combined_audio) / 32000,
                    **kwargs
                )
                yield result
            except Exception as e:
                logger.error(f"Final stream transcription chunk failed: {e}")
    
    def get_capabilities(self) -> ProviderCapabilities:
        """Get OpenAI provider capabilities."""
        return ProviderCapabilities(
            supports_streaming=False,  # OpenAI doesn't support true streaming
            supports_batch=True,
            supported_languages=[
                'nl', 'en', 'de', 'fr', 'es', 'it', 'pt', 'ru', 'zh', 'ja', 'ko'
            ],
            supported_formats=[
                'wav', 'mp3', 'mp4', 'm4a', 'ogg', 'flac', 'webm'
            ],
            max_audio_length=1800,  # 30 minutes
            max_file_size=25 * 1024 * 1024  # 25MB
        )
    
    def get_info(self) -> ProviderInfo:
        """Get provider information."""
        return ProviderInfo(
            name="OpenAI ASR",
            provider_type=ProviderType.ASR,
            status=self._status,
            version="1.0.0",
            model_name=self.model_name,
            capabilities=self.get_capabilities(),
            error_message=self._error_message,
            last_updated=datetime.utcnow().isoformat()
        )
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.client:
            # OpenAI client doesn't need explicit cleanup
            pass
        logger.debug("OpenAI provider cleaned up")