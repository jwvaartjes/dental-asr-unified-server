"""
Security module for pairing functionality.
Handles JWT tokens, origin validation, and rate limiting.
"""
import os
import jwt
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import HTTPException, status, Request, WebSocket

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "test-secret-key-for-local-testing")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "8"))


class JWTHandler:
    """Handle JWT token generation and validation."""
    
    @staticmethod
    def generate_token(user_id: str, device_type: str = "desktop") -> str:
        """Generate a JWT token for authentication."""
        payload = {
            "user": user_id,
            "device_type": device_type,
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def generate_mobile_token(pair_code: str) -> str:
        """Generate a short-lived token for mobile pairing."""
        payload = {
            "device": "mobile",
            "pair_code": pair_code,
            "exp": datetime.utcnow() + timedelta(minutes=5)
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None


class OriginValidator:
    """Validate request origins for CORS security."""

    def __init__(self, allowed_origins: List[str]):
        self.allowed_origins = allowed_origins
        # Same regex pattern as CORS middleware in main.py
        self.allowed_origin_regex = re.compile(
            r"https://.*\.lovable\.app|https://.*\.lovable\.dev|https://.*\.lovableproject\.com|https://.*\.ngrok\.app|https://.*\.ngrok\.io|https://.*\.mondplan\.com"
        )

    def validate_http_origin(self, request: Request) -> bool:
        """Validate HTTP request origin."""
        origin = request.headers.get("origin", "")
        return self._is_allowed(origin)

    def validate_websocket_origin(self, websocket: WebSocket) -> bool:
        """Validate WebSocket connection origin."""
        origin = websocket.headers.get("origin", "")
        return self._is_allowed(origin)

    def _is_allowed(self, origin: str) -> bool:
        """Check if origin is in allowed list or matches regex patterns."""
        if not origin:
            return "null" in self.allowed_origins

        # Check exact match or prefix match with allowed origins list
        exact_or_prefix_match = any(
            origin == allowed or origin.startswith(allowed)
            for allowed in self.allowed_origins
        )

        # Check regex pattern match (same as CORS middleware)
        regex_match = bool(self.allowed_origin_regex.match(origin))

        return exact_or_prefix_match or regex_match


class SecurityMiddleware:
    """Security middleware for pairing operations."""
    
    def __init__(self, origin_validator: OriginValidator, http_rate_limiter=None, ws_rate_limiter=None):
        self.origin_validator = origin_validator
        self.http_rate_limiter = http_rate_limiter
        self.ws_rate_limiter = ws_rate_limiter
    
    async def validate_request(self, request: Request):
        """Validate incoming HTTP request."""
        # Check origin
        if not self.origin_validator.validate_http_origin(request):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Origin not allowed"
            )
        
        # Check HTTP rate limit if available
        if self.http_rate_limiter:
            client_ip = get_client_ip(request=request)
            
            # Handle RateLimiter (HTTP rate limiter)
            if hasattr(self.http_rate_limiter, 'is_allowed'):
                if not self.http_rate_limiter.is_allowed(client_ip):
                    retry_after = getattr(self.http_rate_limiter, 'get_retry_after', lambda x: 60)(client_ip)
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded",
                        headers={"Retry-After": str(retry_after)}
                    )
            # Handle WebSocketRateLimiter incorrectly passed as http_rate_limiter
            elif hasattr(self.http_rate_limiter, 'can_connect'):
                logger.warning("WebSocketRateLimiter passed as http_rate_limiter - skipping HTTP rate limiting")
            else:
                logger.warning(f"HTTP rate limiter does not support expected methods: {type(self.http_rate_limiter)}")
    
    async def validate_websocket(self, websocket: WebSocket) -> tuple[bool, Optional[str]]:
        """Validate incoming WebSocket connection."""
        # Check origin
        if not self.origin_validator.validate_websocket_origin(websocket):
            return False, "Unauthorized origin"
        
        # Check WebSocket connection limit if rate limiter available
        if self.ws_rate_limiter:
            client_ip = get_client_ip(websocket=websocket)
            
            try:
                # Handle WebSocketRateLimiter (correct type for WebSocket connections)
                if hasattr(self.ws_rate_limiter, 'can_connect'):
                    client_id = f"client_{id(websocket)}"
                    can_connect, reason = self.ws_rate_limiter.can_connect(client_ip, client_id)
                    if not can_connect:
                        return False, reason
                # Handle RateLimiter incorrectly passed as ws_rate_limiter
                elif hasattr(self.ws_rate_limiter, 'is_allowed'):
                    logger.warning("RateLimiter passed as ws_rate_limiter - using HTTP rate limiting for WebSocket")
                    if not self.ws_rate_limiter.is_allowed(client_ip):
                        return False, "WebSocket connection rate limited"
                else:
                    logger.warning(f"WebSocket rate limiter does not support expected methods: {type(self.ws_rate_limiter)}")
            except Exception as e:
                # Log error but don't block connection
                logger.warning(f"WebSocket rate limiter error: {e}")
        
        return True, None
    
    def handle_bearer_token(self, websocket: WebSocket) -> Optional[str]:
        """Extract and validate Bearer token from WebSocket subprotocol."""
        subprotocols = websocket.headers.get("sec-websocket-protocol", "")
        
        if subprotocols and subprotocols.startswith("Bearer."):
            token = subprotocols.replace("Bearer.", "")
            payload = JWTHandler.verify_token(token)
            
            if payload:
                logger.info(f"WebSocket authenticated for user: {payload.get('user')}")
                return subprotocols  # Return to accept with subprotocol
            else:
                logger.warning("Invalid Bearer token in WebSocket subprotocol")
        
        return None


def get_client_ip(request: Request = None, websocket: WebSocket = None) -> str:
    """Extract client IP from request or websocket, handling proxy headers."""
    # Try to get IP from X-Forwarded-For header first (for proxies/load balancers)
    if request:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, use the first one
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct client IP
        if request.client:
            return request.client.host
    elif websocket:
        forwarded_for = websocket.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = websocket.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct client IP
        if websocket.client:
            return websocket.client.host
    
    return "127.0.0.1"