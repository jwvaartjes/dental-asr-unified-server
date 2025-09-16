# 🦷 Mondplan Speech - User Management API Documentation

**Base URL:** `http://localhost:8089` (development)
**Authentication:** Bearer JWT tokens
**Content-Type:** `application/json`

## 📋 Table of Contents

- [Authentication Endpoints](#authentication-endpoints)
- [User Management Endpoints](#user-management-endpoints)
- [Authorization & Permissions](#authorization--permissions)
- [Error Handling](#error-handling)
- [Response Formats](#response-formats)

## 🔐 Authentication Endpoints

### POST `/api/auth/login-magic`
**Description:** Magic link login (no password required)

**Request:**
```json
{
  "email": "admin@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "uuid-string",
    "email": "admin@example.com",
    "name": "Admin User",
    "role": "super_admin",
    "permissions": {
      "canManageUsers": true,
      "canDeleteUsers": true,
      "canModifyAdminRoles": true,
      "isSuperAdmin": true
    }
  }
}
```

### POST `/api/auth/login`
**Description:** Regular login with email and password

**Request:**
```json
{
  "email": "user@example.com",
  "password": "your-password"
}
```

**Response:** Same as magic login above

### GET `/api/auth/check-email`
**Description:** Check if an email exists in the system

**Query Parameters:**
- `email` (required): Email to check

**Example:** `GET /api/auth/check-email?email=test@example.com`

**Response:**
```json
{
  "exists": true,
  "message": "Email found"
}
```

### GET `/api/auth/verify`
**Description:** Verify if the current token is valid

**Headers:**
```
Authorization: Bearer <your-jwt-token>
```

**Response:**
```json
{
  "authenticated": true,
  "user": "user@example.com"
}
```

## 👥 User Management Endpoints

> **⚠️ Authorization Required:** All user management endpoints require **admin** or **super_admin** role

### GET `/api/users/`
**Description:** Get paginated list of users with filtering and sorting

**Headers:**
```
Authorization: Bearer <your-jwt-token>
```

**Query Parameters:**
- `page` (optional, default: 1): Page number
- `limit` (optional, default: 20, max: 100): Items per page
- `search` (optional): Search in email/name
- `status` (optional): Filter by status (`active`, `inactive`, `all`)
- `role` (optional): Filter by role (`user`, `admin`, `all`)
- `sort_by` (optional, default: `created_at`): Sort field (`email`, `name`, `created_at`, `last_login`)
- `sort_order` (optional, default: `desc`): Sort order (`asc`, `desc`)

**Example:** `GET /api/users/?page=1&limit=10&search=admin&status=active&sort_by=email&sort_order=asc`

**Response:**
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "id": "uuid-string",
        "email": "admin@example.com",
        "name": "Admin User",
        "role": "super_admin",
        "status": "active",
        "login_count": 15,
        "last_login": "2025-01-15T10:30:00Z",
        "last_login_ip": "192.168.1.1",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-15T10:30:00Z",
        "permissions": {
          "canManageUsers": true,
          "canDeleteUsers": true,
          "canModifyAdminRoles": true,
          "isSuperAdmin": true
        }
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 10,
      "total": 25,
      "total_pages": 3
    }
  }
}
```

### GET `/api/users/stats`
**Description:** Get user statistics for admin dashboard

**Headers:**
```
Authorization: Bearer <your-jwt-token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_users": 150,
    "active_users": 140,
    "inactive_users": 10,
    "admin_users": 5,
    "recent_registrations": [],
    "recent_logins": []
  }
}
```

### GET `/api/users/{user_id}`
**Description:** Get detailed user information

**Headers:**
```
Authorization: Bearer <your-jwt-token>
```

**Query Parameters:**
- `include_activity` (optional, default: false): Include activity log

**Example:** `GET /api/users/uuid-string?include_activity=true`

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid-string",
    "email": "user@example.com",
    "name": "User Name",
    "role": "user",
    "status": "active",
    "login_count": 5,
    "last_login": "2025-01-15T08:00:00Z",
    "last_login_ip": "192.168.1.100",
    "created_at": "2025-01-10T00:00:00Z",
    "updated_at": "2025-01-15T08:00:00Z",
    "permissions": {
      "canManageUsers": false,
      "canDeleteUsers": false,
      "canModifyAdminRoles": false,
      "isSuperAdmin": false
    },
    "activity_log": [
      {
        "action": "user_updated",
        "timestamp": "2025-01-15T09:00:00Z",
        "ip_address": "192.168.1.1",
        "details": {
          "changes": {"status": "active"}
        }
      }
    ]
  }
}
```

### PUT `/api/users/{user_id}`
**Description:** Update user information

**Headers:**
```
Authorization: Bearer <your-jwt-token>
```

**Request:**
```json
{
  "name": "Updated Name",
  "role": "admin",
  "status": "inactive"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    // Updated user object (same format as GET /api/users/{user_id})
  }
}
```

**Notes:**
- Cannot modify own role or status
- Only super_admin can create other admin users
- Cannot modify super_admin users (unless you are super_admin)

### POST `/api/users/{user_id}/activate`
**Description:** Activate user account

**Headers:**
```
Authorization: Bearer <your-jwt-token>
```

**Response:**
```json
{
  "success": true,
  "message": "User activated successfully"
}
```

### POST `/api/users/{user_id}/deactivate`
**Description:** Deactivate user account

**Headers:**
```
Authorization: Bearer <your-jwt-token>
```

**Response:**
```json
{
  "success": true,
  "message": "User deactivated successfully"
}
```

**Notes:**
- Cannot deactivate own account
- Cannot deactivate super_admin users

