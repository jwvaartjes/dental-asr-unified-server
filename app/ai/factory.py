"""
AI provider factory for creating and managing provider instances.
Uses factory pattern to create providers based on configuration.
"""
import logging
from typing import Optional, Dict, Any, List
from .interfaces import ASRProvider, LLMProvider, ProviderError, ProviderInitializationError
from .config import ProviderConfig, config_manager

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Factory for creating AI providers."""
    
    def __init__(self):
        self._asr_provider_cache: Optional[ASRProvider] = None
        self._llm_provider_cache: Optional[LLMProvider] = None
        
    async def create_asr_provider(self, config: Optional[ProviderConfig] = None) -> ASRProvider:
        """
        Create ASR provider instance.
        
        Args:
            config: Provider configuration. If None, loads from environment.
            
        Returns:
            Initialized ASR provider instance
            
        Raises:
            ProviderInitializationError: If provider creation fails
        """
        if config is None:
            config = config_manager.get_asr_config()
            
        # Validate configuration
        if not config_manager.validate_config(config):
            raise ProviderInitializationError(
                f"Invalid configuration for provider: {config.provider_type}"
            )
            
        logger.info(f"Creating ASR provider: {config.provider_type} with model: {config.model_name}")
        
        try:
            # Create provider based on type
            if config.provider_type == 'openai':
                provider = await self._create_openai_asr_provider(config)
            elif config.provider_type == 'openai_realtime':
                provider = await self._create_openai_realtime_provider(config)
            elif config.provider_type == 'whisper':
                provider = await self._create_whisper_provider(config)
            elif config.provider_type == 'azure_openai':
                provider = await self._create_azure_openai_provider(config)
            else:
                raise ProviderInitializationError(
                    f"Unknown ASR provider type: {config.provider_type}"
                )
                
            # Initialize provider
            success = await provider.initialize()
            if not success:
                raise ProviderInitializationError(
                    f"Failed to initialize {config.provider_type} provider: {provider.error_message}"
                )
                
            logger.info(f"Successfully created {config.provider_type} ASR provider")
            return provider
            
        except Exception as e:
            logger.error(f"Failed to create ASR provider {config.provider_type}: {e}")
            raise ProviderInitializationError(
                f"Provider creation failed: {str(e)}",
                provider_name=config.provider_type
            )
    
    async def _create_openai_asr_provider(self, config: ProviderConfig) -> ASRProvider:
        """Create OpenAI ASR provider."""
        try:
            from .providers.openai_provider import OpenAIASRProvider
            return OpenAIASRProvider(config.to_dict())
        except ImportError as e:
            raise ProviderInitializationError(
                f"OpenAI provider dependencies not available: {e}",
                provider_name="openai"
            )

    async def _create_openai_realtime_provider(self, config: ProviderConfig) -> ASRProvider:
        """Create OpenAI Realtime ASR provider."""
        try:
            from .providers.openai_realtime_provider import OpenAIRealtimeProvider
            # Extract API key and model from config
            api_key = config.config.get('api_key')
            model = config.model_name or "gpt-4o-realtime-preview-2024-12-17"
            return OpenAIRealtimeProvider(api_key=api_key, model=model)
        except ImportError as e:
            raise ProviderInitializationError(
                f"OpenAI Realtime provider dependencies not available: {e}",
                provider_name="openai_realtime"
            )
        except Exception as e:
            raise ProviderInitializationError(
                f"OpenAI Realtime provider creation failed: {e}",
                provider_name="openai_realtime"
            )

    async def _create_whisper_provider(self, config: ProviderConfig) -> ASRProvider:
        """Create local Whisper provider."""
        try:
            from .providers.whisper_provider import WhisperASRProvider
            return WhisperASRProvider(config.to_dict())
        except ImportError as e:
            raise ProviderInitializationError(
                f"Whisper provider dependencies not available: {e}",
                provider_name="whisper"
            )
        except Exception as e:
            raise ProviderInitializationError(
                f"Whisper provider creation failed: {e}",
                provider_name="whisper"
            )
    
    async def _create_azure_openai_provider(self, config: ProviderConfig) -> ASRProvider:
        """Create Azure OpenAI ASR provider."""
        try:
            from .providers.azure_openai_provider import AzureOpenAIASRProvider
            return AzureOpenAIASRProvider(config.to_dict())
        except ImportError as e:
            raise ProviderInitializationError(
                f"Azure OpenAI provider dependencies not available: {e}",
                provider_name="azure_openai"
            )
    
    async def create_llm_provider(self, config: Optional[ProviderConfig] = None) -> Optional[LLMProvider]:
        """
        Create LLM provider instance (future use).
        
        Args:
            config: Provider configuration. If None, loads from environment.
            
        Returns:
            Initialized LLM provider instance or None if not configured
        """
        if config is None:
            config = config_manager.get_llm_config()
            
        if config is None:
            logger.info("No LLM provider configured")
            return None
            
        # Validate configuration
        if not config_manager.validate_config(config):
            raise ProviderInitializationError(
                f"Invalid configuration for LLM provider: {config.provider_type}"
            )
            
        logger.info(f"Creating LLM provider: {config.provider_type} with model: {config.model_name}")
        
        try:
            # Create provider based on type
            if config.provider_type == 'openai':
                provider = await self._create_openai_llm_provider(config)
            elif config.provider_type == 'anthropic':
                provider = await self._create_anthropic_provider(config)
            else:
                raise ProviderInitializationError(
                    f"Unknown LLM provider type: {config.provider_type}"
                )
                
            # Initialize provider
            success = await provider.initialize()
            if not success:
                raise ProviderInitializationError(
                    f"Failed to initialize {config.provider_type} LLM provider: {provider.error_message}"
                )
                
            logger.info(f"Successfully created {config.provider_type} LLM provider")
            return provider
            
        except Exception as e:
            logger.error(f"Failed to create LLM provider {config.provider_type}: {e}")
            raise ProviderInitializationError(
                f"LLM provider creation failed: {str(e)}",
                provider_name=config.provider_type
            )
    
    async def _create_openai_llm_provider(self, config: ProviderConfig) -> LLMProvider:
        """Create OpenAI LLM provider."""
        try:
            from .providers.openai_llm_provider import OpenAILLMProvider
            return OpenAILLMProvider(config.to_dict())
        except ImportError as e:
            raise ProviderInitializationError(
                f"OpenAI LLM provider dependencies not available: {e}",
                provider_name="openai"
            )
    
    async def _create_anthropic_provider(self, config: ProviderConfig) -> LLMProvider:
        """Create Anthropic provider."""
        try:
            from .providers.anthropic_provider import AnthropicLLMProvider
            return AnthropicLLMProvider(config.to_dict())
        except ImportError as e:
            raise ProviderInitializationError(
                f"Anthropic provider dependencies not available: {e}",
                provider_name="anthropic"
            )
    
    async def get_cached_asr_provider(self) -> Optional[ASRProvider]:
        """Get cached ASR provider instance."""
        return self._asr_provider_cache
    
    async def get_or_create_asr_provider(self, config: Optional[ProviderConfig] = None) -> ASRProvider:
        """
        Get cached ASR provider or create new one.
        
        Args:
            config: Provider configuration. If None, loads from environment.
            
        Returns:
            ASR provider instance
        """
        # Check if we have a cached provider and if config matches
        if self._asr_provider_cache is not None:
            current_config = config or config_manager.get_asr_config()
            
            # Simple check - if provider type or model changed, recreate
            cached_info = self._asr_provider_cache.get_info()
            if (cached_info.model_name == current_config.model_name and 
                cached_info.name.lower().startswith(current_config.provider_type)):
                logger.debug("Using cached ASR provider")
                return self._asr_provider_cache
            else:
                logger.info("ASR configuration changed, recreating provider")
                await self._cleanup_asr_provider()
        
        # Create new provider
        self._asr_provider_cache = await self.create_asr_provider(config)
        return self._asr_provider_cache
    
    async def get_cached_llm_provider(self) -> Optional[LLMProvider]:
        """Get cached LLM provider instance."""
        return self._llm_provider_cache
    
    async def get_or_create_llm_provider(self, config: Optional[ProviderConfig] = None) -> Optional[LLMProvider]:
        """
        Get cached LLM provider or create new one.
        
        Args:
            config: Provider configuration. If None, loads from environment.
            
        Returns:
            LLM provider instance or None if not configured
        """
        # Check if we have a cached provider
        if self._llm_provider_cache is not None:
            current_config = config or config_manager.get_llm_config()
            
            if current_config is None:
                # No LLM configured, cleanup cached provider
                await self._cleanup_llm_provider()
                return None
            
            # Simple check - if provider type or model changed, recreate
            cached_info = self._llm_provider_cache.get_info()
            if (cached_info.model_name == current_config.model_name and 
                cached_info.name.lower().startswith(current_config.provider_type)):
                logger.debug("Using cached LLM provider")
                return self._llm_provider_cache
            else:
                logger.info("LLM configuration changed, recreating provider")
                await self._cleanup_llm_provider()
        
        # Create new provider
        self._llm_provider_cache = await self.create_llm_provider(config)
        return self._llm_provider_cache
    
    async def _cleanup_asr_provider(self):
        """Cleanup cached ASR provider."""
        if self._asr_provider_cache:
            try:
                await self._asr_provider_cache.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up ASR provider: {e}")
            finally:
                self._asr_provider_cache = None
    
    async def _cleanup_llm_provider(self):
        """Cleanup cached LLM provider."""
        if self._llm_provider_cache:
            try:
                await self._llm_provider_cache.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up LLM provider: {e}")
            finally:
                self._llm_provider_cache = None
    
    async def cleanup(self):
        """Cleanup all cached providers."""
        await self._cleanup_asr_provider()
        await self._cleanup_llm_provider()
        logger.info("Provider factory cleaned up")
    
    def get_supported_providers(self) -> Dict[str, Any]:
        """Get information about all supported providers."""
        return config_manager.get_supported_providers()


# Global factory instance
provider_factory = ProviderFactory()