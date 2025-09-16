# HttpOnly Cookie Migration Plan

## 🎯 **Migratie Doel**

Van: JWT tokens in response body → Naar: HttpOnly cookies voor web browsers

**Voordelen:**
- ✅ **Perfect match met unified auth**: Geen token management in frontend nodig
- ✅ **Automatische inheritance**: Mobile websites erven desktop login status
- ✅ **Maximum security**: XSS protection door httpOnly
- ✅ **Zero code changes**: Frontend unified auth werkt zonder aanpassingen

## 🔄 **Stap-voor-Stap Migratie**

### **Stap 1: Response Class Toevoegen**

```python
# app/pairing/auth_response.py (NIEUW)
from fastapi import Response, Request
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class AuthResponseHandler:
    """Handle auth responses with httpOnly cookies."""

    @staticmethod
    def create_cookie_auth_response(
        response: Response,
        token: str,
        user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create cookie-based auth response."""

        # Set secure httpOnly cookie
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,              # XSS protection
            secure=True,                # HTTPS only (False for local dev)
            samesite="strict",          # CSRF protection
            max_age=8 * 60 * 60,       # 8 hours
            path="/",                   # Available for all routes
        )

        logger.info(f"Auth cookie set for user {user_data.get('email')}")

        # Return user data WITHOUT token
        return {
            "success": True,
            "user": user_data,
            "auth_method": "cookie",
            "expires_in": 8 * 60 * 60,
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

### **Stap 2: Cookie Auth Dependency**

```python
# app/pairing/auth_dependencies.py (NIEUW)
from fastapi import Request, HTTPException, status
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

async def get_auth_token_from_request(request: Request) -> Optional[str]:
    """Extract auth token from request (cookie or header)."""

    # Try cookie first (web browsers)
    cookie_token = request.cookies.get("session_token")
    if cookie_token:
        logger.debug("Auth token found in cookie")
        return cookie_token

    # Try Authorization header (fallback for native apps)
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
        "token": token
    }

# Convenience dependency for routes that require auth
RequireAuth = Depends(get_current_user)
```

### **Stap 3: Update Login Endpoints**

**Voor `/auth/login`:**
```python
from fastapi import Response
from .auth_response import AuthResponseHandler

@router.post("/auth/login")
async def login(
    request: Request,
    response: Response,  # ← Voeg Response toe
    security: SecurityMiddleware = Depends(get_security_middleware)
):
    """Regular login endpoint with httpOnly cookies."""
    await security.validate_request(request)
    try:
        from app.users.auth import user_auth
        data = await request.json()
        email = data.get("email", data.get("username", ""))
        password = data.get("password", "")

        logger.info(f"Login attempt for: {email}")

        # Existing auth logic...
        user = await user_auth.validate_user_credentials(email, password)
        if user:
            token = user_auth.generate_token(user)
            user_data = {
                "id": user.id,
                "email": user.email,
                "name": user.name or (email.split("@")[0] if "@" in email else email),
                "role": user.role,
                "permissions": user.permissions.dict()
            }
        else:
            # Fallback for development
            from app.users.schemas import UserPermissions
            mock_permissions = UserPermissions(
                canManageUsers=True,
                canDeleteUsers=True,
                canModifyAdminRoles=True,
                isSuperAdmin=True
            ) if "admin" in email else UserPermissions()

            token = JWTHandler.generate_token(email)
            user_data = {
                "id": "mock-user-id",
                "email": email,
                "name": email.split("@")[0] if "@" in email else email,
                "role": "super_admin" if "admin" in email else "user",
                "permissions": mock_permissions.dict()
            }

        # ✅ NIEUWE MANIER: HttpOnly cookie response
        return AuthResponseHandler.create_cookie_auth_response(
            response, token, user_data
        )

    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")
```

**Voor `/auth/login-magic`:**
```python
@router.post("/auth/login-magic")
async def login_magic(
    request: Request,
    response: Response,  # ← Voeg Response toe
    security: SecurityMiddleware = Depends(get_security_middleware)
):
    """Magic link login with httpOnly cookies."""
    await security.validate_request(request)
    try:
        from app.users.auth import user_auth
        data = await request.json()
        email = data.get("email", "")

        logger.info(f"Magic login attempt for: {email}")

        if "@" in email:
            # Existing logic...
            user = await user_auth.get_user_by_email(email)
            if user and user.status == "active":
                token = user_auth.generate_token(user)
                user_data = {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name or email.split("@")[0],
                    "role": user.role,
                    "permissions": user.permissions.dict()
                }
            else:
                # Development fallback
                from app.users.schemas import UserRole, UserPermissions
                mock_permissions = UserPermissions(
                    canManageUsers=True,
                    canDeleteUsers=True,
                    canModifyAdminRoles=True,
                    isSuperAdmin=True
                ) if "admin" in email else UserPermissions()

                token = JWTHandler.generate_token(email)
                user_data = {
                    "id": "mock-user-id",
                    "email": email,
                    "name": email.split("@")[0],
                    "role": "super_admin" if "admin" in email else "user",
                    "permissions": mock_permissions.dict()
                }

            # ✅ NIEUWE MANIER: HttpOnly cookie response
            return AuthResponseHandler.create_cookie_auth_response(
                response, token, user_data
            )

        raise HTTPException(status_code=400, detail="Invalid email")

    except Exception as e:
        logger.error(f"Magic login error: {e}")
        raise HTTPException(status_code=500, detail="Magic login failed")
