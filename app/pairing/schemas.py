"""
WebSocket message schemas for validation using Pydantic.
Provides strict schema validation for all WebSocket message types.
"""

from typing import Optional, Dict, Any, List, Union, Literal
from datetime import datetime
from pydantic import BaseModel, Field, validator, root_validator
import re


# Base message schema
class BaseWSMessage(BaseModel):
    """Base schema for all WebSocket messages."""
    type: str = Field(..., min_length=1, max_length=50)
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    @validator('type')
    def validate_type(cls, v):
        """Ensure type contains only safe characters."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Message type contains invalid characters')
        return v


# Authentication messages
class IdentifyMessage(BaseWSMessage):
    """Desktop/Mobile identification message."""
    type: Literal['identify']
    device_type: Literal['desktop', 'mobile']
    session_id: str = Field(..., min_length=10, max_length=100)
    user_agent: Optional[str] = Field(None, max_length=500)
    
    @validator('session_id')
    def validate_session_id(cls, v):
        """Validate session ID format."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Invalid session ID format')
        return v


class MobileInitMessage(BaseWSMessage):
    """Mobile initialization with pairing code."""
    type: Literal['mobile_init']
    device_type: Literal['mobile']
    pairing_code: str = Field(..., pattern=r'^\d{6}$')
    session_id: str = Field(..., min_length=10, max_length=100)


# Channel messages
class JoinChannelMessage(BaseWSMessage):
    """Join a pairing channel."""
    type: Literal['join_channel']
    channel: str = Field(..., min_length=1, max_length=50)
    device_type: Literal['desktop', 'mobile']
    session_id: str = Field(..., min_length=10, max_length=100)
    
    @validator('channel')
    def validate_channel(cls, v):
        """Validate channel format."""
        if not re.match(r'^pair-\d{6}$', v):
            raise ValueError('Invalid channel format. Expected: pair-XXXXXX')
        return v


class ChannelMessage(BaseWSMessage):
    """Message to be broadcast to channel."""
    type: Literal['channel_message']
    channelId: str = Field(..., min_length=1, max_length=50)
    payload: Dict[str, Any]
    
    @validator('channelId')
    def validate_channel_id(cls, v):
        """Validate channel ID format."""
        if not re.match(r'^pair-\d{6}$', v):
            raise ValueError('Invalid channel ID format')
        return v
    
    @validator('payload')
    def validate_payload(cls, v):
        """Validate payload size and structure."""
        import json
        payload_str = json.dumps(v)
        if len(payload_str) > 10240:  # 10KB limit for channel messages
            raise ValueError('Payload exceeds maximum size')
        return v


# Audio messages
class AudioChunkMessage(BaseWSMessage):
    """Audio chunk for streaming."""
    type: Literal['audio_chunk', 'audio_data', 'audio_stream']
    chunk_id: Optional[str] = Field(None, max_length=50)
    audio_data: str = Field(..., max_length=1048576)  # Base64 encoded, ~1MB
    format: Optional[Literal['wav', 'mp3', 'webm', 'opus']] = 'webm'
    sample_rate: Optional[int] = Field(None, ge=8000, le=48000)
    
    @validator('audio_data')
    def validate_base64(cls, v):
        """Validate base64 encoding."""
        import base64
        try:
            base64.b64decode(v, validate=True)
        except Exception:
            raise ValueError('Invalid base64 encoded data')
        return v


# Settings sync messages
class SettingsSyncMessage(BaseWSMessage):
    """Settings synchronization between devices."""
    type: Literal['settings_sync']
    channelId: str = Field(..., pattern=r'^pair-\d{6}$')
    settings: Dict[str, Any]
    
    @validator('settings')
    def validate_settings(cls, v):
        """Validate settings structure."""
        allowed_keys = {
            'audioGain', 'autoGainEnabled', 'chunkDuration',
            'overlapPercent', 'paragraphBreakDuration',
            'language', 'model', 'vadEnabled'
        }
        
        # Check for unexpected keys
        unexpected = set(v.keys()) - allowed_keys
        if unexpected:
            raise ValueError(f'Unexpected settings keys: {unexpected}')
        
        # Validate value ranges
        if 'audioGain' in v:
            if not isinstance(v['audioGain'], (int, float)) or v['audioGain'] < 0 or v['audioGain'] > 100:
                raise ValueError('Invalid audioGain value')
        
        if 'chunkDuration' in v:
            if not isinstance(v['chunkDuration'], (int, float)) or v['chunkDuration'] < 0.5 or v['chunkDuration'] > 30:
                raise ValueError('Invalid chunkDuration value')
        
        return v


# Pairing status messages
class PairingSuccessMessage(BaseWSMessage):
    """Pairing success notification."""
    type: Literal['pairing_success']
    code: Optional[str] = Field(None, pattern=r'^\d{6}$')
    message: Optional[str] = Field(None, max_length=200)


class ClientJoinedMessage(BaseWSMessage):
    """Client joined channel notification."""
    type: Literal['client_joined']
    client_id: str = Field(..., max_length=100)
    device_type: Literal['desktop', 'mobile']


class DisconnectMessage(BaseWSMessage):
    """Disconnection notification."""
    type: Literal['desktop_disconnected', 'mobile_disconnected', 'client_disconnected']
    reason: Optional[str] = Field(None, max_length=200)
    force_disconnect: Optional[bool] = False


