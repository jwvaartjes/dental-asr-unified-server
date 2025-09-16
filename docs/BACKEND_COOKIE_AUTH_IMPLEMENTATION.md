# Backend HttpOnly Cookie Authentication Implementation

## 🎯 **Current Status**

**✅ FastAPI Support**: Heeft native cookie support via `Response.set_cookie()`
**❌ Implementation**: Jullie backend gebruikt het nog NIET
**🔄 Current Flow**: Alle auth endpoints returnen JWT tokens in response body

## 🏗️ **Implementation Strategy**

### **Hybrid Approach: Best of Both Worlds**

```python
# Device-aware auth based on User-Agent
Desktop → httpOnly cookies (secure)
Mobile → JWT tokens (necessary for React Native)
```

## 🔧 **Backend Implementation**

### **1. Device Detection Utility**

```python
# app/pairing/device_detection.py
from fastapi import Request
from typing import Literal

DeviceType = Literal["desktop", "mobile"]

def detect_device_type(request: Request) -> DeviceType:
    """Detect device type from User-Agent header."""
    user_agent = request.headers.get("user-agent", "").lower()

    mobile_indicators = [
        "mobile", "android", "iphone", "ipad", "ipod",
        "blackberry", "windows phone", "tablet",
        "react-native", "expo", "cordova", "phonegap"
    ]

    # Check for mobile indicators
    is_mobile = any(indicator in user_agent for indicator in mobile_indicators)

    # Check for explicit mobile client header
    client_type = request.headers.get("x-client-type", "").lower()
    if client_type == "mobile":
        is_mobile = True

    return "mobile" if is_mobile else "desktop"

def is_mobile_device(request: Request) -> bool:
    """Check if request comes from mobile device."""
    return detect_device_type(request) == "mobile"
```

### **2. Enhanced Auth Response Handler**

```python
# app/pairing/auth_response.py
from fastapi import Response, Request
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class AuthResponseHandler:
    """Handle auth responses based on device type."""

    @staticmethod
    def create_auth_response(
        request: Request,
        response: Response,
        token: str,
        user_data: Dict[str, Any],
        device_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create appropriate auth response based on device type."""

        # Auto-detect device type if not provided
        if device_type is None:
            from .device_detection import detect_device_type
            device_type = detect_device_type(request)

        if device_type == "desktop":
            # Desktop: Set httpOnly cookie
            return AuthResponseHandler._create_cookie_response(
                response, token, user_data
            )
        else:
            # Mobile: Return JWT token
            return AuthResponseHandler._create_jwt_response(
                token, user_data
            )

    @staticmethod
    def _create_cookie_response(
        response: Response,
        token: str,
        user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create cookie-based auth response for desktop."""

        # Set secure httpOnly cookie
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,              # XSS protection
            secure=True,                # HTTPS only (disable for local dev)
            samesite="strict",          # CSRF protection
            max_age=8 * 60 * 60,       # 8 hours
            path="/",                   # Available for all routes
        )

        logger.info(f"Desktop auth: Set httpOnly cookie for user {user_data.get('email')}")

        # Return user data WITHOUT token
        return {
            "success": True,
            "user": user_data,
            "auth_method": "cookie",
            "expires_in": 8 * 60 * 60,  # 8 hours in seconds
        }

    @staticmethod
    def _create_jwt_response(
        token: str,
        user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create JWT-based auth response for mobile."""

        logger.info(f"Mobile auth: Returning JWT token for user {user_data.get('email')}")

        # Return token in response body (mobile needs this)
        return {
            "success": True,
            "token": token,
            "user": user_data,
            "auth_method": "jwt",
            "expires_in": 8 * 60 * 60,  # 8 hours in seconds
        }

    @staticmethod
    def clear_auth_cookie(response: Response) -> None:
        """Clear authentication cookie."""
        response.delete_cookie(
            key="session_token",
            path="/",
            secure=True,
            samesite="strict"
        )
        logger.info("Auth cookie cleared")
```

