"""
Authentication response handler for httpOnly cookies.
"""
from fastapi import Response
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class AuthResponseHandler:
    """Handle auth responses with httpOnly cookies."""

    @staticmethod
    def create_cookie_auth_response(
        response: Response,
        token: str,
        user_data: Dict[str, Any],
        request=None
    ) -> Dict[str, Any]:
        """Create cookie-based auth response for web browsers."""

        # Determine if we're behind ngrok proxy by checking headers
        cookie_domain = None
        if request:
            # Check for ngrok forwarded headers
            forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
            if forwarded_host and "ngrok" in forwarded_host:
                cookie_domain = forwarded_host
                logger.info(f"Setting cookie for ngrok domain: {cookie_domain}")

        # Set secure httpOnly cookie for desktop browsers only
        cookie_params = {
            "key": "session_token",
            "value": token,
            "httponly": True,              # XSS protection
            "secure": True,                # Required for HTTPS (ngrok)
            "max_age": 8 * 60 * 60,       # 8 hours
            "path": "/",                   # Available for all routes
        }

        # Simplified logic - treat all browsers the same for ngrok
        if cookie_domain:
            # For ALL browsers with ngrok: use none with domain
            cookie_params["samesite"] = "none"
            cookie_params["domain"] = cookie_domain
        else:
            # Local development: use lax
            cookie_params["samesite"] = "lax"

        response.set_cookie(**cookie_params)

        logger.info(f"HttpOnly cookie set for user {user_data.get('email')}")

        # Return user data WITHOUT token
        return {
            "success": True,
            "user": user_data,
            "auth_method": "cookie",
            "expires_in": 8 * 60 * 60,
        }

    @staticmethod
    def clear_auth_cookie(response: Response, request=None) -> None:
        """Clear authentication cookie."""

        # Determine if we're behind ngrok proxy by checking headers
        cookie_domain = None
        if request:
            # Check for ngrok forwarded headers
            forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
            if forwarded_host and "ngrok" in forwarded_host:
                cookie_domain = forwarded_host
                logger.info(f"Clearing cookie for ngrok domain: {cookie_domain}")

        # Clear with domain if needed
        delete_params = {
            "key": "session_token",
            "path": "/",
            "secure": True,   # Match the original cookie settings
            "samesite": "none"  # Match the updated cookie settings
        }

        if cookie_domain:
            delete_params["domain"] = cookie_domain

        response.delete_cookie(**delete_params)
        logger.info("Auth cookie cleared")