# Error messages
class ErrorMessage(BaseWSMessage):
    """Error notification."""
    type: Literal['error']
    code: Optional[str] = Field(None, max_length=50)
    message: str = Field(..., max_length=500)
    details: Optional[Dict[str, Any]] = None


# Heartbeat/Ping messages
class PingMessage(BaseWSMessage):
    """Ping message for keep-alive."""
    type: Literal['ping']
    sequence: Optional[int] = Field(None, ge=0)


class PongMessage(BaseWSMessage):
    """Pong response to ping."""
    type: Literal['pong']
    sequence: Optional[int] = Field(None, ge=0)


# Union type for all message types
WSMessage = Union[
    IdentifyMessage,
    MobileInitMessage,
    JoinChannelMessage,
    ChannelMessage,
    AudioChunkMessage,
    SettingsSyncMessage,
    PairingSuccessMessage,
    ClientJoinedMessage,
    DisconnectMessage,
    ErrorMessage,
    PingMessage,
    PongMessage
]


class MessageValidator:
    """Utility class for validating WebSocket messages."""
    
    # Map message types to their schemas
    MESSAGE_SCHEMAS = {
        'identify': IdentifyMessage,
        'mobile_init': MobileInitMessage,
        'join_channel': JoinChannelMessage,
        'channel_message': ChannelMessage,
        'audio_chunk': AudioChunkMessage,
        'audio_data': AudioChunkMessage,
        'audio_stream': AudioChunkMessage,
        'settings_sync': SettingsSyncMessage,
        'pairing_success': PairingSuccessMessage,
        'client_joined': ClientJoinedMessage,
        'desktop_disconnected': DisconnectMessage,
        'mobile_disconnected': DisconnectMessage,
        'client_disconnected': DisconnectMessage,
        'error': ErrorMessage,
        'ping': PingMessage,
        'pong': PongMessage
    }
    
    @classmethod
    def validate_message(cls, message_dict: dict) -> tuple[bool, Optional[BaseWSMessage], Optional[str]]:
        """
        Validate a WebSocket message against its schema.
        Returns (is_valid, validated_message, error_message).
        """
        try:
            # Get message type
            msg_type = message_dict.get('type')
            if not msg_type:
                return False, None, "Missing 'type' field"
            
            # Get corresponding schema
            schema_class = cls.MESSAGE_SCHEMAS.get(msg_type)
            if not schema_class:
                return False, None, f"Unknown message type: {msg_type}"
            
            # Validate against schema
            validated = schema_class(**message_dict)
            return True, validated, None
            
        except Exception as e:
            return False, None, str(e)
    
    @classmethod
    def sanitize_message(cls, message_dict: dict) -> dict:
        """
        Sanitize a message by removing potentially dangerous content.
        Returns sanitized message dict.
        """
        sanitized = {}
        
        for key, value in message_dict.items():
            # Skip keys that are too long
            if len(str(key)) > 50:
                continue
            
            # Sanitize string values
            if isinstance(value, str):
                # Remove control characters
                value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')
                # Truncate if too long
                if len(value) > 10000:
                    value = value[:10000]
            
            # Recursively sanitize nested dicts
            elif isinstance(value, dict):
                value = cls.sanitize_message(value)
            
            # Limit list sizes
            elif isinstance(value, list):
                value = value[:100]  # Max 100 items in lists
            
            sanitized[key] = value
        
        return sanitized


class ConnectionLimits:
    """Configuration for connection limits and thresholds."""
    
    # Maximum connections per IP
    MAX_CONNECTIONS_PER_IP = 50
    
    # Maximum channels per connection
    MAX_CHANNELS_PER_CONNECTION = 5
    
    # Maximum message rate (messages per second)
    MAX_MESSAGE_RATE = 10.0
    
    # Maximum pairing attempts
    MAX_PAIRING_ATTEMPTS = 5
    PAIRING_WINDOW_SECONDS = 60
    
    # Message size limits
    TEXT_MESSAGE_LIMIT = 10 * 1024              # 10KB for text
    AUDIO_CHUNK_LIMIT = 1024 * 1024             # 1MB for streaming audio chunks  
    AUDIO_FILE_LIMIT = 100 * 1024 * 1024        # 100MB for complete audio files
    BINARY_MESSAGE_LIMIT = 50 * 1024 * 1024     # 50MB for binary/file uploads
    
    # Timeout settings
    CONNECTION_TIMEOUT = 300  # 5 minutes
    IDLE_TIMEOUT = 600       # 10 minutes
    
    # Burst limits
    MESSAGE_BURST_SIZE = 20
    
    @classmethod
    def get_message_size_limit(cls, message_type: str) -> int:
        """Get size limit for specific message type."""
        audio_types = {'audio_chunk', 'audio_data', 'audio_stream'}
        binary_types = {'file_upload', 'binary_data', 'image'}
        
        if message_type in audio_types:
            return cls.AUDIO_MESSAGE_LIMIT
        elif message_type in binary_types:
            return cls.BINARY_MESSAGE_LIMIT
        else:
            return cls.TEXT_MESSAGE_LIMIT