### POST `/api/users/{user_id}/make-admin`
**Description:** Grant admin privileges to user

> **⚠️ Super Admin Only:** This endpoint requires **super_admin** role

**Headers:**
```
Authorization: Bearer <your-jwt-token>
```

**Response:**
```json
{
  "success": true,
  "message": "User granted admin privileges"
}
```

### POST `/api/users/{user_id}/remove-admin`
**Description:** Remove admin privileges from user

> **⚠️ Super Admin Only:** This endpoint requires **super_admin** role

**Headers:**
```
Authorization: Bearer <your-jwt-token>
```

**Response:**
```json
{
  "success": true,
  "message": "Admin privileges revoked"
}
```

**Notes:**
- Cannot revoke super_admin privileges
- Cannot revoke own admin privileges

### DELETE `/api/users/{user_id}`
**Description:** Delete user account

> **⚠️ Super Admin Only:** This endpoint requires **super_admin** role

**Headers:**
```
Authorization: Bearer <your-jwt-token>
```

**Response:**
```json
{
  "success": true,
  "message": "User deleted successfully"
}
```

**Notes:**
- Cannot delete own account
- Cannot delete super_admin users

### POST `/api/users/bulk`
**Description:** Perform bulk operations on multiple users

**Headers:**
```
Authorization: Bearer <your-jwt-token>
```

**Request:**
```json
{
  "action": "activate",
  "user_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Valid Actions:**
- `activate` - Activate users (admin required)
- `deactivate` - Deactivate users (admin required)
- `delete` - Delete users (super_admin required)
- `make_admin` - Grant admin privileges (super_admin required)
- `remove_admin` - Revoke admin privileges (super_admin required)

**Response:**
```json
{
  "success": true,
  "message": "Bulk operation completed: 3 processed, 0 failed",
  "data": {
    "processed": 3,
    "failed": 0,
    "errors": []
  }
}
```

### GET `/api/users/me/profile`
**Description:** Get current user's profile

**Headers:**
```
Authorization: Bearer <your-jwt-token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    // Current user object (same format as other user endpoints)
  }
}
```

## 🔐 Authorization & Permissions

### Role Hierarchy
1. **user** - Regular user (no management access)
2. **admin** - Can manage users, cannot modify admin roles
3. **super_admin** - Can do everything, including managing admin roles

### Permission Matrix

| Action | User | Admin | Super Admin |
|--------|------|-------|-------------|
| View own profile | ✅ | ✅ | ✅ |
| List users | ❌ | ✅ | ✅ |
| View user details | ❌ | ✅ | ✅ |
| Update users | ❌ | ✅ | ✅ |
| Activate/Deactivate | ❌ | ✅ | ✅ |
| Make/Remove admin | ❌ | ❌ | ✅ |
| Delete users | ❌ | ❌ | ✅ |
| Bulk operations | ❌ | ✅* | ✅ |

*Admin can only perform safe bulk operations (activate/deactivate)

### Frontend Permission Flags

When you receive a user object, use these permission flags for UI rendering:

```typescript
interface UserPermissions {
  canManageUsers: boolean;      // Show user management menu
  canDeleteUsers: boolean;      // Show delete buttons
  canModifyAdminRoles: boolean; // Show admin role controls
  isSuperAdmin: boolean;        // Show super admin features
}
```

## ❌ Error Handling

### HTTP Status Codes

- `200` - Success
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (invalid/missing token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (user doesn't exist)
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error

### Error Response Format

```json
{
  "detail": "Admin privileges required"
}
```

### Common Errors

**401 Unauthorized:**
```json
{
  "detail": "Authentication required"
}
```

**403 Forbidden:**
```json
{
  "detail": "Admin privileges required"
}
```

**400 Bad Request:**
```json
{
  "detail": "Cannot assign super_admin role through API"
}
```

**404 Not Found:**
```json
{
  "detail": "User not found"
}
```

## 📊 Response Formats

### Success Response
All successful responses follow this format:
```json
{
  "success": true,
  "data": { /* actual data */ }
}
```

### List Response
Paginated lists include pagination info:
```json
{
  "success": true,
  "data": {
    "users": [/* array of users */],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 100,
      "total_pages": 5
    }
  }
}
```

## 🚀 Quick Start Example

```javascript
// 1. Login
const loginResponse = await fetch('http://localhost:8089/api/auth/login-magic', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    email: 'admin@example.com'
  })
});

const { token, user } = await loginResponse.json();

// 2. Store token and check permissions
localStorage.setItem('jwt_token', token);
const canManageUsers = user.permissions.canManageUsers;

// 3. Make authenticated request
const usersResponse = await fetch('http://localhost:8089/api/users/', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  }
});

const { data } = await usersResponse.json();
console.log('Users:', data.users);
console.log('Total pages:', data.pagination.total_pages);
```

## 📝 Notes for Frontend Implementation

1. **Token Storage**: Store JWT tokens securely (consider httpOnly cookies for production)
2. **Token Expiry**: Handle token expiration (currently 2 hours)
3. **Permission-Based UI**: Use permission flags to show/hide UI elements
4. **Error Handling**: Implement proper error handling for all status codes
5. **Loading States**: Show loading indicators for API calls
6. **Pagination**: Implement pagination controls for user lists
7. **Search & Filtering**: Add search and filter controls
8. **Bulk Operations**: Consider checkboxes for bulk operations
9. **Activity Logs**: Show user activity history when needed
10. **Real-time Updates**: Consider WebSocket connections for real-time user status updates

---

**Need help?** Check the auto-generated API docs at `http://localhost:8089/docs` or test endpoints at `http://localhost:8089/api-test`