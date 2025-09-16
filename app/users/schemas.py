"""
Pydantic models for user management.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, validator
from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class UserPermissions(BaseModel):
    """User permissions for frontend."""
    canManageUsers: bool = False
    canDeleteUsers: bool = False
    canModifyAdminRoles: bool = False
    isSuperAdmin: bool = False


class UserBase(BaseModel):
    """Base user model."""
    email: str
    name: Optional[str] = None
    role: UserRole = UserRole.USER
    status: UserStatus = UserStatus.ACTIVE

    @validator('email')
    def validate_email(cls, v):
        """Simple email validation."""
        if '@' not in v or '.' not in v:
            raise ValueError('Invalid email format')
        return v.lower()


class UserCreate(UserBase):
    """User creation model."""
    password: Optional[str] = None


class UserUpdate(BaseModel):
    """User update model."""
    name: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None

    @validator('role')
    def validate_role_change(cls, v):
        """Validate role changes."""
        if v and v == UserRole.SUPER_ADMIN:
            raise ValueError("Cannot assign super_admin role through API")
        return v


class User(UserBase):
    """Complete user model."""
    id: str
    login_count: int = 0
    last_login: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Computed permissions
    permissions: Optional[UserPermissions] = None

    class Config:
        from_attributes = True

    def get_permissions(self) -> UserPermissions:
        """Calculate user permissions based on role."""
        if self.role == UserRole.SUPER_ADMIN:
            return UserPermissions(
                canManageUsers=True,
                canDeleteUsers=True,
                canModifyAdminRoles=True,
                isSuperAdmin=True
            )
        elif self.role == UserRole.ADMIN:
            return UserPermissions(
                canManageUsers=True,
                canDeleteUsers=True,
                canModifyAdminRoles=False,
                isSuperAdmin=False
            )
        else:
            return UserPermissions()


class UserActivity(BaseModel):
    """User activity log model."""
    id: str
    user_id: str
    admin_id: Optional[str] = None
    action: str
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime


class UserListResponse(BaseModel):
    """Response for user list endpoint."""
    success: bool = True
    data: Dict[str, Any]


class UserResponse(BaseModel):
    """Response for single user endpoint."""
    success: bool = True
    data: User


class UserStatsResponse(BaseModel):
    """Response for user statistics."""
    success: bool = True
    data: Dict[str, Any]


class BulkOperationRequest(BaseModel):
    """Request for bulk operations."""
    action: str
    user_ids: List[str]

    @validator('action')
    def validate_action(cls, v):
        valid_actions = ['activate', 'deactivate', 'delete', 'make_admin', 'remove_admin']
        if v not in valid_actions:
            raise ValueError(f"Action must be one of: {valid_actions}")
        return v


class BulkOperationResponse(BaseModel):
    """Response for bulk operations."""
    success: bool = True
    message: str
    data: Dict[str, Any]