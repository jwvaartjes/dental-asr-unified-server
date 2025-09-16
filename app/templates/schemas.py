"""
Consultation Template Schemas
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime


class TemplateSettings(BaseModel):
    """Template configuration settings"""
    prompt_config: Dict[str, Any] = Field(
        default={
            "system_prompt": "Dit is een Nederlandse tandheelkundige consultatie. Gebruik correcte tandheelkundige terminologie.",
            "include_base_prompt": True,
            "additional_context": ""
        },
        description="Prompt configuration"
    )

    ai_model_config: Dict[str, Any] = Field(
        default={
            "provider": "openai",
            "model_name": "gpt-4o-transcribe",
            "language": "nl",
            "temperature": 0.2
        },
        description="Model configuration"
    )

    vad_config: Dict[str, Any] = Field(
        default={
            "enable_silero": True,
            "silero_threshold": 0.9,
            "enable_frontend_vad": False,
            "silence_duration": 1.5
        },
        description="Voice Activity Detection configuration"
    )

    lexicon_config: Dict[str, Any] = Field(
        default={
            "enabled_categories": [],
            "disabled_categories": [],
            "use_custom_patterns": True,
            "use_protected_words": True,
            "custom_additions": {}
        },
        description="Lexicon configuration"
    )

    normalization_config: Dict[str, Any] = Field(
        default={
            "enable_phonetic": True,
            "phonetic_threshold": 0.84,
            "enable_element_parsing": True,
            "enable_variant_generation": True
        },
        description="Normalization configuration"
    )


class ConsultationTemplate(BaseModel):
    """Consultation template model"""
    id: Optional[str] = Field(None, description="Template ID (UUID)")
    user_id: str = Field(..., description="Owner user ID")
    template_name: str = Field(..., description="Template name")
    template_type: str = Field(default="general", description="Template type")
    description: Optional[str] = Field(default="", description="Template description")
    is_active: bool = Field(default=False, description="Currently active template")
    is_default: bool = Field(default=False, description="Default template for user")
    settings: TemplateSettings = Field(..., description="Template settings")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class CreateTemplateRequest(BaseModel):
    """Request to create a new template"""
    template_name: str = Field(..., description="Template name")
    template_type: str = Field(default="general", description="Template type")
    description: Optional[str] = Field(default="", description="Template description")
    is_default: bool = Field(default=False, description="Set as default template")
    settings: TemplateSettings = Field(..., description="Template settings")


class UpdateTemplateRequest(BaseModel):
    """Request to update an existing template"""
    template_name: Optional[str] = Field(None, description="Template name")
    template_type: Optional[str] = Field(None, description="Template type")
    description: Optional[str] = Field(None, description="Template description")
    is_default: Optional[bool] = Field(None, description="Set as default template")
    settings: Optional[TemplateSettings] = Field(None, description="Template settings")


class TemplateListResponse(BaseModel):
    """Response containing list of templates"""
    templates: List[ConsultationTemplate] = Field(..., description="List of templates")
    active_template_id: Optional[str] = Field(None, description="Currently active template ID")


class TranscriptionRequestWithTemplate(BaseModel):
    """Enhanced transcription request with template support"""
    audio_data: str = Field(..., description="Base64-encoded audio data")
    language: Optional[str] = Field("nl", description="Language code")
    template_id: Optional[str] = Field(None, description="Template ID to use")
    override_settings: Optional[Dict[str, Any]] = Field(None, description="Temporary setting overrides")
    format: Optional[str] = Field("wav", description="Audio format")