```

### **Stap 4: Auth Status Endpoint**

```python
from .auth_dependencies import RequireAuth

@router.get("/auth/status")
async def auth_status(current_user: dict = RequireAuth):
    """Check authentication status using cookie or header."""
    return {
        "authenticated": True,
        "user": current_user["user"]
    }

@router.post("/auth/logout")
async def logout(
    response: Response,
    current_user: dict = RequireAuth
):
    """Logout with cookie cleanup."""
    user_email = current_user["user"]

    # Clear cookie
    AuthResponseHandler.clear_auth_cookie(response)
    logger.info(f"Logout: Cookie cleared for {user_email}")

    return {
        "success": True,
        "message": "Logged out successfully"
    }

@router.get("/auth/verify")
async def verify_token(current_user: dict = RequireAuth):
    """Verify token (works with both cookies and headers)."""
    return {
        "valid": True,
        "user": current_user["user"]
    }
```

### **Stap 5: Development Configuration**

```python
# app/settings.py - Add cookie settings
import os

class Settings:
    # Existing settings...

    # Cookie settings
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    cookie_samesite: str = os.getenv("COOKIE_SAMESITE", "lax")  # lax for dev
    cookie_max_age: int = int(os.getenv("COOKIE_MAX_AGE", "28800"))  # 8 hours

settings = Settings()

# Update AuthResponseHandler to use settings
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

```bash
# .env - Add for local development
COOKIE_SECURE=false          # Set to true in production
COOKIE_SAMESITE=lax          # Can be 'lax' for local dev
COOKIE_MAX_AGE=28800         # 8 hours
```

## 🎯 **Frontend Impact: ZERO!**

**Unified Auth blijft hetzelfde:**
```typescript
// Dit blijft exact hetzelfde werken:
const { login, logout, isAuthenticated, user } = useAuth();

// Maar onder de motorkap:
// VOOR: Manual token management
// NA: Browser handelt cookies automatisch af
```

**Login blijft hetzelfde:**
```typescript
const handleLogin = async () => {
    const success = await login(email);
    // ✅ Werkt nog steeds, maar nu met cookies!
};
```

**Auth requests worden automatisch:**
```typescript
// Frontend hoeft NIETS te veranderen:
fetch('/api/protected', {
    credentials: 'include'  // Browser stuurt cookie mee
});

// Unified auth store handelt dit al af!
```

## 🧪 **Testing Plan**

### **Test 1: Desktop Login**
```bash
# Login (should set cookie)
curl -X POST http://localhost:8089/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}' \
  -c cookies.txt

# Response should NOT contain token, but cookie should be set
```

### **Test 2: Auth Status with Cookie**
```bash
# Check auth status (should use cookie)
curl -X GET http://localhost:8089/api/auth/status \
  -b cookies.txt

# Should return user data
```

### **Test 3: Mobile Website Inheritance**
```bash
# Desktop login first
curl -X POST http://localhost:8089/api/auth/login \
  -H "User-Agent: Mozilla/5.0 (Macintosh)" \
  -d '{"email": "test@example.com"}' \
  -c cookies.txt

# Then mobile website (same cookie jar)
curl -X GET http://localhost:8089/api/auth/status \
  -H "User-Agent: Mozilla/5.0 (iPhone)" \
  -b cookies.txt

# Should be automatically authenticated!
```

## ✅ **Migration Checklist**

- [ ] Create `auth_response.py` with cookie handling
- [ ] Create `auth_dependencies.py` with cookie auth
- [ ] Update `/auth/login` endpoint to use cookies
- [ ] Update `/auth/login-magic` endpoint to use cookies
- [ ] Add `/auth/logout` endpoint with cookie cleanup
- [ ] Update settings for development
- [ ] Test desktop login with cookies
- [ ] Test mobile website inheritance
- [ ] Verify unified auth frontend still works

**Result:**
- ✅ HttpOnly cookies voor maximum security
- ✅ Automatische inheritance tussen desktop en mobile websites
- ✅ Zero frontend changes - unified auth blijft werken
- ✅ Pairing alleen nodig voor native apps (later)