# Simple Unified Auth Guide: HttpOnly Cookie Ready

## 🎯 **Goal: Zero Token Management**

Deze guide laat zien hoe je een **super simpele** unified auth maakt die perfect werkt met httpOnly cookies. Geen complex storage management, geen migrations - gewoon clean, simple code.

### **Key Principle:**
```typescript
// Met httpOnly cookies hoef je GEEN tokens te managen!
// Browser doet alles automatisch
```

## 🏗️ **Architecture Overview**

```
Simpele Unified Auth:
├── src/stores/authStore.ts     # Single Zustand store
├── src/hooks/useAuth.ts        # Simple auth hook
└── src/utils/api.ts            # Fetch with credentials: 'include'

NO NEED FOR:
❌ Storage layers
❌ Token encryption
❌ Device detection
❌ Complex migrations
```

## 📝 **Step 1: Create Simple Auth Store**

```typescript
// src/stores/authStore.ts
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  permissions: {
    canManageUsers: boolean;
    canDeleteUsers: boolean;
    canModifyAdminRoles: boolean;
    isSuperAdmin: boolean;
  };
}

interface AuthState {
  // State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  devtools(
    (set) => ({
      // Initial state
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Actions (immutable updates)
      setUser: (user) => set(
        (state) => ({
          ...state,
          user,
          isAuthenticated: !!user,
          error: null
        }),
        false,
        'auth/setUser'
      ),

      setLoading: (isLoading) => set(
        (state) => ({ ...state, isLoading }),
        false,
        'auth/setLoading'
      ),

      setError: (error) => set(
        (state) => ({ ...state, error, isLoading: false }),
        false,
        'auth/setError'
      ),

      clearAuth: () => set(
        () => ({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: null
        }),
        false,
        'auth/clearAuth'
      ),
    }),
    { name: 'auth-store' }
  )
);
```

## 📡 **Step 2: Create API Utility**

```typescript
// src/utils/api.ts
const API_BASE = 'http://localhost:8089/api';

interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
}

// Helper for making authenticated requests
export const apiCall = async <T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> => {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      credentials: 'include', // ✅ CRITICAL: Enables httpOnly cookies
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    const data = await response.json();

    if (!response.ok) {
      return {
        success: false,
        error: data.detail || 'Request failed'
      };
    }

    return {
      success: true,
      data
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Network error'
    };
  }
};

// Auth-specific API calls
export const authApi = {
  login: (email: string, password?: string) =>
    apiCall('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    }),

  magicLogin: (email: string) =>
    apiCall('/auth/login-magic', {
      method: 'POST',
      body: JSON.stringify({ email })
    }),

  checkStatus: () => apiCall('/auth/status'),

  logout: () => apiCall('/auth/logout', { method: 'POST' }),

  verify: () => apiCall('/auth/verify')
};
```

## 🎯 **Step 3: Create Simple Auth Hook**

```typescript
// src/hooks/useAuth.ts
import { useAuthStore } from '../stores/authStore';
import { authApi } from '../utils/api';

export const useAuth = () => {
  const {
    user,
    isAuthenticated,
    isLoading,
    error,
    setUser,
    setLoading,
    setError,
    clearAuth
  } = useAuthStore();

  // Login function
  const login = async (email: string, password?: string): Promise<boolean> => {
    setLoading(true);
    setError(null);

    try {
      // Use magic login if no password provided
      const response = password
        ? await authApi.login(email, password)
        : await authApi.magicLogin(email);

      if (response.success && response.data) {
        setUser(response.data.user);
        return true;
      } else {
        setError(response.error || 'Login failed');
        return false;
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Login failed');
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Logout function
  const logout = async (): Promise<void> => {
    setLoading(true);

    try {
      await authApi.logout(); // Clear cookie on server
      clearAuth(); // Clear local state
    } catch (error) {
      console.error('Logout error:', error);
      clearAuth(); // Clear anyway
    } finally {
      setLoading(false);
    }
  };

  // Check auth status (useful for app initialization)
  const checkAuthStatus = async (): Promise<boolean> => {
    setLoading(true);

    try {
      const response = await authApi.checkStatus();

      if (response.success && response.data) {
        setUser(response.data.user);
        return true;
      } else {
        clearAuth();
        return false;
      }
    } catch (error) {
      clearAuth();
      return false;
    } finally {
      setLoading(false);
    }
  };

  return {
    // State
    user,
    isAuthenticated,
    isLoading,
    error,

    // Actions
    login,
    logout,
    checkAuthStatus,
    clearError: () => setError(null)
  };
};
```

