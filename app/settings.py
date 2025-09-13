"""
Application settings and configuration using Pydantic BaseSettings.
"""
import os
from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from enum import Enum


class Environment(str, Enum):
    """Application environment."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TEST = "test"


class Settings(BaseSettings):
    """Application settings with environment-based configuration."""
    
    # Environment
    app_env: Environment = Field(
        default=Environment.DEVELOPMENT,
        env="APP_ENV",
        description="Application environment"
    )
    
    # Server settings
    port: int = Field(
        default=3001,
        env="PORT",
        description="Server port"
    )
    host: str = Field(
        default="0.0.0.0",
        env="HOST",
        description="Server host"
    )
    
    # JWT settings
    jwt_secret: str = Field(
        default="test-secret-key-for-local-testing",
        env="JWT_SECRET",
        description="JWT secret key"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        env="JWT_ALGORITHM",
        description="JWT algorithm"
    )
    jwt_expiry_hours: int = Field(
        default=1,
        env="JWT_EXPIRY_HOURS",
        description="JWT token expiry in hours"
    )
    
    # CORS settings
    allowed_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost:8085",
            "http://localhost:8086",
            "http://localhost:8087",
            "http://localhost:8088",
            "http://localhost:8089",
            "null"
        ],
        env="ALLOWED_ORIGINS",
        description="Allowed CORS origins"
    )
    
    # Rate limiting settings
    rate_limit_enabled: bool = Field(
        default=True,
        env="RATE_LIMIT_ENABLED",
        description="Enable rate limiting"
    )
    max_requests_per_minute: int = Field(
        default=30,
        env="MAX_REQUESTS_PER_MINUTE",
        description="Maximum requests per minute"
    )
    max_connections_per_ip: int = Field(
        default=50,
        env="MAX_CONNECTIONS_PER_IP",
        description="Maximum WebSocket connections per IP"
    )
    max_messages_per_second: float = Field(
        default=10.0,
        env="MAX_MESSAGES_PER_SECOND",
        description="Maximum messages per second"
    )
    max_pairing_attempts: int = Field(
        default=5,
        env="MAX_PAIRING_ATTEMPTS",
        description="Maximum pairing attempts"
    )
    pairing_window_seconds: int = Field(
        default=60,
        env="PAIRING_WINDOW_SECONDS",
        description="Pairing window in seconds"
    )
    
    # Storage settings
    use_redis: bool = Field(
        default=False,
        env="USE_REDIS",
        description="Use Redis for storage"
    )
    redis_host: str = Field(
        default="localhost",
        env="REDIS_HOST",
        description="Redis host"
    )
    redis_port: int = Field(
        default=6379,
        env="REDIS_PORT",
        description="Redis port"
    )
    redis_db: int = Field(
        default=0,
        env="REDIS_DB",
        description="Redis database number"
    )
    
    # WebSocket settings
    ws_message_size_limit: int = Field(
        default=10 * 1024,
        env="WS_MESSAGE_SIZE_LIMIT",
        description="WebSocket message size limit (bytes)"
    )
    ws_audio_chunk_limit: int = Field(
        default=1024 * 1024,
        env="WS_AUDIO_CHUNK_LIMIT",
        description="WebSocket audio chunk limit (bytes)"
    )
    ws_audio_file_limit: int = Field(
        default=100 * 1024 * 1024,
        env="WS_AUDIO_FILE_LIMIT",
        description="WebSocket audio file limit (bytes)"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="Logging level"
    )
    
    # OpenAI settings
    openai_api_key: str = Field(
        default="",
        env="OPENAI_API_KEY",
        description="OpenAI API key"
    )
    model_id: str = Field(
        default="openai/gpt-4o-transcribe",
        env="MODEL_ID",
        description="AI model identifier"
    )
    
    # HuggingFace settings
    hf_token: str = Field(
        default="",
        env="HF_TOKEN",
        description="HuggingFace token"
    )
    
    # Supabase settings
    supabase_url: str = Field(
        default="",
        env="SUPABASE_URL",
        description="Supabase project URL"
    )
    supabase_service_key: str = Field(
        default="",
        env="SUPABASE_SERVICE_KEY",
        description="Supabase service role key"
    )
    supabase_anon_key: str = Field(
        default="",
        env="SUPABASE_ANON_KEY",
        description="Supabase anonymous key"
    )
    
    @validator("allowed_origins", pre=True)
    def parse_allowed_origins(cls, v):
        """Parse allowed origins from comma-separated string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("app_env", pre=True)
    def parse_app_env(cls, v):
        """Parse app environment, handle common variations."""
        if isinstance(v, str):
            v = v.lower()
            if v in ["dev", "development", "local"]:
                return Environment.DEVELOPMENT
            elif v in ["prod", "production"]:
                return Environment.PRODUCTION
            elif v in ["test", "testing"]:
                return Environment.TEST
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == Environment.DEVELOPMENT
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == Environment.PRODUCTION
    
    @property
    def is_test(self) -> bool:
        """Check if running in test mode."""
        return self.app_env == Environment.TEST
    
    def get_port(self) -> int:
        """Get port based on environment."""
        if self.is_development:
            # Development defaults to 8089
            return self.port if self.port != 3001 else 8089
        return self.port
    
    def get_allowed_origins(self) -> List[str]:
        """Get allowed origins based on environment."""
        if self.is_production:
            # Production origins
            return [
                "https://mondplan.com",
                "https://www.mondplan.com",
                "https://app.mondplan.com"
            ]
        elif self.is_test:
            # Test origins
            return ["http://localhost:5173", "http://localhost:8089"]
        else:
            # Development origins (default)
            return self.allowed_origins
    
    def should_use_redis(self) -> bool:
        """Determine if Redis should be used based on environment."""
        if self.is_production:
            return True  # Always use Redis in production
        return self.use_redis  # Use config value in dev/test
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Use enum values in JSON
        use_enum_values = True


# Global settings instance - will be created by factory
settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings instance."""
    global settings
    if settings is None:
        settings = Settings()
    return settings


def configure_settings(**overrides) -> Settings:
    """Configure settings with overrides (useful for testing)."""
    global settings
    settings = Settings(**overrides)
    return settings