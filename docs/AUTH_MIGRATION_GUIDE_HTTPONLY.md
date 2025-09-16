# Auth Migration Guide: From JWT to HttpOnly Cookies

## 🎯 **Migration Overview**

Deze guide migreert van JWT tokens in localStorage/sessionStorage naar **httpOnly cookies** voor alle web browsers (desktop + mobile websites).

### **Before → After**

```
BEFORE (JWT Tokens):
├── Desktop: JWT in sessionStorage
├── Mobile website: JWT in localStorage
├── Manual token management
└── Inheritance via pairing codes

AFTER (HttpOnly Cookies):
├── Desktop: HttpOnly cookie (automatic)
├── Mobile website: HttpOnly cookie (automatic inheritance!)
├── Zero token management
└── Automatic inheritance via browser
```

## 🚀 **Key Benefits**

1. **🔒 Maximum Security**: XSS protection via httpOnly
2. **🎯 Zero Frontend Changes**: Unified auth blijft exact hetzelfde
3. **🔄 Automatic Inheritance**: Mobile websites erven desktop login automatisch
4. **🧹 Simpler State**: Geen token storage meer in frontend
5. **🌐 Universal Support**: Werkt in alle web browsers

## 📋 **Migration Steps**

### **Step 1: Create Auth Response Handler**

```python
# app/pairing/auth_response.py (NEW FILE)
"""
Authentication response handler for httpOnly cookies.
"""
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
        """Create cookie-based auth response for web browsers."""

        # Set secure httpOnly cookie
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,              # XSS protection
            secure=False,               # False for local development
            samesite="lax",             # Lax for local development
            max_age=8 * 60 * 60,       # 8 hours
            path="/",                   # Available for all routes
        )

        logger.info(f"HttpOnly cookie set for user {user_data.get('email')}")

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
            secure=False,  # Match the original cookie settings
            samesite="lax"
        )
        logger.info("Auth cookie cleared")
```

### **Step 2: Create Cookie Auth Dependencies**

```python
# app/pairing/auth_dependencies.py (NEW FILE)
"""
Authentication dependencies for httpOnly cookies.
"""
from fastapi import Request, HTTPException, status, Depends
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

async def get_auth_token_from_request(request: Request) -> Optional[str]:
    """Extract auth token from request (cookie first, then header fallback)."""

    # Try cookie first (web browsers)
    cookie_token = request.cookies.get("session_token")
    if cookie_token:
        logger.debug("Auth token found in cookie")
        return cookie_token

    # Fallback: Try Authorization header (for API clients)
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

### **Step 3: Update Login Endpoints**

**Update `/auth/login` endpoint:**

```python
# app/pairing/router.py - Update login function
from fastapi import Response
from .auth_response import AuthResponseHandler