## 🚀 **Step 4: App Initialization**

```typescript
// src/App.tsx
import React, { useEffect, useState } from 'react';
import { useAuth } from './hooks/useAuth';

function App() {
  const { checkAuthStatus } = useAuth();
  const [initComplete, setInitComplete] = useState(false);

  useEffect(() => {
    const initializeAuth = async () => {
      // Check if user is already authenticated via httpOnly cookie
      await checkAuthStatus();
      setInitComplete(true);
    };

    initializeAuth();
  }, [checkAuthStatus]);

  // Show loading during initialization
  if (!initComplete) {
    return <div>Loading...</div>;
  }

  return (
    <div className="App">
      <AuthenticatedApp />
    </div>
  );
}

function AuthenticatedApp() {
  const { isAuthenticated } = useAuth();

  return isAuthenticated ? <Dashboard /> : <LoginPage />;
}
```

## 🔐 **Step 5: Login Component**

```typescript
// src/components/LoginPage.tsx
import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';

export const LoginPage: React.FC = () => {
  const { login, isLoading, error } = useAuth();
  const [email, setEmail] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email) return;

    const success = await login(email); // Magic login

    if (success) {
      console.log('✅ Login successful');
      // User will be redirected automatically by App.tsx
    }
  };

  return (
    <div>
      <h1>Login</h1>

      <form onSubmit={handleLogin}>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Enter your email"
          disabled={isLoading}
        />

        <button type="submit" disabled={isLoading || !email}>
          {isLoading ? 'Logging in...' : 'Login'}
        </button>
      </form>

      {error && (
        <div style={{ color: 'red' }}>
          Error: {error}
        </div>
      )}
    </div>
  );
};
```

## 📊 **Step 6: Dashboard Component**

```typescript
// src/components/Dashboard.tsx
import React from 'react';
import { useAuth } from '../hooks/useAuth';

export const Dashboard: React.FC = () => {
  const { user, logout, isLoading } = useAuth();

  const handleLogout = async () => {
    await logout();
    console.log('✅ Logged out');
  };

  return (
    <div>
      <h1>Dashboard</h1>

      <div>
        <h2>Welcome, {user?.name}!</h2>
        <p>Email: {user?.email}</p>
        <p>Role: {user?.role}</p>
      </div>

      <button onClick={handleLogout} disabled={isLoading}>
        {isLoading ? 'Logging out...' : 'Logout'}
      </button>
    </div>
  );
};
```

## 🧪 **Testing Your Implementation**

### **Test 1: Login Flow**
```typescript
// In browser console after login:
console.log('Auth store state:', useAuthStore.getState());
// Should show: { user: {...}, isAuthenticated: true, ... }
```

### **Test 2: Cookie Verification**
```javascript
// In browser dev tools:
// Application → Cookies → localhost:8089
// Should see: session_token (httpOnly: true)
```

### **Test 3: Page Refresh**
1. Log in
2. Refresh page
3. Should stay logged in (cookie persists)

### **Test 4: Cross-tab Behavior**
1. Log in in tab 1
2. Open tab 2 with same app
3. Should be automatically logged in

## 🎉 **What You Get**

### **✅ Benefits:**
- **Super Simple**: Only ~100 lines of code total
- **HttpOnly Ready**: Perfect for backend cookie implementation
- **Zero Token Management**: Browser handles everything
- **Immutable Updates**: Clean Zustand patterns
- **TypeScript**: Full type safety
- **Automatic Inheritance**: Works across tabs/devices

### **✅ No Need For:**
- ❌ Storage encryption
- ❌ Device detection
- ❌ Complex migrations
- ❌ Token refresh logic
- ❌ Storage cleanup

### **✅ Perfect Timing:**
- Works immediately with httpOnly cookies
- No breaking changes when backend switches
- Clean foundation for future features

## 📋 **Implementation Checklist**

### **Create Files:**
- [ ] `src/stores/authStore.ts` - Zustand store
- [ ] `src/utils/api.ts` - API utilities
- [ ] `src/hooks/useAuth.ts` - Auth hook
- [ ] `src/components/LoginPage.tsx` - Login UI
- [ ] `src/components/Dashboard.tsx` - Protected UI

### **Update Files:**
- [ ] `src/App.tsx` - Add auth initialization
- [ ] Remove old auth files (after testing)

### **Test:**
- [ ] Login/logout flow
- [ ] Page refresh persistence
- [ ] Error handling
- [ ] TypeScript compilation

**Result: Clean, simple auth that's ready for httpOnly cookies!** 🚀