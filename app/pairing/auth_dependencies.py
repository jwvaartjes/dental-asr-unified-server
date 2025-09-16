"""
Authentication dependencies for httpOnly cookies.
"""
from fastapi import Request, HTTPException, status, Depends
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

def is_mobile_device(request: Request) -> bool:
    """Detect if request comes from a mobile device."""
    user_agent = request.headers.get("user-agent", "").lower()
    mobile_indicators = [
        "mobile", "android", "iphone", "ipad", "ipod",
        "blackberry", "windows phone", "opera mini"
    ]
    return any(indicator in user_agent for indicator in mobile_indicators)

async def get_auth_token_from_request(request: Request) -> Optional[str]:
    """Extract auth token from request (cookie first, then header fallback)."""

    # Check if request is from mobile device
    is_mobile = is_mobile_device(request)

    # Try cookie first (web browsers) - but NOT for mobile devices
    cookie_token = request.cookies.get("session_token")
    if cookie_token:
        if is_mobile:
            logger.warning("Mobile device attempted to use desktop cookie - blocking")
            # Mobile devices should use Bearer tokens, not cookies
            cookie_token = None
        else:
            logger.debug("Auth token found in cookie (desktop)")
            return cookie_token

    # Try Authorization header (for API clients and mobile)
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
        logger.debug(f"Auth token found in Authorization header ({'mobile' if is_mobile else 'api client'})")
        return token

    logger.debug(f"No auth token found in request ({'mobile' if is_mobile else 'desktop'})")
    return None

async def get_current_user(request: Request) -> Dict[str, Any]:
    """Get current user from auth token (cookie or header)."""
    from .security import JWTHandler

    token = await get_auth_token_from_request(request)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token provided"
        )

    # Verify token
    payload = JWTHandler.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    # Handle both token formats:
    # - Login tokens: {"user_id": "...", "email": "..."}
    # - WebSocket tokens: {"user": "..."}
    user_identifier = payload.get("user") or payload.get("email") or payload.get("user_id")

    return {
        "user": user_identifier,
        "token": token
    }

# Convenience dependency for routes that require auth
RequireAuth = Depends(get_current_user)