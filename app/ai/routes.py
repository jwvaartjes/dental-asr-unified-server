"""
AI provider API routes.
Provides endpoints for transcription, provider management, and status.
"""
import logging
import base64
import io
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, status
from pydantic import BaseModel, Field

from .factory import provider_factory
from .interfaces import TranscriptionResult, ProviderInfo, ProviderError
from .normalization import NormalizationPipeline
from ..pairing.security import SecurityMiddleware
from ..data.registry import DataRegistry

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/ai", tags=["ai"])


# Request/Response models
class TranscriptionRequest(BaseModel):
    """Request model for transcription."""
    audio_data: str = Field(..., description="Base64-encoded audio data")
    language: Optional[str] = Field("nl", description="Language code (e.g., 'nl', 'en')")
    prompt: Optional[str] = Field(None, description="Context prompt for better accuracy")
    format: Optional[str] = Field("wav", description="Audio format")


class TranscriptionResponse(BaseModel):
    """Response model for transcription."""
    text: str  # Keep for backward compatibility
    raw: str   # Raw transcription from ASR
    normalized: str  # Normalized transcription (same as raw for now, until normalization is implemented)
    segments: List[Dict[str, Any]]
    language: Optional[str] = None
    duration: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class ProviderInfoResponse(BaseModel):
    """Response model for provider information."""
    name: str
    provider_type: str
    status: str
    version: Optional[str] = None
    model_name: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    last_updated: Optional[str] = None


class ProvidersListResponse(BaseModel):
    """Response model for supported providers list."""
    providers: Dict[str, Dict[str, Any]]


class StatusResponse(BaseModel):
    """Response model for AI service status."""
    asr_provider: Optional[ProviderInfoResponse] = None
    llm_provider: Optional[ProviderInfoResponse] = None
    supported_providers: Dict[str, Dict[str, Any]]


def get_security_middleware(request: Request) -> SecurityMiddleware:
    """Dependency to get security middleware from app state."""
    return request.app.state.security_middleware


def get_normalization_pipeline(request: Request) -> NormalizationPipeline:
    """Dependency to get normalization pipeline from app state."""
    return getattr(request.app.state, 'normalization_pipeline', None)


def get_data_registry(request: Request) -> DataRegistry:
    """Dependency to get data registry from app state."""
    return request.app.state.data_registry


async def apply_normalization(
    text: str, 
    language: str = "nl",
    pipeline: NormalizationPipeline = None
) -> tuple[str, str]:
    """Apply normalization to text. Returns (raw, normalized)."""
    if not pipeline or not text.strip():
        return text, text
    
    try:
        result = pipeline.normalize(text, language=language)
        return text, result.normalized_text
    except Exception as e:
        logger.warning(f"⚠️ Normalization failed: {e}")
        return text, text


# API Endpoints
@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    request_data: TranscriptionRequest,
    request: Request,
    security: SecurityMiddleware = Depends(get_security_middleware),
    normalization_pipeline: NormalizationPipeline = Depends(get_normalization_pipeline)
):
    """Transcribe audio data using the configured ASR provider."""
    # Validate request
    await security.validate_request(request)
    
    try:
        # Get ASR provider
        provider = await provider_factory.get_or_create_asr_provider()
        
        # Decode base64 audio data
        try:
            audio_bytes = base64.b64decode(request_data.audio_data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid base64 audio data: {str(e)}"
            )
        
        # Create audio buffer
        audio_buffer = io.BytesIO(audio_bytes)
        audio_buffer.name = f"audio.{request_data.format}"
        
        # Transcribe audio
        result = await provider.transcribe(
            audio_data=audio_buffer,
            language=request_data.language,
            prompt=request_data.prompt,
            duration=len(audio_bytes) / 32000  # Approximate duration
        )
        
        # Apply normalization
        raw_text, normalized_text = await apply_normalization(
            result.text, 
            language=request_data.language or "nl",
            pipeline=normalization_pipeline
        )
        
        # Convert segments to dict format
        segments_dict = []
        for segment in result.segments:
            segments_dict.append({
                "text": segment.text,
                "start": segment.start,
                "end": segment.end,
                "id": segment.id
            })
        
        return TranscriptionResponse(
            text=normalized_text,  # Return normalized text as main text field
            raw=raw_text,  # Raw transcription from ASR
            normalized=normalized_text,  # Normalized transcription
            segments=segments_dict,
            language=result.language,
            duration=result.duration,
            metadata=result.metadata
        )
        
    except ProviderError as e:
        logger.error(f"Provider error during transcription: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Transcription service error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during transcription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal transcription error"
        )


@router.post("/transcribe-file", response_model=TranscriptionResponse)
async def transcribe_file(
    file: UploadFile = File(...),
    language: Optional[str] = "nl",
    prompt: Optional[str] = None,
    request: Request = None,
    security: SecurityMiddleware = Depends(get_security_middleware)
):
    """Transcribe uploaded audio file."""
    # Validate request
    await security.validate_request(request)
    
    # Check file size (limit to 25MB)
    max_size = 25 * 1024 * 1024
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {max_size/1024/1024}MB"
        )
    
    try:
        # Get ASR provider
        provider = await provider_factory.get_or_create_asr_provider()
        
        # Create audio buffer
        audio_buffer = io.BytesIO(content)
        audio_buffer.name = file.filename
        
        # Transcribe audio
        result = await provider.transcribe(
            audio_data=audio_buffer,
            language=language,
            prompt=prompt,
            duration=len(content) / 32000  # Approximate duration
        )
        
        # Convert segments to dict format
        segments_dict = []
        for segment in result.segments:
            segments_dict.append({
                "text": segment.text,
                "start": segment.start,
                "end": segment.end,
                "id": segment.id
            })
        
        return TranscriptionResponse(
            text=result.text,  # For file upload, keeping raw text for now
            raw=result.text,  # Raw transcription from ASR
            normalized=result.text,  # For file upload, keeping raw text for now
            segments=segments_dict,
            language=result.language,
            duration=result.duration,
            metadata=result.metadata
        )
        
    except ProviderError as e:
        logger.error(f"Provider error during file transcription: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Transcription service error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during file transcription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal transcription error"
        )