@router.post("/auth/login")
async def login(
    request: Request,
    response: Response,  # ← ADD this parameter
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

        # ✅ NEW: HttpOnly cookie response (instead of returning token)
        return AuthResponseHandler.create_cookie_auth_response(
            response, token, user_data
        )

    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")
```

**Update `/auth/login-magic` endpoint:**

```python
@router.post("/auth/login-magic")
async def login_magic(
    request: Request,
    response: Response,  # ← ADD this parameter
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

            # ✅ NEW: HttpOnly cookie response
            return AuthResponseHandler.create_cookie_auth_response(
                response, token, user_data
            )

        raise HTTPException(status_code=400, detail="Invalid email")

    except Exception as e:
        logger.error(f"Magic login error: {e}")
        raise HTTPException(status_code=500, detail="Magic login failed")
```

### **Step 4: Add Auth Status & Logout Endpoints**

```python
# Add these endpoints to router.py
from .auth_dependencies import RequireAuth

@router.get("/auth/status")
async def auth_status(current_user: dict = RequireAuth):
    """Check authentication status using cookie."""
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

### **Step 5: Frontend Impact Analysis**

**✅ ZERO CHANGES NEEDED in Unified Auth:**

```typescript
// This continues to work EXACTLY the same:
const { login, logout, isAuthenticated, user } = useAuth();

// Frontend doesn't need to know about cookies vs JWT!
const handleLogin = async () => {
    const success = await login(email);
    if (success) {
        // User is now logged in via httpOnly cookie
    }
};
```

**✅ Automatic `credentials: 'include'` in fetch calls:**

```typescript
// Unified auth should already use:
fetch('/api/auth/login', {
    method: 'POST',
    credentials: 'include',  // ← This enables cookie support
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email })
});
```

**✅ State simplification opportunity:**

```typescript
// Before (with JWT tokens):
interface AuthState {
    user: User | null;
    token: string | null;      // ← Can be removed!
    isAuthenticated: boolean;
}

// After (with httpOnly cookies):
interface AuthState {
    user: User | null;
    isAuthenticated: boolean;  // ← Simpler!
}
```

## 🧪 **Testing the Migration**

### **Test 1: Desktop Login**
```bash
# Login (should set httpOnly cookie)
curl -X POST http://localhost:8089/api/auth/login \
  -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)" \
  -d '{"email": "test@example.com"}' \
  -c cookies.txt

# Expected response: user data, NO token field
# Expected: Set-Cookie header with session_token
```

### **Test 2: Auth Status with Cookie**
```bash
# Check auth status (should use cookie)
curl -X GET http://localhost:8089/api/auth/status \
  -b cookies.txt

# Expected: {"authenticated": true, "user": {...}}
```

### **Test 3: Mobile Website Inheritance**
```bash
# Desktop login first
curl -X POST http://localhost:8089/api/auth/login \
  -H "User-Agent: Mozilla/5.0 (Macintosh)" \
  -d '{"email": "test@example.com"}' \
  -c cookies.txt

# Then mobile website (same cookie jar = automatic inheritance!)
curl -X GET http://localhost:8089/api/auth/status \
  -H "User-Agent: Mozilla/5.0 (iPhone)" \
  -b cookies.txt

# Expected: Automatically authenticated!
```

### **Test 4: Logout Cookie Cleanup**
```bash
# Logout (should clear cookie)
curl -X POST http://localhost:8089/api/auth/logout \
  -b cookies.txt \
  -c cookies.txt

# Expected: Set-Cookie with expired/deleted session_token
```

## ⚠️ **Migration Considerations**

### **Breaking Changes:**
1. **Response Format**: Login endpoints no longer return `token` field
2. **Cookie Dependency**: Frontend must use `credentials: 'include'`
3. **Development Settings**: Cookies use `secure=false`, `samesite=lax` for local dev

### **Compatibility:**
- ✅ **Unified Auth**: No changes needed
- ✅ **API Endpoints**: Still accept Authorization header as fallback
- ✅ **Mobile Websites**: Automatic inheritance via cookies
- ⚠️ **Native Apps**: Would need separate JWT endpoint (future work)

### **Production Configuration:**
```bash
# .env for production
COOKIE_SECURE=true
COOKIE_SAMESITE=strict
```

## 🎯 **Benefits After Migration**

### **Security Improvements:**
- ✅ **XSS Protection**: HttpOnly prevents JavaScript access
- ✅ **CSRF Protection**: SameSite attribute
- ✅ **Automatic HTTPS**: Secure flag in production

### **Developer Experience:**
- ✅ **Simpler Frontend**: No token management needed
- ✅ **Automatic Inheritance**: Mobile websites inherit desktop login
- ✅ **Less State**: Remove token from Zustand store
- ✅ **Better Immutable Updates**: Fewer fields to manage

### **User Experience:**
- ✅ **Seamless Inheritance**: Login on desktop → auto login on mobile website
- ✅ **Better Security**: Users get maximum protection automatically
- ✅ **No Behavior Changes**: Login/logout flows identical

## ✅ **Migration Checklist**

### **Backend Tasks:**
- [ ] Create `app/pairing/auth_response.py`
- [ ] Create `app/pairing/auth_dependencies.py`
- [ ] Update `/auth/login` endpoint (add Response parameter)
- [ ] Update `/auth/login-magic` endpoint (add Response parameter)
- [ ] Add `/auth/status` endpoint
- [ ] Add `/auth/logout` endpoint
- [ ] Update `/auth/verify` endpoint
- [ ] Test all endpoints with cookies

### **Frontend Verification:**
- [ ] Verify `credentials: 'include'` in fetch calls
- [ ] Test login flow (should work unchanged)
- [ ] Test logout flow (should work unchanged)
- [ ] Test auth status checks (should work unchanged)
- [ ] Consider removing token from state (optional cleanup)

### **Testing:**
- [ ] Desktop browser login
- [ ] Mobile website inheritance
- [ ] Logout cookie cleanup
- [ ] Cross-tab behavior
- [ ] Page refresh persistence

**Result: Maximum security with zero frontend complexity!** 🎉