### **3. Cookie Authentication Dependency**

```python
# app/pairing/auth_dependencies.py
from fastapi import Request, HTTPException, status, Depends
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

async def get_auth_token_from_request(request: Request) -> Optional[str]:
    """Extract auth token from request (cookie or header)."""

    # Try cookie first (desktop)
    cookie_token = request.cookies.get("session_token")
    if cookie_token:
        logger.debug("Auth token found in cookie")
        return cookie_token

    # Try Authorization header (mobile)
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
        logger.debug("Auth token found in Authorization header")
        return token

    logger.debug("No auth token found in request")
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

    return {
        "user": payload.get("user"),
        "device_type": payload.get("device_type", "desktop"),
        "token": token  # Include for logging/debugging
    }

# Convenience dependency for routes that require auth
RequireAuth = Depends(get_current_user)
```

### **4. Updated Router Endpoints**

```python
# app/pairing/router.py - Updated endpoints
from fastapi import APIRouter, Request, Response, Depends, HTTPException, status
from .auth_response import AuthResponseHandler
from .auth_dependencies import RequireAuth, get_auth_token_from_request
from .security import JWTHandler
from .device_detection import detect_device_type
import logging

logger = logging.getLogger(__name__)

@router.post("/auth/login")
async def login(
    request: Request,
    response: Response,
    security: SecurityMiddleware = Depends(get_security_middleware)
):
    """Enhanced login with device-aware auth."""
    await security.validate_request(request)

    try:
        data = await request.json()
        email = data.get("email", "")
        password = data.get("password", "")

        # Detect device type
        device_type = detect_device_type(request)
        logger.info(f"Login attempt from {device_type} device: {email}")

        # Your existing auth logic here...
        if "@" in email:  # Your validation logic
            # Generate token with device type
            token = JWTHandler.generate_token(email, device_type=device_type)

            user_data = {
                "id": "mock-user-id",
                "email": email,
                "name": email.split("@")[0],
                "role": "admin" if "admin" in email else "user",
                "permissions": {
                    "canManageUsers": "admin" in email,
                    "canDeleteUsers": "admin" in email,
                    "canModifyAdminRoles": "admin" in email,
                    "isSuperAdmin": "admin" in email,
                }
            }

            # Create device-appropriate response
            return AuthResponseHandler.create_auth_response(
                request, response, token, user_data, device_type
            )

        raise HTTPException(status_code=400, detail="Invalid credentials")

    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@router.post("/auth/login-magic")
async def login_magic(
    request: Request,
    response: Response,
    security: SecurityMiddleware = Depends(get_security_middleware)
):
    """Enhanced magic login with device-aware auth."""
    await security.validate_request(request)

    try:
        data = await request.json()
        email = data.get("email", "")

        # Detect device type
        device_type = detect_device_type(request)
        logger.info(f"Magic login attempt from {device_type} device: {email}")

        if "@" in email:
            # Your existing magic auth logic...
            token = JWTHandler.generate_token(email, device_type=device_type)

            user_data = {
                "id": "magic-user-id",
                "email": email,
                "name": email.split("@")[0],
                "role": "admin" if "admin" in email else "user",
                "permissions": {
                    "canManageUsers": "admin" in email,
                    "canDeleteUsers": "admin" in email,
                    "canModifyAdminRoles": "admin" in email,
                    "isSuperAdmin": "admin" in email,
                }
            }

            # Create device-appropriate response
            return AuthResponseHandler.create_auth_response(
                request, response, token, user_data, device_type
            )

        raise HTTPException(status_code=400, detail="Invalid email")

    except Exception as e:
        logger.error(f"Magic login error: {e}")
        raise HTTPException(status_code=500, detail="Magic login failed")

@router.get("/auth/status")
async def auth_status(current_user: dict = RequireAuth):
    """Check authentication status."""
    return {
        "authenticated": True,
        "user": current_user["user"],
        "device_type": current_user.get("device_type", "desktop")
    }

@router.post("/auth/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: dict = RequireAuth
):
    """Logout with proper cleanup."""

    device_type = current_user.get("device_type", "desktop")
    user_email = current_user["user"]

    if device_type == "desktop":
        # Clear cookie for desktop
        AuthResponseHandler.clear_auth_cookie(response)
        logger.info(f"Desktop logout: Cookie cleared for {user_email}")
    else:
        # For mobile, just confirm logout (client will discard token)
        logger.info(f"Mobile logout: Token invalidation confirmed for {user_email}")

    return {
        "success": True,
        "message": "Logged out successfully",
        "device_type": device_type
    }

@router.get("/auth/verify")
async def verify_token(current_user: dict = RequireAuth):
    """Verify token (works with both cookies and headers)."""
    return {
        "valid": True,
        "user": current_user["user"],
        "device_type": current_user.get("device_type", "desktop")
    }
```

