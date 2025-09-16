"""
User management service with business logic.
"""
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from supabase import create_client, Client

from .schemas import User, UserCreate, UserUpdate, UserRole, UserStatus, UserActivity
from .auth import user_auth

logger = logging.getLogger(__name__)


class UserService:
    """Service for user management operations."""

    def __init__(self):
        """Initialize Supabase connection."""
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

            if not supabase_url or not supabase_key:
                raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

            self.client: Client = create_client(supabase_url, supabase_key)
            logger.info("UserService initialized")

        except Exception as e:
            logger.error(f"Failed to initialize UserService: {e}")
            raise

    async def get_users(
        self,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
        role: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """Get paginated list of users with filtering."""
        try:
            # Build query
            query = self.client.table("users").select("*", count="exact")

            # Apply filters
            if search:
                query = query.or_(f"email.ilike.%{search}%,name.ilike.%{search}%")

            if status and status != "all":
                query = query.eq("status", status)

            if role and role != "all":
                query = query.eq("role", role)

            # Apply sorting
            desc = sort_order == "desc"
            query = query.order(sort_by, desc=desc)

            # Apply pagination
            offset = (page - 1) * limit
            query = query.range(offset, offset + limit - 1)

            # Execute query
            result = query.execute()

            # Create user objects
            users = []
            for user_data in result.data:
                user = user_auth._create_user_object(user_data)
                users.append(user.dict())

            return {
                "users": users,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": result.count or 0,
                    "total_pages": ((result.count or 0) + limit - 1) // limit
                }
            }

        except Exception as e:
            logger.error(f"Error getting users: {e}")
            raise

    async def get_user(self, user_id: str, include_activity: bool = False) -> Optional[Dict[str, Any]]:
        """Get user by ID with optional activity log."""
        try:
            # Get user
            result = self.client.table("users").select("*").eq("id", user_id).limit(1).execute()

            if not result.data:
                return None

            user = user_auth._create_user_object(result.data[0])
            user_dict = user.dict()

            # Add activity log if requested
            if include_activity:
                activity_result = self.client.table("user_activity_log").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(50).execute()

                user_dict["activity_log"] = [
                    {
                        "action": activity["action"],
                        "timestamp": activity["created_at"],
                        "ip_address": activity.get("ip_address"),
                        "details": activity.get("details", {})
                    }
                    for activity in activity_result.data
                ]

            return user_dict

        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            raise

    async def update_user(
        self,
        user_id: str,
        updates: UserUpdate,
        admin_user: User,
        ip_address: str = "127.0.0.1"
    ) -> bool:
        """Update user information."""
        try:
            # Get current user
            current_user = await user_auth.get_user_by_id(user_id)
            if not current_user:
                return False

            # Prevent self-modification of critical fields
            if admin_user.id == user_id:
                if updates.role or updates.status:
                    raise ValueError("Cannot modify own role or status")

            # Prevent non-superadmin from creating other admins
            if updates.role == UserRole.ADMIN and admin_user.role != UserRole.SUPER_ADMIN:
                raise ValueError("Only super admin can create admin users")

            # Prevent modification of super admin
            if current_user.role == UserRole.SUPER_ADMIN and admin_user.role != UserRole.SUPER_ADMIN:
                raise ValueError("Cannot modify super admin user")

            # Build update data
            update_data = {}
            if updates.name is not None:
                update_data["name"] = updates.name
            if updates.role is not None:
                update_data["role"] = updates.role.value
            if updates.status is not None:
                update_data["status"] = updates.status.value

            if not update_data:
                return True  # No changes needed

            # Update user
            self.client.table("users").update(update_data).eq("id", user_id).execute()

            # Log activity
            await self._log_activity(
                user_id=user_id,
                admin_id=admin_user.id,
                action="user_updated",
                details={"changes": update_data},
                ip_address=ip_address
            )

            logger.info(f"User {user_id} updated by admin {admin_user.id}")
            return True

        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            raise

    async def activate_user(self, user_id: str, admin_user: User, ip_address: str = "127.0.0.1") -> bool:
        """Activate user account."""
        return await self._change_user_status(user_id, UserStatus.ACTIVE, admin_user, ip_address)

    async def deactivate_user(self, user_id: str, admin_user: User, ip_address: str = "127.0.0.1") -> bool:
        """Deactivate user account."""
        # Prevent self-deactivation
        if admin_user.id == user_id:
            raise ValueError("Cannot deactivate own account")

        # Prevent deactivating super admin
        user = await user_auth.get_user_by_id(user_id)
        if user and user.role == UserRole.SUPER_ADMIN:
            raise ValueError("Cannot deactivate super admin")

        return await self._change_user_status(user_id, UserStatus.INACTIVE, admin_user, ip_address)

    async def make_admin(self, user_id: str, admin_user: User, ip_address: str = "127.0.0.1") -> bool:
        """Grant admin privileges to user."""
        if admin_user.role != UserRole.SUPER_ADMIN:
            raise ValueError("Only super admin can grant admin privileges")

        try:
            self.client.table("users").update({"role": UserRole.ADMIN.value}).eq("id", user_id).execute()

            await self._log_activity(
                user_id=user_id,
                admin_id=admin_user.id,
                action="admin_privileges_granted",
                ip_address=ip_address
            )

            return True

        except Exception as e:
            logger.error(f"Error granting admin privileges to {user_id}: {e}")
            raise

    async def remove_admin(self, user_id: str, admin_user: User, ip_address: str = "127.0.0.1") -> bool:
        """Remove admin privileges from user."""
        if admin_user.role != UserRole.SUPER_ADMIN:
            raise ValueError("Only super admin can revoke admin privileges")

        # Prevent revoking super admin
        user = await user_auth.get_user_by_id(user_id)
        if user and user.role == UserRole.SUPER_ADMIN:
            raise ValueError("Cannot revoke super admin privileges")

        # Prevent self-demotion
        if admin_user.id == user_id:
            raise ValueError("Cannot revoke own admin privileges")

        try:
            self.client.table("users").update({"role": UserRole.USER.value}).eq("id", user_id).execute()

            await self._log_activity(
                user_id=user_id,
                admin_id=admin_user.id,
                action="admin_privileges_revoked",
                ip_address=ip_address
            )

            return True

        except Exception as e:
            logger.error(f"Error revoking admin privileges from {user_id}: {e}")
            raise

    async def delete_user(self, user_id: str, admin_user: User, ip_address: str = "127.0.0.1") -> bool:
        """Delete user account."""
        # Prevent self-deletion
        if admin_user.id == user_id:
            raise ValueError("Cannot delete own account")

        # Prevent deleting super admin
        user = await user_auth.get_user_by_id(user_id)
        if user and user.role == UserRole.SUPER_ADMIN:
            raise ValueError("Cannot delete super admin")

        try:
            # Log before deletion
            await self._log_activity(
                user_id=user_id,
                admin_id=admin_user.id,
                action="user_deleted",
                details={"deleted_user": user.dict() if user else {}},
                ip_address=ip_address
            )

            # Delete user (CASCADE will handle related records)
            self.client.table("users").delete().eq("id", user_id).execute()

            logger.info(f"User {user_id} deleted by admin {admin_user.id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            raise

    async def bulk_operation(
        self,
        action: str,
        user_ids: List[str],
        admin_user: User,
        ip_address: str = "127.0.0.1"
    ) -> Dict[str, Any]:
        """Perform bulk operations on users."""
        processed = 0
        failed = 0
        errors = []

        for user_id in user_ids:
            try:
                if action == "activate":
                    await self.activate_user(user_id, admin_user, ip_address)
                elif action == "deactivate":
                    await self.deactivate_user(user_id, admin_user, ip_address)
                elif action == "delete":
                    await self.delete_user(user_id, admin_user, ip_address)
                elif action == "make_admin":
                    await self.make_admin(user_id, admin_user, ip_address)
                elif action == "remove_admin":
                    await self.remove_admin(user_id, admin_user, ip_address)
                else:
                    raise ValueError(f"Unknown action: {action}")

                processed += 1

            except Exception as e:
                failed += 1
                errors.append(f"User {user_id}: {str(e)}")
                logger.error(f"Bulk operation {action} failed for user {user_id}: {e}")

        return {
            "processed": processed,
            "failed": failed,
            "errors": errors
        }

    async def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics."""
        try:
            # Get user counts by role and status
            result = self.client.table("users").select("role,status", count="exact").execute()

            stats = {
                "total_users": result.count or 0,
                "active_users": 0,
                "inactive_users": 0,
                "admin_users": 0,
                "recent_registrations": [],
                "recent_logins": []
            }

            # Count by status and role
            for user in result.data:
                if user["status"] == "active":
                    stats["active_users"] += 1
                else:
                    stats["inactive_users"] += 1

                if user["role"] in ["admin", "super_admin"]:
                    stats["admin_users"] += 1

            # Get recent registrations (last 30 days)
            # TODO: Implement date-based queries for charts

            return stats

        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            raise

    async def _change_user_status(
        self,
        user_id: str,
        status: UserStatus,
        admin_user: User,
        ip_address: str
    ) -> bool:
        """Helper method to change user status."""
        try:
            self.client.table("users").update({"status": status.value}).eq("id", user_id).execute()

            await self._log_activity(
                user_id=user_id,
                admin_id=admin_user.id,
                action=f"user_{status.value}",
                ip_address=ip_address
            )

            return True

        except Exception as e:
            logger.error(f"Error changing user {user_id} status to {status.value}: {e}")
            raise

    async def _log_activity(
        self,
        user_id: str,
        admin_id: str,
        action: str,
        details: Dict[str, Any] = None,
        ip_address: str = "127.0.0.1",
        user_agent: str = None
    ):
        """Log user management activity."""
        try:
            activity_data = {
                "user_id": user_id,
                "admin_id": admin_id,
                "action": action,
                "details": details or {},
                "ip_address": ip_address,
                "user_agent": user_agent
            }

            self.client.table("user_activity_log").insert(activity_data).execute()

        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
            # Don't raise - logging failure shouldn't break the main operation