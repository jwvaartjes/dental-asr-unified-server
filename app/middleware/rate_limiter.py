"""
Rate limiting module for HTTP and WebSocket connections.
Provides both request-based and connection-based rate limiting with configurable limits.
"""

import time
import random
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """HTTP request rate limiter with per-IP tracking."""
    
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_counts: Dict[str, deque] = defaultdict(deque)
    
    def is_allowed(self, ip: str) -> bool:
        """Check if request from IP is allowed."""
        now = time.time()
        requests = self.request_counts[ip]
        
        # Remove old requests outside the window
        while requests and requests[0] < now - self.window_seconds:
            requests.popleft()
        
        # Check if limit exceeded
        if len(requests) >= self.max_requests:
            return False
        
        # Add current request
        requests.append(now)
        return True
    
    def get_retry_after(self, ip: str) -> int:
        """Get seconds until next request is allowed."""
        if not self.request_counts[ip]:
            return 0
        
        oldest_request = self.request_counts[ip][0]
        retry_after = int(oldest_request + self.window_seconds - time.time())
        
        # Add jitter (0-3 seconds)
        retry_after += random.randint(0, 3)
        
        return max(0, retry_after)


class WebSocketRateLimiter:
    """WebSocket-specific rate limiter with connection and message rate limiting."""
    
    def __init__(
        self,
        max_connections_per_ip: int = 50,
        max_messages_per_second: float = 10.0,
        max_pairing_attempts: int = 5,
        pairing_window_seconds: int = 60,
        burst_size: int = 20
    ):
        self.max_connections_per_ip = max_connections_per_ip
        self.max_messages_per_second = max_messages_per_second
        self.max_pairing_attempts = max_pairing_attempts
        self.pairing_window_seconds = pairing_window_seconds
        self.burst_size = burst_size
        
        # Track active connections per IP
        self.connections_per_ip: Dict[str, set] = defaultdict(set)
        
        # Track message rates per connection (token bucket algorithm)
        self.message_buckets: Dict[str, dict] = {}
        
        # Track pairing attempts per IP
        self.pairing_attempts: Dict[str, deque] = defaultdict(deque)
        
        # Track channel message rates
        self.channel_message_rates: Dict[str, deque] = defaultdict(deque)
        
    def can_connect(self, ip: str, connection_id: str) -> Tuple[bool, Optional[str]]:
        """Check if new WebSocket connection is allowed."""
        if len(self.connections_per_ip[ip]) >= self.max_connections_per_ip:
            return False, f"Too many connections from IP {ip}"
        
        return True, None
    
    def register_connection(self, ip: str, connection_id: str):
        """Register a new WebSocket connection."""
        self.connections_per_ip[ip].add(connection_id)
        
        # Initialize token bucket for this connection
        self.message_buckets[connection_id] = {
            'tokens': self.burst_size,
            'last_refill': time.time()
        }
        
        logger.info(f"Registered connection {connection_id} from {ip}. "
                   f"Total connections from IP: {len(self.connections_per_ip[ip])}")
    
    def unregister_connection(self, ip: str, connection_id: str):
        """Remove a WebSocket connection."""
        if connection_id in self.connections_per_ip[ip]:
            self.connections_per_ip[ip].remove(connection_id)
            
        if connection_id in self.message_buckets:
            del self.message_buckets[connection_id]
            
        # Clean up empty IP entries
        if not self.connections_per_ip[ip]:
            del self.connections_per_ip[ip]
            
        logger.info(f"Unregistered connection {connection_id} from {ip}")
    
    def can_send_message(self, connection_id: str, message_size: int = 1) -> Tuple[bool, Optional[float]]:
        """
        Check if connection can send a message using token bucket algorithm.
        Returns (allowed, retry_after_seconds).
        """
        if connection_id not in self.message_buckets:
            return False, None
        
        bucket = self.message_buckets[connection_id]
        now = time.time()
        
        # Refill tokens based on time elapsed
        time_elapsed = now - bucket['last_refill']
        tokens_to_add = time_elapsed * self.max_messages_per_second
        bucket['tokens'] = min(self.burst_size, bucket['tokens'] + tokens_to_add)
        bucket['last_refill'] = now
        
        # Check if we have enough tokens
        if bucket['tokens'] >= message_size:
            bucket['tokens'] -= message_size
            return True, None
        
        # Calculate retry after
        tokens_needed = message_size - bucket['tokens']
        retry_after = tokens_needed / self.max_messages_per_second
        
        # Add jitter (0-0.5 seconds)
        retry_after += random.random() * 0.5
        
        return False, retry_after
    
    def can_attempt_pairing(self, ip: str) -> Tuple[bool, Optional[int]]:
        """Check if IP can attempt pairing."""
        now = time.time()
        attempts = self.pairing_attempts[ip]
        
        # Remove old attempts outside the window
        while attempts and attempts[0] < now - self.pairing_window_seconds:
            attempts.popleft()
        
        # Check if limit exceeded
        if len(attempts) >= self.max_pairing_attempts:
            retry_after = int(attempts[0] + self.pairing_window_seconds - now)
            retry_after += random.randint(0, 3)  # Add jitter
            return False, max(0, retry_after)
        
        # Record this attempt
        attempts.append(now)
        return True, None
    
    def check_channel_rate(self, channel_id: str, max_messages: int = 100, window: int = 10) -> bool:
        """Check if channel message rate is within limits."""
        now = time.time()
        messages = self.channel_message_rates[channel_id]
        
        # Remove old messages outside the window
        while messages and messages[0] < now - window:
            messages.popleft()
        
        # Check if limit exceeded
        if len(messages) >= max_messages:
            return False
        
        # Record this message
        messages.append(now)
        return True
    
    def get_stats(self) -> dict:
        """Get current rate limiter statistics."""
        return {
            'total_ips': len(self.connections_per_ip),
            'total_connections': sum(len(conns) for conns in self.connections_per_ip.values()),
            'connections_by_ip': {
                ip: len(conns) for ip, conns in self.connections_per_ip.items()
            },
            'active_channels': len(self.channel_message_rates)
        }