@router.get("/providers", response_model=ProvidersListResponse)
async def get_supported_providers(
    request: Request,
    security: SecurityMiddleware = Depends(get_security_middleware)
):
    """Get list of supported AI providers."""
    await security.validate_request(request)
    
    try:
        providers_info = provider_factory.get_supported_providers()
        return ProvidersListResponse(providers=providers_info)
        
    except Exception as e:
        logger.error(f"Error getting providers list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get providers information"
        )


@router.get("/status", response_model=StatusResponse)
async def get_ai_status(
    request: Request,
    security: SecurityMiddleware = Depends(get_security_middleware)
):
    """Get AI service status including current providers."""
    await security.validate_request(request)
    
    try:
        # Get current providers
        asr_provider = await provider_factory.get_cached_asr_provider()
        llm_provider = await provider_factory.get_cached_llm_provider()
        
        # Convert provider info to response format
        asr_info = None
        if asr_provider:
            info = asr_provider.get_info()
            asr_info = ProviderInfoResponse(
                name=info.name,
                provider_type=info.provider_type.value,
                status=info.status.value,
                version=info.version,
                model_name=info.model_name,
                capabilities=info.capabilities.__dict__ if info.capabilities else None,
                error_message=info.error_message,
                last_updated=info.last_updated
            )
        
        llm_info = None
        if llm_provider:
            info = llm_provider.get_info()
            llm_info = ProviderInfoResponse(
                name=info.name,
                provider_type=info.provider_type.value,
                status=info.status.value,
                version=info.version,
                model_name=info.model_name,
                capabilities=info.capabilities.__dict__ if info.capabilities else None,
                error_message=info.error_message,
                last_updated=info.last_updated
            )
        
        # Get supported providers
        supported_providers = provider_factory.get_supported_providers()
        
        return StatusResponse(
            asr_provider=asr_info,
            llm_provider=llm_info,
            supported_providers=supported_providers
        )
        
    except Exception as e:
        logger.error(f"Error getting AI status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get AI service status"
        )


@router.post("/reload")
async def reload_providers(
    request: Request,
    security: SecurityMiddleware = Depends(get_security_middleware)
):
    """Reload AI providers with new configuration."""
    await security.validate_request(request)
    
    try:
        # Cleanup existing providers
        await provider_factory.cleanup()
        
        # Create new providers (will be lazy-loaded on next request)
        logger.info("AI providers reloaded successfully")
        
        return {"message": "AI providers reloaded successfully"}
        
    except Exception as e:
        logger.error(f"Error reloading providers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload providers: {str(e)}"
        )


@router.get("/model-info")
async def get_model_info(
    request: Request,
    security: SecurityMiddleware = Depends(get_security_middleware)
):
    """Get current model information for WebSocket compatibility."""
    await security.validate_request(request)
    
    try:
        # Get or create ASR provider
        provider = await provider_factory.get_or_create_asr_provider()
        info = provider.get_info()
        
        # Format for WebSocket compatibility with existing client
        return {
            "model_id": info.model_name,
            "provider": info.name,
            "status": info.status.value,
            "capabilities": {
                "supports_streaming": info.capabilities.supports_streaming if info.capabilities else False,
                "supported_languages": info.capabilities.supported_languages if info.capabilities else ["nl"],
                "max_audio_length": info.capabilities.max_audio_length if info.capabilities else 1800
            }
        }
        
    except ProviderError as e:
        logger.error(f"Provider error getting model info: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model service error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get model information"
        )


@router.get("/normalization/config")
async def get_normalization_config(
    request: Request,
    security: SecurityMiddleware = Depends(get_security_middleware),
    data_registry: DataRegistry = Depends(get_data_registry)
):
    """Get complete normalization configuration from Supabase used by the pipeline."""
    await security.validate_request(request)
    
    try:
        # Use admin user ID for config (same as in main.py startup)
        admin_id = data_registry.loader.get_admin_id()
        
        # Get all configuration data that the normalization pipeline uses
        config = await data_registry.get_config(admin_id)
        lexicon = await data_registry.get_lexicon(admin_id)
        custom_patterns = await data_registry.get_custom_patterns(admin_id)
        protected_words = await data_registry.get_protected_words(admin_id)
        
        # Get cache stats as well
        cache_stats = await data_registry.get_cache_stats()
        
        return {
            "admin_user_id": admin_id,
            "config": config,
            "lexicon": lexicon,
            "custom_patterns": custom_patterns, 
            "protected_words": protected_words,
            "cache_stats": cache_stats,
            "data_source": "supabase",
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting normalization config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get normalization configuration: {str(e)}"
        )