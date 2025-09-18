"""
User management API router.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Request, Query

from .auth import require_admin, require_superadmin
from ..pairing.auth_dependencies import RequireAuth
from .service import UserService
from .schemas import (
    User, UserUpdate, UserListResponse, UserResponse, UserStatsResponse,
    BulkOperationRequest, BulkOperationResponse
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/users", tags=["user-management"])

# Service instance
user_service = UserService()


async def get_admin_user_from_cookie_auth(current_user: dict) -> User:
    """Get admin user using httpOnly cookie authentication (same pattern as lexicon)"""
    from .auth import user_auth

    user_email = current_user["user"]
    user = await user_auth.get_user_by_email(user_email)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )

    return user


async def get_superadmin_user_from_cookie_auth(current_user: dict) -> User:
    """Get superadmin user using httpOnly cookie authentication (same pattern as lexicon)"""
    from .auth import user_auth

    user_email = current_user["user"]
    user = await user_auth.get_user_by_email(user_email)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required"
        )

    return user


def get_client_ip(request: Request) -> str:
    """Extract client IP from request headers."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    if request.client:
        return request.client.host

    return "127.0.0.1"


@router.get("/", response_model=UserListResponse)
async def get_users(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in email/name"),
    status: Optional[str] = Query("all", description="Filter by status: active, inactive, all"),
    role: Optional[str] = Query("all", description="Filter by role: user, admin, all"),
    sort_by: str = Query("created_at", description="Sort by field"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    current_user: dict = RequireAuth
):
    """Get paginated list of users with filtering."""
    try:
        # Get admin user using httpOnly cookie authentication
        admin_user = await get_admin_user_from_cookie_auth(current_user)

        # Validate parameters
        if status not in ["active", "inactive", "all"]:
            raise HTTPException(status_code=400, detail="Invalid status filter")

        if role not in ["user", "admin", "all"]:
            raise HTTPException(status_code=400, detail="Invalid role filter")

        if sort_by not in ["email", "name", "created_at", "last_login"]:
            raise HTTPException(status_code=400, detail="Invalid sort field")

        if sort_order not in ["asc", "desc"]:
            raise HTTPException(status_code=400, detail="Invalid sort order")

        data = await user_service.get_users(
            page=page,
            limit=limit,
            search=search,
            status=status if status != "all" else None,
            role=role if role != "all" else None,
            sort_by=sort_by,
            sort_order=sort_order
        )

        return UserListResponse(data=data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    current_user: dict = RequireAuth
):
    """Get user statistics."""
    try:
        # Get admin user using httpOnly cookie authentication
        admin_user = await get_admin_user_from_cookie_auth(current_user)

        data = await user_service.get_user_stats()
        return UserStatsResponse(data=data)

    except Exception as e:
        logger.error(f"Error in get_user_stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user statistics"
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    include_activity: bool = Query(False, description="Include activity log"),
    current_user: dict = RequireAuth
):
    """Get user details by ID."""
    try:
        # Get admin user using httpOnly cookie authentication
        admin_user = await get_admin_user_from_cookie_auth(current_user)

        user_data = await user_service.get_user(user_id, include_activity=include_activity)

        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return UserResponse(data=user_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user"
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    request: Request,
    current_user: dict = RequireAuth
):
    """Update user information."""
    try:
        # Get admin user using httpOnly cookie authentication
        admin_user = await get_admin_user_from_cookie_auth(current_user)

        ip_address = get_client_ip(request)

        success = await user_service.update_user(
            user_id=user_id,
            updates=user_update,
            admin_user=admin_user,
            ip_address=ip_address
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Return updated user
        user_data = await user_service.get_user(user_id)
        return UserResponse(data=user_data)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.post("/{user_id}/activate")
async def activate_user(
    user_id: str,
    request: Request,
    current_user: dict = RequireAuth
):
    """Activate user account."""
    try:
        # Get admin user using httpOnly cookie authentication
        admin_user = await get_admin_user_from_cookie_auth(current_user)

        ip_address = get_client_ip(request)

        success = await user_service.activate_user(
            user_id=user_id,
            admin_user=admin_user,
            ip_address=ip_address
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return {"success": True, "message": "User activated successfully"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error activating user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate user"
        )


@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    request: Request,
    current_user: dict = RequireAuth
):
    """Deactivate user account."""
    try:
        # Get admin user using httpOnly cookie authentication
        admin_user = await get_admin_user_from_cookie_auth(current_user)

        ip_address = get_client_ip(request)

        success = await user_service.deactivate_user(
            user_id=user_id,
            admin_user=admin_user,
            ip_address=ip_address
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return {"success": True, "message": "User deactivated successfully"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deactivating user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate user"
        )


@router.post("/{user_id}/make-admin")
async def make_admin(
    user_id: str,
    request: Request,
    current_user: dict = RequireAuth
):
    """Grant admin privileges to user."""
    try:
        # Get superadmin user using httpOnly cookie authentication
        admin_user = await get_superadmin_user_from_cookie_auth(current_user)

        ip_address = get_client_ip(request)

        success = await user_service.make_admin(
            user_id=user_id,
            admin_user=admin_user,
            ip_address=ip_address
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return {"success": True, "message": "User granted admin privileges"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error granting admin to user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to grant admin privileges"
        )


@router.post("/{user_id}/remove-admin")
async def remove_admin(
    user_id: str,
    request: Request,
    current_user: dict = RequireAuth
):
    """Remove admin privileges from user."""
    try:
        # Get superadmin user using httpOnly cookie authentication
        admin_user = await get_superadmin_user_from_cookie_auth(current_user)

        ip_address = get_client_ip(request)

        success = await user_service.remove_admin(
            user_id=user_id,
            admin_user=admin_user,
            ip_address=ip_address
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return {"success": True, "message": "Admin privileges revoked"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error removing admin from user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove admin privileges"
        )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    request: Request,
    current_user: dict = RequireAuth
):
    """Delete user account."""
    try:
        # Get superadmin user using httpOnly cookie authentication
        admin_user = await get_superadmin_user_from_cookie_auth(current_user)

        ip_address = get_client_ip(request)

        success = await user_service.delete_user(
            user_id=user_id,
            admin_user=admin_user,
            ip_address=ip_address
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return {"success": True, "message": "User deleted successfully"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


@router.post("/bulk", response_model=BulkOperationResponse)
async def bulk_operation(
    bulk_request: BulkOperationRequest,
    request: Request,
    current_user: dict = RequireAuth
):
    """Perform bulk operations on users."""
    try:
        # Get admin user using httpOnly cookie authentication
        admin_user = await get_admin_user_from_cookie_auth(current_user)

        # Require superadmin for certain operations
        dangerous_actions = ["delete", "make_admin", "remove_admin"]
        if bulk_request.action in dangerous_actions and admin_user.role != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Super admin privileges required for this operation"
            )

        ip_address = get_client_ip(request)

        result = await user_service.bulk_operation(
            action=bulk_request.action,
            user_ids=bulk_request.user_ids,
            admin_user=admin_user,
            ip_address=ip_address
        )

        message = f"Bulk operation completed: {result['processed']} processed, {result['failed']} failed"

        return BulkOperationResponse(
            message=message,
            data=result
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk operation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk operation"
        )


