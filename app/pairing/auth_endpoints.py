"""
Clean auth endpoints with httpOnly cookies - no fallbacks.
"""
import json
import logging
from fastapi import APIRouter, Request, Response, Depends, HTTPException, status
from .security import SecurityMiddleware
from .auth_response import AuthResponseHandler
from .auth_dependencies import RequireAuth, is_mobile_device

logger = logging.getLogger(__name__)

# Create auth router
auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

def get_security_middleware(request: Request) -> SecurityMiddleware:
    """Dependency to get security middleware from app state."""
    return request.app.state.security_middleware


@auth_router.post("/login")
async def login(
    request: Request,
    response: Response,
    security: SecurityMiddleware = Depends(get_security_middleware)
):
    """Regular login endpoint with httpOnly cookies."""
    await security.validate_request(request)

    try:
        # Import here to avoid circular imports
        from app.users.auth import user_auth

        # Handle JSON parsing explicitly
        try:
            data = await request.json()
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"Malformed JSON in login request: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON format")

        email = data.get("email", data.get("username", ""))
        password = data.get("password", "")

        if not email:
            raise HTTPException(status_code=400, detail="Email is required")

        logger.info(f"Login attempt for: {email}")

        # Validate against real user database
        user = await user_auth.validate_user_credentials(email, password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Generate token and user data
        token = user_auth.generate_token(user)
        user_data = {
            "id": user.id,
            "email": user.email,
            "name": user.name or (email.split("@")[0] if "@" in email else email),
            "role": user.role,
            "permissions": user.permissions.dict()
        }

        # Check if request is from mobile device
        if is_mobile_device(request):
            # Mobile devices get Bearer token response (no cookie)
            logger.info(f"Mobile login for user: {email}")
            return {
                "success": True,
                "user": user_data,
                "token": token,
                "auth_method": "bearer",
                "expires_in": 8 * 60 * 60,
            }
        else:
            # Desktop gets httpOnly cookie response
            logger.info(f"Desktop login for user: {email}")
            return AuthResponseHandler.create_cookie_auth_response(
                response, token, user_data, request
            )

    except HTTPException:
        # Re-raise HTTP exceptions (400, 401, etc.)
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")


@auth_router.post("/login-magic")
async def login_magic(
    request: Request,
    response: Response,
    security: SecurityMiddleware = Depends(get_security_middleware)
):
    """Magic link login with httpOnly cookies."""
    await security.validate_request(request)

    try:
        # Import here to avoid circular imports
        from app.users.auth import user_auth

        data = await request.json()
        email = data.get("email", "")

        if not email or "@" not in email:
            raise HTTPException(status_code=400, detail="Valid email is required")

        logger.info(f"Magic login attempt for: {email}")

        # Get user from database
        user = await user_auth.get_user_by_email(email)
        if not user or user.status != "active":
            raise HTTPException(status_code=401, detail="User not found or inactive")

        # 🚨 CRITICAL SECURITY: Block magic login for admin/super_admin accounts
        if user.role in ["admin", "super_admin"]:
            logger.warning(f"🚨 SECURITY: Magic login blocked for admin account: {email}")
            raise HTTPException(
                status_code=403,
                detail="Admin accounts must use password authentication for security"
            )

        # Generate token and user data
        token = user_auth.generate_token(user)
        user_data = {
            "id": user.id,
            "email": user.email,
            "name": user.name or email.split("@")[0],
            "role": user.role,
            "permissions": user.permissions.dict()
        }

        # Check if request is from mobile device
        if is_mobile_device(request):
            # Mobile devices get Bearer token response (no cookie)
            logger.info(f"Mobile magic login for user: {email}")
            return {
                "success": True,
                "user": user_data,
                "token": token,
                "auth_method": "bearer",
                "expires_in": 8 * 60 * 60,
            }
        else:
            # Desktop gets httpOnly cookie response
            logger.info(f"Desktop magic login for user: {email}")
            return AuthResponseHandler.create_cookie_auth_response(
                response, token, user_data, request
            )

    except Exception as e:
        logger.error(f"Magic login error: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="Magic login failed")


@auth_router.get("/status")
async def auth_status(current_user: dict = RequireAuth):
    """Check authentication status and return full user data."""
    try:
        # Import here to avoid circular imports
        from app.users.auth import user_auth

        # Get user email from token
        user_email = current_user["user"]

        # Fetch full user data from database
        user = await user_auth.get_user_by_email(user_email)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # Return complete user data (same format as login)
        user_data = {
            "id": user.id,
            "email": user.email,
            "name": user.name or (user.email.split("@")[0] if "@" in user.email else user.email),
            "role": user.role,
            "permissions": user.permissions.dict()
        }

        return {
            "authenticated": True,
            "user": user_data
        }

    except Exception as e:
        logger.error(f"Status check error: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="Failed to get user status")

@auth_router.get("/token-status")
async def token_status(request: Request):
    """Check token validity and expiration status."""
    from datetime import datetime
    from ..pairing.security import JWTHandler
    
    try:
        # Try to get token from different sources
        token = None
        
        # First try Authorization header
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
        
        # Fallback: try httpOnly cookie
        if not token:
            token = request.cookies.get("session_token")
        
        # No token found
        if not token:
            return {
                "valid": False,
                "expired": False,
                "reason": "no_token",
                "action_required": "login"
            }
        
        # Verify token
        payload = JWTHandler.verify_token(token)
        if not payload:
            return {
                "valid": False,
                "expired": True,
                "reason": "token_expired",
                "action_required": "logout"
            }
        
        # Token is valid - calculate expiration info
        exp_timestamp = payload.get("exp", 0)
        current_timestamp = datetime.utcnow().timestamp()
        time_until_expiry = exp_timestamp - current_timestamp
        
        # Check if token expires soon (30 minutes = 1800 seconds)
        should_refresh_soon = time_until_expiry < 1800
        
        return {
            "valid": True,
            "expired": False,
            "authenticated": True,
            "expires_at": datetime.fromtimestamp(exp_timestamp).isoformat() + "Z",
            "time_until_expiry_seconds": int(time_until_expiry),
            "time_until_expiry_minutes": int(time_until_expiry / 60),
            "should_refresh_soon": should_refresh_soon,
            "action_required": "none"
        }
        
    except Exception as e:
        logger.error(f"Token status check error: {e}")
        return {
            "valid": False,
            "expired": True,
            "reason": "token_validation_error",
            "action_required": "logout",
            "error": str(e)
        }

@auth_router.get("/session-info")
async def session_info(request: Request):
    """Detailed session information with user-friendly messaging for frontend."""
    from datetime import datetime, timedelta
    from ..pairing.security import JWTHandler
    
    try:
        # Try to get token from different sources
        token = None
        token_source = "none"
        
        # First try Authorization header
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            token_source = "bearer_header"
        
        # Fallback: try httpOnly cookie
        if not token:
            token = request.cookies.get("session_token")
            if token:
                token_source = "httponly_cookie"
        
        # No token found - provide clear guidance
        if not token:
            return {
                "authenticated": False,
                "session_status": "no_session",
                "token_source": "none",
                "message": "No authentication session found. Please log in.",
                "action_required": "login",
                "login_url": "/login",
                "can_refresh": False
            }
        
        # Verify token
        payload = JWTHandler.verify_token(token)
        if not payload:
            return {
                "authenticated": False,
                "session_status": "expired",
                "token_source": token_source,
                "message": "Your session has expired. Please log in again.",
                "action_required": "logout_and_login", 
                "login_url": "/login",
                "can_refresh": False
            }
        
        # Token is valid - calculate detailed expiration info
        exp_timestamp = payload.get("exp", 0)
        iat_timestamp = payload.get("iat", 0)
        current_timestamp = datetime.utcnow().timestamp()
        
        time_until_expiry = exp_timestamp - current_timestamp
        session_age = current_timestamp - iat_timestamp
        session_duration_hours = (exp_timestamp - iat_timestamp) / 3600
        
        # Determine session health and recommendations
        expires_soon = time_until_expiry < 1800  # 30 minutes
        expires_very_soon = time_until_expiry < 300  # 5 minutes
        
        if expires_very_soon:
            session_status = "expires_very_soon"
            message = f"Session expires in {int(time_until_expiry/60)} minutes. Please save your work."
            action_required = "refresh_soon"
        elif expires_soon:
            session_status = "expires_soon"
            message = f"Session expires in {int(time_until_expiry/60)} minutes."
            action_required = "refresh_recommended"
        else:
            session_status = "active"
            message = f"Session active. Expires in {int(time_until_expiry/60)} minutes."
            action_required = "none"
        
        return {
            "authenticated": True,
            "session_status": session_status,
            "token_source": token_source,
            "message": message,
            "action_required": action_required,
            "session_info": {
                "expires_at": datetime.fromtimestamp(exp_timestamp).isoformat() + "Z",
                "issued_at": datetime.fromtimestamp(iat_timestamp).isoformat() + "Z",
                "time_until_expiry_seconds": int(time_until_expiry),
                "time_until_expiry_minutes": int(time_until_expiry / 60),
                "session_age_minutes": int(session_age / 60),
                "session_duration_hours": round(session_duration_hours, 1),
                "expires_soon": expires_soon,
                "expires_very_soon": expires_very_soon
            },
            "can_refresh": True,  # Sessions can potentially be refreshed
            "user_email": payload.get("email") or payload.get("user")
        }
        
    except Exception as e:
        logger.error(f"Session info check error: {e}")
        return {
            "authenticated": False,
            "session_status": "error", 
            "token_source": "unknown",
            "message": "Unable to check session status. Please try logging in again.",
            "action_required": "login",
            "login_url": "/login",
            "can_refresh": False,
            "error": str(e)
        }

@auth_router.post("/refresh-session")
async def refresh_session(
    request: Request,
    response: Response,
    current_user: dict = RequireAuth
):
    """Refresh session by issuing a new token with extended expiry."""
    from datetime import datetime, timedelta
    from ..pairing.security import JWTHandler
    from .auth_response import AuthResponseHandler
    
    try:
        # Import here to avoid circular imports
        from app.users.auth import user_auth

        # Get user email from current authenticated session
        user_email = current_user["user"]

        # Fetch full user data from database to ensure user is still active
        user = await user_auth.get_user_by_email(user_email)
        if not user or user.status != "active":
            raise HTTPException(
                status_code=401, 
                detail="User not found or inactive. Please log in again."
            )

        # Generate new token with extended expiry
        new_token = user_auth.generate_token(user)
        user_data = {
            "id": user.id,
            "email": user.email,
            "name": user.name or (user.email.split("@")[0] if "@" in user.email else user.email),
            "role": user.role,
            "permissions": user.permissions.dict()
        }

        # Check if request is from mobile device
        if is_mobile_device(request):
            # Mobile devices get Bearer token response
            logger.info(f"Session refresh for mobile user: {user_email}")
            return {
                "success": True,
                "refreshed": True,
                "message": "Session refreshed successfully",
                "user": user_data,
                "token": new_token,
                "auth_method": "bearer",
                "expires_in": 8 * 60 * 60,  # 8 hours
                "refresh_reason": "user_requested"
            }
        else:
            # Desktop gets new httpOnly cookie
            logger.info(f"Session refresh for desktop user: {user_email}")

            # Create refreshed cookie response
            cookie_response = AuthResponseHandler.create_cookie_auth_response(
                response, new_token, user_data, request
            )

            # Add refresh-specific fields
            cookie_response.update({
                "refreshed": True,
                "message": "Session refreshed successfully",
                "refresh_reason": "user_requested"
            })

            return cookie_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session refresh error: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to refresh session. Please log in again."
        )


@auth_router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: dict = RequireAuth
):
    """Logout with proper session clearing."""
    user_email = current_user["user"]
    is_mobile = is_mobile_device(request)

    # Clear auth cookies with proper configurations
    cookie_names = ["session_token", "auth_token", "access_token", "pairing_token"]

    for cookie_name in cookie_names:
        # Clear with the settings that match our login cookies
        try:
            response.delete_cookie(
                key=cookie_name,
                path="/",
                secure=True,
                samesite="none"
            )
            # Also clear for local development (non-secure)
            response.delete_cookie(
                key=cookie_name,
                path="/",
                secure=False,
                samesite="lax"
            )
        except Exception:
            # Continue if cookie deletion fails
            pass

    # Add reasonable cache busting headers (without Clear-Site-Data)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    logger.info(f"Logout completed for {user_email} ({'mobile' if is_mobile else 'desktop'})")

    return {
        "success": True,
        "message": "Logged out successfully",
        "device_type": "mobile" if is_mobile else "desktop",
        "cleared_cookies": cookie_names
    }


@auth_router.get("/verify")
async def verify_token(current_user: dict = RequireAuth):
    """Verify token (works with both cookies and headers)."""
    return {
        "valid": True,
        "user": current_user["user"]
    }


@auth_router.get("/check-email")
async def check_email(
    email: str,
    request: Request,
    security: SecurityMiddleware = Depends(get_security_middleware)
):
    """Check if email exists in database."""
    await security.validate_request(request)

    try:
        # Import here to avoid circular imports
        from app.users.auth import user_auth

        # Get user from database with full info
        user = await user_auth.get_user_by_email(email)
        exists = user is not None

        # Return actual role from database (not pattern matching!)
        user_role = user.role if user else None
        is_admin = user_role in ["admin", "super_admin"] if user_role else False

        return {
            "exists": exists,
            "role": user_role,  # ✅ Include actual role for frontend!
            "is_admin": is_admin,  # ✅ Based on real role, not pattern matching
            "message": f"Email {email} {'exists' if exists else 'not found'}"
        }
    except Exception as e:
        logger.error(f"Email check failed for {email}: {e}")
        # Return safe fallback response
        return {
            "exists": False,
            "role": None,  # ✅ Consistent with success response
            "is_admin": False,
            "message": "Unable to check email"
        }


@auth_router.post("/ws-token")
async def get_ws_token(
    request: Request,
    security: SecurityMiddleware = Depends(get_security_middleware),
    current_user: dict = RequireAuth
):
    """Generate WebSocket authentication token for desktop."""
    await security.validate_request(request)

    # Import here to avoid circular imports
    from .security import JWTHandler

    try:
        # Get user email from authenticated session
        user_email = current_user["user"]

        # Generate WebSocket token using email as user_id
        token = JWTHandler.generate_token(user_email, device_type="desktop")

        logger.info(f"Generated WebSocket token for user: {user_email}")

        return {
            "token": token,
            "expires_in": 120,
            "user": user_email
        }

    except Exception as e:
        logger.error(f"WebSocket token generation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate WebSocket token")


@auth_router.post("/ws-token-mobile")
async def get_ws_token_mobile(
    request: Request,
    security: SecurityMiddleware = Depends(get_security_middleware)
):
    """Generate WebSocket token for mobile - inherits desktop auth if paired."""
    await security.validate_request(request)

    # Import here to avoid circular imports
    from .security import JWTHandler

    try:
        data = await request.json()
        pair_code = data.get("pair_code", "")

        if not pair_code:
            raise HTTPException(status_code=400, detail="pair_code is required")

        # Get pairing service to check for paired desktop
        pairing_service = request.app.state.pairing_service

        # Try to inherit desktop auth through pairing
        if pairing_service.store:
            try:
                pairing_data = await pairing_service.store.get_pairing_with_auth(pair_code)
                if pairing_data and pairing_data.get("auth_info"):
                    # Found desktop auth info - inherit it!
                    desktop_auth = pairing_data["auth_info"]
                    inherited_user = desktop_auth.get("username", f"mobile_user_{pair_code}")
                    logger.info(f"Mobile inheriting auth from desktop: {inherited_user}")

                    # Generate token with inherited auth
                    token = JWTHandler.generate_token(inherited_user, device_type="mobile")
                    return {
                        "token": token,
                        "expires_in": 120,
                        "inherited_from": inherited_user,
                        "pair_code": pair_code
                    }
            except Exception as e:
                logger.warning(f"Failed to check pairing auth: {e}")

        # Fallback: generate token for mobile without inheritance
        fallback_user = f"mobile_user_{pair_code}"
        token = JWTHandler.generate_token(fallback_user, device_type="mobile")

        logger.info(f"Generated fallback WebSocket token for mobile: {fallback_user}")

        return {
            "token": token,
            "expires_in": 120,
            "user": fallback_user,
            "pair_code": pair_code,
            "inherited": False
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mobile WebSocket token generation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate mobile WebSocket token")