# 📚 Frontend Integration Documentation

This directory contains comprehensive documentation for integrating the Mondplan Speech User Management API with your frontend application.

## 📁 Files Overview

### 📖 [`API_DOCUMENTATION_USER_MANAGEMENT.md`](./API_DOCUMENTATION_USER_MANAGEMENT.md)
**Complete API Reference**
- All authentication and user management endpoints
- Request/response examples with real data
- Permission requirements and authorization matrix
- Error handling and status codes
- Quick start guide with JavaScript examples

### 🔷 [`frontend-types.ts`](./frontend-types.ts)
**TypeScript Interfaces**
- Complete type definitions for all API responses
- Enums for roles, statuses, and actions
- React component prop types
- Hook return types
- Utility functions and type guards
- Constants and labels

### 🛠️ [`userService.example.ts`](./userService.example.ts)
**Ready-to-Use Service Class**
- Full TypeScript service class implementation
- Authentication handling with token management
- All user management operations
- Error handling and timeout management
- React hooks for easy integration
- Usage examples and patterns

## 🚀 Quick Start

### 1. Copy the Files
```bash
# Copy types to your project
cp docs/frontend-types.ts src/types/userManagement.ts

# Copy and customize the service
cp docs/userService.example.ts src/services/userService.ts
```

### 2. Install Dependencies (if needed)
```bash
npm install # or yarn install
# No additional dependencies required - uses fetch API
```

### 3. Initialize the Service
```typescript
import { UserManagementService } from './services/userService';

const userService = new UserManagementService({
  baseURL: 'http://localhost:8089', // Your API base URL
  timeout: 10000,
  onTokenExpired: () => {
    // Redirect to login or show modal
    window.location.href = '/login';
  },
  onError: (error) => {
    // Show toast notification or error message
    console.error('API Error:', error.detail);
  },
});
```

### 4. Use in React Components
```typescript
import { useAuth, useUsers } from './services/userService';

function UserManagement() {
  const auth = useAuth(userService);
  const users = useUsers(userService, { page: 1, limit: 20 });

  if (!auth.isAuthenticated) {
    return <LoginForm onLogin={auth.login} />;
  }

  if (!auth.hasPermission('canManageUsers')) {
    return <div>Access denied</div>;
  }

  return (
    <UserTable
      users={users.users}
      onUserUpdate={users.updateUser}
      onBulkOperation={users.bulkOperation}
    />
  );
}
```

## 🎯 Key Features

### ✅ **Type Safety**
- Full TypeScript support
- Compile-time error checking
- IntelliSense/autocomplete support
- Type guards for runtime validation

### 🔐 **Authentication**
- Automatic JWT token management
- Token expiration handling
- Permission-based UI rendering
- Role-based access control

### 🛡️ **Error Handling**
- Custom ApiError class
- Detailed error types and status codes
- Automatic retry mechanisms
- Global error handling hooks

### 🔄 **React Integration**
- Ready-to-use hooks (useAuth, useUsers)
- Automatic state management
- Loading and error states
- Optimistic updates

### 📊 **Permission System**
- Role-based permissions (user/admin/super_admin)
- Permission flags for UI elements
- Helper functions for access control
- Bulk operation permissions

## 🔐 Permission Matrix

| Feature | User | Admin | Super Admin |
|---------|------|-------|-------------|
| View own profile | ✅ | ✅ | ✅ |
| List users | ❌ | ✅ | ✅ |
| Update users | ❌ | ✅ | ✅ |
| Activate/Deactivate | ❌ | ✅ | ✅ |
| Make/Remove admin | ❌ | ❌ | ✅ |
| Delete users | ❌ | ❌ | ✅ |
| Bulk operations | ❌ | ✅* | ✅ |

*Admin can only perform safe bulk operations

## 📋 Implementation Checklist

### Authentication Flow
- [ ] Implement login form
- [ ] Handle magic link login
- [ ] Store JWT token securely
- [ ] Implement logout functionality
- [ ] Handle token expiration
- [ ] Add authentication guards

### User Management UI
- [ ] Create user list component
- [ ] Add pagination controls
- [ ] Implement search and filtering
- [ ] Add sorting functionality
- [ ] Create user details view
- [ ] Implement user edit form
- [ ] Add bulk action controls

### Permission-Based UI
- [ ] Hide/show elements based on permissions
- [ ] Implement role-based routing
- [ ] Add permission checks to actions
- [ ] Display appropriate error messages
- [ ] Handle unauthorized access

### Error Handling
- [ ] Implement global error handler
- [ ] Add toast notifications
- [ ] Handle network errors
- [ ] Show loading states
- [ ] Add retry mechanisms

### Testing
- [ ] Test all API endpoints
- [ ] Test permission scenarios
- [ ] Test error conditions
- [ ] Test token expiration
- [ ] Test bulk operations

## 🔧 Customization Guide

### Styling Integration
The service is UI-agnostic. Integrate with your preferred UI library:

```typescript
// Material-UI example
import { Alert, CircularProgress } from '@mui/material';

function UserList() {
  const { users, loading, error } = useUsers(userService);

  if (loading) return <CircularProgress />;
  if (error) return <Alert severity="error">{error.detail}</Alert>;

  return <UserTable users={users} />;
}

// Tailwind CSS example
function UserList() {
  const { users, loading, error } = useUsers(userService);

  if (loading) return <div className="spinner animate-spin" />;
  if (error) return <div className="bg-red-100 text-red-800 p-4 rounded">{error.detail}</div>;

  return <UserTable users={users} />;
}
```

### Adding Custom Endpoints
Extend the service class for additional functionality:

```typescript
class ExtendedUserService extends UserManagementService {
  async exportUsers(format: 'csv' | 'json'): Promise<Blob> {
    const response = await fetch(`${this.baseURL}/api/users/export?format=${format}`, {
      headers: { 'Authorization': `Bearer ${this.token}` }
    });
    return response.blob();
  }
}
```

### State Management Integration
Integrate with Redux, Zustand, or other state management:

```typescript
// Redux example
const userSlice = createSlice({
  name: 'users',
  initialState: { users: [], loading: false },
  reducers: {
    setUsers: (state, action) => {
      state.users = action.payload;
    },
    setLoading: (state, action) => {
      state.loading = action.payload;
    }
  }
});

// Zustand example
const useUserStore = create((set) => ({
  users: [],
  loading: false,
  setUsers: (users) => set({ users }),
  setLoading: (loading) => set({ loading })
}));
```

## 🐛 Troubleshooting

### Common Issues

**Authentication fails**
- Check if JWT token is properly stored
- Verify token hasn't expired
- Ensure Authorization header format: `Bearer <token>`

**Permission denied errors**
- Check user role and permissions
- Verify endpoint requires correct role level
- Check if user account is active

**Network errors**
- Verify API base URL is correct
- Check if backend server is running
- Ensure CORS is properly configured

**TypeScript errors**
- Update type definitions if API changes
- Check for missing null checks
- Verify enum values match API responses

### Debug Mode
Enable debug logging:

```typescript
const userService = new UserManagementService({
  baseURL: 'http://localhost:8089',
  onError: (error) => {
    console.error('API Error:', error);
    console.trace('Error stack trace');
  }
});
```

## 📞 Support

- **API Documentation**: Check the auto-generated docs at `http://localhost:8089/docs`
- **Interactive Testing**: Use the test page at `http://localhost:8089/api-test`
- **Health Check**: Monitor API status at `http://localhost:8089/health`

---

**Happy coding! 🚀**

The user management system is now ready for frontend integration with complete type safety, error handling, and React hooks.