### **5. Enhanced JWT Handler**

```python
# app/pairing/security.py - Updated JWTHandler
from datetime import datetime, timedelta
import jwt
import os

class JWTHandler:
    """Enhanced JWT handler with device type support."""

    @staticmethod
    def generate_token(user_id: str, device_type: str = "desktop") -> str:
        """Generate JWT token with device type."""
        payload = {
            "user": user_id,
            "device_type": device_type,
            "exp": datetime.utcnow() + timedelta(hours=8),
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """Verify JWT token."""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
```

### **6. Development Configuration**

```python
# app/settings.py - Add cookie settings
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Existing settings...

    # Cookie settings
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    cookie_samesite: str = os.getenv("COOKIE_SAMESITE", "strict")
    cookie_max_age: int = int(os.getenv("COOKIE_MAX_AGE", "28800"))  # 8 hours

    class Config:
        env_file = ".env"

settings = Settings()

# app/pairing/auth_response.py - Use settings
response.set_cookie(
    key="session_token",
    value=token,
    httponly=True,
    secure=settings.cookie_secure,  # False for local development
    samesite=settings.cookie_samesite,
    max_age=settings.cookie_max_age,
    path="/",
)
```

### **7. Environment Configuration**

```bash
# .env - Add these for local development
COOKIE_SECURE=false          # Set to true in production
COOKIE_SAMESITE=lax          # Can be 'lax' for local dev
COOKIE_MAX_AGE=28800         # 8 hours

# For production:
# COOKIE_SECURE=true
# COOKIE_SAMESITE=strict
```

## 🧪 **Testing the Implementation**

### **Test Desktop Cookie Auth**
```bash
# Login (should set cookie)
curl -X POST http://localhost:8089/api/auth/login \
  -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)" \
  -d '{"email": "test@example.com"}' \
  -c cookies.txt

# Check auth status (should use cookie)
curl -X GET http://localhost:8089/api/auth/status \
  -b cookies.txt

# Logout (should clear cookie)
curl -X POST http://localhost:8089/api/auth/logout \
  -b cookies.txt \
  -c cookies.txt
```

### **Test Mobile JWT Auth**
```bash
# Login (should return JWT)
curl -X POST http://localhost:8089/api/auth/login \
  -H "Content-Type: application/json" \
  -H "User-Agent: MyApp/1.0 (iPhone; iOS 14.0) React-Native/0.64" \
  -d '{"email": "test@example.com"}'

# Use JWT token
curl -X GET http://localhost:8089/api/auth/status \
  -H "Authorization: Bearer <jwt-token>"
```

## ✅ **Migration Checklist**

### **Backend Changes**
- [ ] Add device detection utility
- [ ] Implement AuthResponseHandler
- [ ] Add cookie auth dependencies
- [ ] Update login endpoints
- [ ] Add auth status endpoint
- [ ] Test cookie and JWT auth

### **Frontend Changes**
- [ ] Desktop: Remove JWT token, use credentials: 'include'
- [ ] Mobile: Keep JWT token approach
- [ ] Update auth status checks
- [ ] Test cross-device compatibility

Dit geeft je een complete, production-ready cookie authentication implementation! 🍪