"""
AI provider configuration management.
Handles provider selection and configuration based on environment variables.
"""
import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Configuration for a specific provider."""
    provider_type: str  # 'openai', 'whisper', 'azure_openai', etc.
    model_name: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    organization: Optional[str] = None
    extra_config: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for provider initialization."""
        config = {
            'model': self.model_name,
        }
        
        if self.api_key:
            config['api_key'] = self.api_key
        if self.api_base:
            config['api_base'] = self.api_base
        if self.api_version:
            config['api_version'] = self.api_version
        if self.organization:
            config['organization'] = self.organization
        if self.extra_config:
            config.update(self.extra_config)
            
        return config


class AIConfigManager:
    """Manages AI provider configuration."""
    
    def __init__(self):
        self._config_cache = {}
        
    def get_asr_config(self) -> ProviderConfig:
        """Get ASR provider configuration from environment."""
        model_id = os.getenv('MODEL_ID', 'openai/gpt-4o-transcribe')
        
        logger.info(f"Loading ASR config for MODEL_ID: {model_id}")
        
        # Parse provider and model from MODEL_ID
        if '/' in model_id:
            provider_type, model_name = model_id.split('/', 1)
        else:
            # Default to local whisper for non-prefixed models
            provider_type = 'whisper'
            model_name = model_id
            
        # Create provider-specific configuration
        if provider_type == 'openai':
            return self._create_openai_config(model_name)
        elif provider_type == 'whisper':
            return self._create_whisper_config(model_name)
        elif provider_type == 'azure_openai':
            return self._create_azure_openai_config(model_name)
        elif provider_type == 'anthropic':
            return self._create_anthropic_config(model_name)
        else:
            logger.warning(f"Unknown provider type '{provider_type}', defaulting to OpenAI")
            return self._create_openai_config(model_name)
    
    def _create_openai_config(self, model_name: str) -> ProviderConfig:
        """Create OpenAI provider configuration."""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("OPENAI_API_KEY not found in environment")
        
        return ProviderConfig(
            provider_type='openai',
            model_name=model_name,
            api_key=api_key,
            api_base=os.getenv('OPENAI_API_BASE'),
            organization=os.getenv('OPENAI_ORGANIZATION'),
            extra_config={
                'timeout': float(os.getenv('OPENAI_TIMEOUT', '30')),
                'max_retries': int(os.getenv('OPENAI_MAX_RETRIES', '3'))
            }
        )
    
    def _create_whisper_config(self, model_name: str) -> ProviderConfig:
        """Create local Whisper provider configuration."""
        return ProviderConfig(
            provider_type='whisper',
            model_name=model_name,
            extra_config={
                'device': os.getenv('WHISPER_DEVICE', 'auto'),
                'compute_type': os.getenv('WHISPER_COMPUTE_TYPE', 'float16'),
                'beam_size': int(os.getenv('WHISPER_BEAM_SIZE', '5')),
                'best_of': int(os.getenv('WHISPER_BEST_OF', '5')),
                'temperature': float(os.getenv('WHISPER_TEMPERATURE', '0')),
                'cache_dir': os.getenv('WHISPER_CACHE_DIR', '.whisper_cache')
            }
        )
    
    def _create_azure_openai_config(self, model_name: str) -> ProviderConfig:
        """Create Azure OpenAI provider configuration."""
        api_key = os.getenv('AZURE_OPENAI_API_KEY')
        api_base = os.getenv('AZURE_OPENAI_ENDPOINT')
        api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-01')
        
        if not api_key or not api_base:
            logger.warning("Azure OpenAI configuration incomplete")
        
        return ProviderConfig(
            provider_type='azure_openai',
            model_name=model_name,
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            extra_config={
                'deployment_name': os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', model_name),
                'timeout': float(os.getenv('AZURE_OPENAI_TIMEOUT', '30'))
            }
        )
    
    def _create_anthropic_config(self, model_name: str) -> ProviderConfig:
        """Create Anthropic provider configuration."""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not found in environment")
        
        return ProviderConfig(
            provider_type='anthropic',
            model_name=model_name,
            api_key=api_key,
            api_base=os.getenv('ANTHROPIC_API_BASE', 'https://api.anthropic.com'),
            extra_config={
                'timeout': float(os.getenv('ANTHROPIC_TIMEOUT', '60')),
                'max_tokens': int(os.getenv('ANTHROPIC_MAX_TOKENS', '4096'))
            }
        )
    
    def get_llm_config(self) -> Optional[ProviderConfig]:
        """Get LLM provider configuration (future use)."""
        llm_model_id = os.getenv('LLM_MODEL_ID')
        if not llm_model_id:
            return None
            
        logger.info(f"Loading LLM config for MODEL_ID: {llm_model_id}")
        
        # Parse provider and model
        if '/' in llm_model_id:
            provider_type, model_name = llm_model_id.split('/', 1)
        else:
            provider_type = 'openai'  # Default
            model_name = llm_model_id
            
        # For now, only support OpenAI and Anthropic for LLM
        if provider_type == 'openai':
            return self._create_openai_config(model_name)
        elif provider_type == 'anthropic':
            return self._create_anthropic_config(model_name)
        else:
            logger.warning(f"Unsupported LLM provider: {provider_type}")
            return None
    
    def validate_config(self, config: ProviderConfig) -> bool:
        """Validate provider configuration."""
        if not config.model_name:
            logger.error("Model name is required")
            return False
            
        # Provider-specific validation
        if config.provider_type == 'openai':
            if not config.api_key:
                logger.error("OpenAI API key is required")
                return False
        elif config.provider_type == 'azure_openai':
            if not config.api_key or not config.api_base:
                logger.error("Azure OpenAI requires API key and endpoint")
                return False
        elif config.provider_type == 'anthropic':
            if not config.api_key:
                logger.error("Anthropic API key is required")
                return False
                
        return True
    
    def get_supported_providers(self) -> Dict[str, Dict[str, Any]]:
        """Get information about supported providers."""
        return {
            'openai': {
                'name': 'OpenAI',
                'type': 'asr',
                'models': ['gpt-4o-transcribe', 'whisper-1'],
                'requires_api_key': True,
                'supports_streaming': False
            },
            'whisper': {
                'name': 'Local Whisper',
                'type': 'asr',
                'models': [
                    'openai/whisper-large-v2',
                    'openai/whisper-medium',
                    'janwillemvaartjes/whisper-dutch-dental'
                ],
                'requires_api_key': False,
                'supports_streaming': True
            },
            'azure_openai': {
                'name': 'Azure OpenAI',
                'type': 'asr',
                'models': ['whisper'],
                'requires_api_key': True,
                'supports_streaming': False
            },
            'anthropic': {
                'name': 'Anthropic Claude',
                'type': 'llm',
                'models': ['claude-3-haiku', 'claude-3-sonnet'],
                'requires_api_key': True,
                'supports_streaming': True
            }
        }


# Global config manager instance
config_manager = AIConfigManager()