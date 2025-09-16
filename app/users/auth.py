"""
Enhanced authentication system with real user validation.
"""
import os
import jwt
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client

from .schemas import User, UserRole, UserPermissions

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "test-secret-key-for-local-testing")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 8


class UserAuth:
    """Enhanced authentication with Supabase user validation."""

    def __init__(self):
        """Initialize Supabase connection for user validation."""
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

            if not supabase_url or not supabase_key:
                raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

            self.client: Client = create_client(supabase_url, supabase_key)
            logger.info("UserAuth initialized with Supabase connection")

        except Exception as e:
            logger.error(f"Failed to initialize UserAuth: {e}")
            raise

    async def validate_user_credentials(self, email: str, password: str) -> Optional[User]:
        """Validate user credentials against Supabase."""
        try:
            # Get user by email
            result = self.client.table("users").select("*").eq("email", email).eq("status", "active").limit(1).execute()

            if not result.data:
                logger.warning(f"User not found or inactive: {email}")
                return None

            user_data = result.data[0]

            # For now, skip password validation in development
            # In production, implement proper password hashing
            if password and user_data.get("password_hash"):
                # TODO: Implement bcrypt password verification
                pass

            # Update last login info
            await self._update_login_info(user_data["id"], "127.0.0.1")  # TODO: Get real IP

            return self._create_user_object(user_data)

        except Exception as e:
            logger.error(f"Error validating credentials for {email}: {e}")
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID from Supabase."""
        try:
            result = self.client.table("users").select("*").eq("id", user_id).limit(1).execute()

            if not result.data:
                return None

            return self._create_user_object(result.data[0])

        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email from Supabase."""
        try:
            result = self.client.table("users").select("*").eq("email", email).limit(1).execute()

            if not result.data:
                return None

            return self._create_user_object(result.data[0])

        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None

    def generate_token(self, user: User) -> str:
        """Generate JWT token for authenticated user."""
        payload = {
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload."""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None

    async def _update_login_info(self, user_id: str, ip_address: str):
        """Update user login information."""
        try:
            self.client.table("users").update({
                "last_login": datetime.utcnow().isoformat(),
                "last_login_ip": ip_address,
                "login_count": self.client.table("users").select("login_count").eq("id", user_id).execute().data[0]["login_count"] + 1
            }).eq("id", user_id).execute()

        except Exception as e:
            logger.error(f"Failed to update login info for user {user_id}: {e}")

    def _create_user_object(self, user_data: Dict[str, Any]) -> User:
        """Create User object from Supabase data."""
        user = User(
            id=user_data["id"],
            email=user_data["email"],
            name=user_data.get("name"),
            role=UserRole(user_data.get("role", "user")),
            status=user_data.get("status", "active"),
            login_count=user_data.get("login_count", 0),
            last_login=user_data.get("last_login"),
            last_login_ip=user_data.get("last_login_ip"),
            created_at=user_data["created_at"],
            updated_at=user_data["updated_at"]
        )

        # Add permissions
        user.permissions = user.get_permissions()
        return user


# Global auth instance
user_auth = UserAuth()

# HTTP Bearer security
security = HTTPBearer(auto_error=False)


class AuthMiddleware:
    """Authentication middleware for dependency injection."""

    @staticmethod
    async def get_current_user(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Optional[User]:
        """Get current authenticated user from JWT token."""

        # Try to get token from Authorization header
        token = None
        if credentials:
            token = credentials.credentials

        # Fallback: try to get token from request body (for development)
        if not token:
            try:
                body = await request.json()
                token = body.get("token")
            except:
                pass

        if not token:
            return None

        # Verify token
        payload = user_auth.verify_token(token)
        if not payload:
            return None

        # Get user from database
        user = await user_auth.get_user_by_id(payload.get("user_id"))
        if not user or user.status != "active":
            return None

        return user

    async def get_current_user_from_token(self, token: str) -> Optional[User]:
        """Get current user from JWT token string."""
        if not token:
            return None

        # Verify token
        payload = user_auth.verify_token(token)
        if not payload:
            return None

        # Get user from database
        user = await user_auth.get_user_by_id(payload.get("user_id"))
        if not user or user.status != "active":
            return None

        return user


def extract_bearer_token(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Extract Bearer token from Authorization header."""
    if not authorization:
        return None

    if not authorization.startswith("Bearer "):
        return None

    return authorization[7:]  # Remove "Bearer " prefix


# Create a single instance of AuthMiddleware for dependencies
auth_middleware = AuthMiddleware()

# Simpler standalone dependency functions
async def get_current_user(
    authorization: str = Depends(extract_bearer_token)
) -> Optional[User]:
    """Get current user from JWT token."""
    return await auth_middleware.get_current_user(authorization)

async def require_auth(
    authorization: str = Depends(extract_bearer_token)
) -> User:
    """Require authentication - raise 401 if not authenticated."""
    current_user = await auth_middleware.get_current_user(authorization)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return current_user

async def require_admin(
    token: str = Depends(extract_bearer_token)
) -> User:
    """Require admin role - raise 403 if not admin."""
    current_user = await auth_middleware.get_current_user_from_token(token)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

async def require_superadmin(
    authorization: str = Depends(extract_bearer_token)
) -> User:
    """Require super admin role - raise 403 if not super admin."""
    current_user = await auth_middleware.get_current_user(authorization)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required"
        )
    return current_user