class MessageSizeLimiter:
    """Enforces message size limits based on content type."""
    
    # Size limits in bytes
    TEXT_MESSAGE_LIMIT = 10 * 1024              # 10KB for text messages
    AUDIO_CHUNK_LIMIT = 1024 * 1024             # 1MB for streaming audio chunks
    AUDIO_FILE_LIMIT = 100 * 1024 * 1024        # 100MB for complete audio files
    BINARY_MESSAGE_LIMIT = 50 * 1024 * 1024     # 50MB for binary data/file uploads
    
    @classmethod
    def check_size(cls, message: bytes, content_type: str = 'text', is_file_upload: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Check if message size is within limits.
        Returns (allowed, error_message).
        """
        message_size = len(message)
        
        # Different limits for streaming vs file uploads
        if content_type == 'audio':
            limit = cls.AUDIO_FILE_LIMIT if is_file_upload else cls.AUDIO_CHUNK_LIMIT
        elif content_type == 'binary':
            limit = cls.BINARY_MESSAGE_LIMIT
        else:
            limit = cls.TEXT_MESSAGE_LIMIT
        
        if message_size > limit:
            limit_mb = limit / (1024 * 1024)
            size_mb = message_size / (1024 * 1024)
            return False, f"Message size {size_mb:.1f}MB exceeds {content_type} {'file' if is_file_upload else 'chunk'} limit of {limit_mb:.1f}MB"
        
        return True, None
    
    @classmethod
    def get_content_type(cls, message: dict) -> Tuple[str, bool]:
        """
        Determine content type and whether it's a file upload from message.
        Returns (content_type, is_file_upload).
        """
        msg_type = message.get('type', '')
        
        # Audio file uploads (complete files)
        if msg_type in ['audio_file', 'audio_upload', 'consultation_audio']:
            return 'audio', True
        
        # Audio streaming chunks
        if msg_type in ['audio_chunk', 'audio_data', 'audio_stream']:
            return 'audio', False
        
        # Binary data types
        if msg_type in ['file_upload', 'binary_data', 'image']:
            return 'binary', True
        
        # Default to text
        return 'text', False


class ConnectionTracker:
    """Tracks connection metadata and patterns for security monitoring."""
    
    def __init__(self):
        self.connection_metadata: Dict[str, dict] = {}
        self.suspicious_patterns: Dict[str, list] = defaultdict(list)
    
    def track_connection(self, connection_id: str, ip: str, user_agent: str = None, origin: str = None):
        """Track new connection metadata."""
        self.connection_metadata[connection_id] = {
            'ip': ip,
            'user_agent': user_agent,
            'origin': origin,
            'connected_at': datetime.utcnow(),
            'message_count': 0,
            'last_message_at': None,
            'channels': set()
        }
    
    def track_message(self, connection_id: str):
        """Track message from connection."""
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]['message_count'] += 1
            self.connection_metadata[connection_id]['last_message_at'] = datetime.utcnow()
    
    def track_channel_join(self, connection_id: str, channel_id: str):
        """Track channel join."""
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]['channels'].add(channel_id)
    
    def track_suspicious_activity(self, ip: str, activity_type: str, details: str = None):
        """Track suspicious activity for security monitoring."""
        self.suspicious_patterns[ip].append({
            'type': activity_type,
            'details': details,
            'timestamp': datetime.utcnow()
        })
        
        # Keep only last 100 activities per IP
        if len(self.suspicious_patterns[ip]) > 100:
            self.suspicious_patterns[ip] = self.suspicious_patterns[ip][-100:]
    
    def get_connection_info(self, connection_id: str) -> Optional[dict]:
        """Get connection metadata."""
        return self.connection_metadata.get(connection_id)
    
    def cleanup_old_connections(self, max_age_hours: int = 24):
        """Remove old connection metadata."""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        to_remove = [
            conn_id for conn_id, metadata in self.connection_metadata.items()
            if metadata['connected_at'] < cutoff
        ]
        
        for conn_id in to_remove:
            del self.connection_metadata[conn_id]
        
        return len(to_remove)