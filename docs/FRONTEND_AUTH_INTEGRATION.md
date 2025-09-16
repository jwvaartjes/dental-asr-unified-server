# 🔐 Frontend Auth Integration Guide

**Complete authentication system with 8-hour tokens and auto-refresh**

## 🚀 Quick Start

### 1. **Install Dependencies**
```bash
# If using React Router
npm install react-router-dom

# If using TypeScript (recommended)
npm install --save-dev @types/react @types/react-dom
```

### 2. **Copy the Auth Hook**
Copy `useAuth.tsx` to your `src/hooks/` or `src/lib/` folder.

### 3. **Wrap Your App**
```tsx
// src/main.tsx or src/App.tsx
import { AuthProvider } from './hooks/useAuth';
import { BrowserRouter as Router } from 'react-router-dom';

function App() {
  return (
    <AuthProvider>
      <Router>
        <YourAppContent />
      </Router>
    </AuthProvider>
  );
}

export default App;
```

### 4. **Ready to Use!**
```tsx
import { useAuth } from './hooks/useAuth';

function LoginPage() {
  const { loginMagic, isLoading, error } = useAuth();

  // Magic link login - no password needed!
  const handleLogin = () => loginMagic('user@example.com');

  return (
    <button onClick={handleLogin} disabled={isLoading}>
      {isLoading ? 'Logging in...' : 'Login'}
    </button>
  );
}
```

---

## ✨ Features

### ✅ **Auto-login na refresh**
- Token wordt opgeslagen in localStorage
- Automatische verificatie bij app start
- Gebruiker blijft ingelogd na browser refresh

### ✅ **8 uur token levensduur**
- Backend configured voor 8 uur tokens
- Frontend checkt elke 30 minuten of token nog geldig is
- Automatische cleanup bij expiry

### ✅ **Magic Link Authentication**
- Geen wachtwoord nodig in development
- Gewoon email adres invoeren
- Perfect voor testing en development

### ✅ **Role-based toegang**
- `user`, `admin`, `super_admin` rollen
- Permission-based UI rendering
- Protected routes en componenten

### ✅ **TypeScript Support**
- Volledig getypeerd
- IntelliSense support
- Type-safe API calls

---

## 🛠️ API Configuratie

### Backend Settings (al geconfigureerd)
```python
# In app/settings.py
jwt_expiry_hours: int = 8  # 8 uur token levensduur
```

### Frontend Configuration
```tsx
// In useAuth.tsx - pas aan indien nodig
const AUTH_CONFIG = {
  API_BASE_URL: 'http://localhost:8089',
  TOKEN_KEY: 'auth_token',
  USER_KEY: 'user_data',
  REFRESH_BEFORE_EXPIRY: 30 * 60 * 1000, // 30 minuten voor expiry
  TOKEN_DURATION: 8 * 60 * 60 * 1000,    // 8 uur
} as const;
```

---

## 📝 Gebruik Voorbeelden

### **Basis Login Component**
```tsx
import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';

function LoginForm() {
  const { loginMagic, login, isLoading, error, clearError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleMagicLogin = async () => {
    const success = await loginMagic(email);
    if (success) {
      // Redirect of state update
      console.log('Logged in successfully!');
    }
  };

  const handleRegularLogin = async () => {
    const success = await login(email, password);
    if (success) {
      console.log('Logged in successfully!');
    }
  };

  return (
    <div className="login-form">
      <h2>Login</h2>

      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
        disabled={isLoading}
      />

      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password (optional in dev)"
        disabled={isLoading}
      />

      <button onClick={handleMagicLogin} disabled={isLoading}>
        {isLoading ? 'Logging in...' : 'Magic Link Login'}
      </button>

      <button onClick={handleRegularLogin} disabled={isLoading}>
        {isLoading ? 'Logging in...' : 'Regular Login'}
      </button>

      {error && (
        <div className="error">
          {error}
          <button onClick={clearError}>×</button>
        </div>
      )}
    </div>
  );
}
```

### **Dashboard met User Info**
```tsx
import { useAuth, usePermission, useRole } from '../hooks/useAuth';

function Dashboard() {
  const { user, logout, isAuthenticated } = useAuth();
  const canManageUsers = usePermission('canManageUsers');
  const role = useRole();

  if (!isAuthenticated) {
    return <div>Please log in</div>;
  }

  return (
    <div className="dashboard">
      <header>
        <h1>Welcome, {user?.name || user?.email}</h1>
        <div className="user-info">
          <span>Role: {role}</span>
          <button onClick={logout}>Logout</button>
        </div>
      </header>

      <main>
        <p>Email: {user?.email}</p>
        <p>ID: {user?.id}</p>

        {canManageUsers && (
          <section className="admin-section">
            <h2>Admin Controls</h2>
            <button>Manage Users</button>
          </section>
        )}

        {user?.permissions.isSuperAdmin && (
          <section className="super-admin-section">
            <h2>Super Admin Controls</h2>
            <button>System Settings</button>
          </section>
        )}
      </main>
    </div>
  );
}
```

### **Protected Routes**
```tsx
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth, withAuth, withRole } from '../hooks/useAuth';

// Protected components
const ProtectedDashboard = withAuth(Dashboard);
const AdminPanel = withRole(AdminSettings, 'admin');
const SuperAdminPanel = withRole(SuperAdminSettings, 'super_admin');

function AppRoutes() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div>Loading...</div>;
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginForm />} />

      {/* Public routes */}
      <Route path="/" element={<HomePage />} />

      {/* Protected routes */}
      <Route
        path="/dashboard"
        element={
          isAuthenticated ?
            <ProtectedDashboard /> :
            <Navigate to="/login" />
        }
      />

      <Route path="/admin" element={<AdminPanel />} />
      <Route path="/super-admin" element={<SuperAdminPanel />} />

      {/* Redirect unknown routes */}
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}
```

### **Conditionale UI Rendering**
```tsx
import { useAuth, usePermission } from '../hooks/useAuth';

function Navigation() {
  const { isAuthenticated, user, logout } = useAuth();
  const canManageUsers = usePermission('canManageUsers');

  return (
    <nav>
      <div className="nav-links">
        <a href="/">Home</a>

        {isAuthenticated ? (
          <>
            <a href="/dashboard">Dashboard</a>
            {canManageUsers && <a href="/admin">Admin</a>}
            {user?.permissions.isSuperAdmin && <a href="/super-admin">Super Admin</a>}
          </>
        ) : (
          <a href="/login">Login</a>
        )}
      </div>

      {isAuthenticated && (
        <div className="user-menu">
          <span>Hello, {user?.name}</span>
          <button onClick={logout}>Logout</button>
        </div>
      )}
    </nav>
  );
}
```

---

## 🔧 Geavanceerde Configuratie

### **Custom API URLs**
```tsx
// Voor production
const AUTH_CONFIG = {
  API_BASE_URL: process.env.REACT_APP_API_URL || 'http://localhost:8089',
  // ... rest of config
};
```

### **Error Handling**
```tsx
function LoginWithErrorHandling() {
  const { loginMagic, error, clearError } = useAuth();

  const handleLogin = async (email: string) => {
    clearError(); // Clear previous errors

    try {
      const success = await loginMagic(email);
      if (success) {
        // Handle success
      } else {
        // Handle failure (error is already set in state)
      }
    } catch (err) {
      // Handle unexpected errors
      console.error('Login error:', err);
    }
  };

  return (
    <div>
      {/* Login form */}
      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={clearError}>Dismiss</button>
        </div>
      )}
    </div>
  );
}
```

### **Loading States**
```tsx
function AppWithLoading() {
  const { isLoading, isAuthenticated } = useAuth();

  if (isLoading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
        <p>Loading...</p>
      </div>
    );
  }

  return isAuthenticated ? <AuthenticatedApp /> : <UnauthenticatedApp />;
}
```

---

## 🧪 Testing

### **Test Login**
```tsx
// Test accounts (development only)
const testLogin = async () => {
  // Any email with 'admin' becomes admin
  await loginMagic('admin@test.com');

  // Any other email becomes regular user
  await loginMagic('user@test.com');
};
```

### **Check Token in DevTools**
```javascript
// In browser console
localStorage.getItem('auth_token');
localStorage.getItem('user_data');
```

---

## 🔒 Security Notes

1. **Development vs Production**:
   - Development: Any password accepted
   - Production: Implement proper password validation

2. **Token Storage**:
   - localStorage is used (persistent across tabs)
   - Consider sessionStorage for single-tab sessions

3. **Auto-refresh**:
   - Token checked every 30 minutes
   - Invalid tokens trigger automatic logout

4. **CORS**:
   - Origin header required for API calls
   - Backend configured for localhost:5173

---

## ❓ Troubleshooting

**Token not persisting after refresh?**
- Check browser localStorage in DevTools
- Verify AUTH_CONFIG.TOKEN_KEY matches

**CORS errors?**
- Check Origin header in requests
- Verify backend CORS settings

**Magic login not working?**
- Check backend logs
- Verify email format
- Test with 'admin@test.com'

**User roles not working?**
- Check user permissions in localStorage
- Verify backend role assignment

---

## 🎯 Next Steps

1. **Copy files** to your React project
2. **Install dependencies**
3. **Wrap App** with AuthProvider
4. **Add login form** with useAuth hook
5. **Protect routes** with withAuth/withRole
6. **Test login flow** with test emails
7. **Customize styling** and error messages

---

## 🔌 WebSocket Integration with Authentication

### **WebSocket Authentication Flow**
```typescript
// Complete WebSocket setup with Bearer token
const useAuthenticatedWebSocket = () => {
  const { token, isAuthenticated, refreshToken } = useAuth();
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  const connectWebSocket = useCallback(async () => {
    if (!isAuthenticated || !token) return;

    try {
      // Get WebSocket-specific token
      const wsTokenResponse = await fetch('/api/auth/ws-token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'Origin': window.location.origin
        }
      });

      if (wsTokenResponse.status === 429) {
        // Rate limited - wait and retry
        console.warn('WebSocket token request rate limited');
        setTimeout(() => connectWebSocket(), 5000);
        return;
      }

      if (!wsTokenResponse.ok) {
        throw new Error(`WebSocket token failed: ${wsTokenResponse.status}`);
      }

      const { token: wsToken } = await wsTokenResponse.json();

      // Create WebSocket with Bearer token in subprotocol
      const websocket = new WebSocket(
        'ws://localhost:8089/ws',
        [`Bearer.${wsToken}`]
      );

      websocket.onopen = () => {
        setIsConnected(true);
        setWs(websocket);
      };

      websocket.onclose = () => {
        setIsConnected(false);
        setWs(null);

        // Auto-reconnect if still authenticated
        if (isAuthenticated) {
          setTimeout(() => connectWebSocket(), 3000);
        }
      };

    } catch (error) {
      console.error('WebSocket connection failed:', error);
    }
  }, [isAuthenticated, token]);

  useEffect(() => {
    if (isAuthenticated) {
      connectWebSocket();
    }
    return () => ws?.close();
  }, [isAuthenticated, connectWebSocket]);

  return { ws, isConnected };
};
```

### **Rate Limit Friendly Token Management**
```typescript
// Enhanced token management with rate limiting
const useWebSocketToken = () => {
  const [wsToken, setWsToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const maxRetries = 5;

  const getWebSocketToken = useCallback(async () => {
    if (isLoading) return; // Prevent multiple simultaneous requests

    setIsLoading(true);

    try {
      const response = await fetch('/api/auth/ws-token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Origin': window.location.origin
        }
      });

      if (response.status === 429) {
        // Rate limited - exponential backoff
        const delay = Math.pow(2, retryCount) * 1000; // 1s, 2s, 4s, 8s, 16s
        console.warn(`Rate limited. Retrying in ${delay}ms`);

        if (retryCount < maxRetries) {
          setTimeout(() => {
            setRetryCount(prev => prev + 1);
            getWebSocketToken();
          }, delay);
        }
        return;
      }

      if (!response.ok) {
        throw new Error(`Token request failed: ${response.status}`);
      }

      const { token } = await response.json();
      setWsToken(token);
      setRetryCount(0); // Reset on success

    } catch (error) {
      console.error('Failed to get WebSocket token:', error);
    } finally {
      setIsLoading(false);
    }
  }, [retryCount, isLoading]);

  return { wsToken, getWebSocketToken, isLoading };
};
```

### **Complete Authentication + WebSocket Hook**
```typescript
// Combined auth and WebSocket management
const useAuthWebSocket = () => {
  const auth = useAuth();
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const sendMessage = useCallback((message: any) => {
    if (ws && isConnected) {
      ws.send(JSON.stringify(message));
    } else {
      console.warn('Cannot send message: WebSocket not connected');
    }
  }, [ws, isConnected]);

  const joinChannel = useCallback((channelId: string, deviceType: 'desktop' | 'mobile') => {
    const sessionId = `${deviceType}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    sendMessage({
      type: "join_channel",
      channel: channelId,        // ✅ CORRECT: "channel" not "channelId"
      device_type: deviceType,
      session_id: sessionId      // ✅ REQUIRED field
    });
  }, [sendMessage]);

  // WebSocket connection logic
  useEffect(() => {
    if (!auth.isAuthenticated) {
      ws?.close();
      return;
    }

    const connectWebSocket = async () => {
      try {
        setConnectionError(null);

        // Get WebSocket token
        const tokenResponse = await fetch('/api/auth/ws-token', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Origin': window.location.origin
          }
        });

        if (tokenResponse.status === 429) {
          setConnectionError('Rate limited. Please wait...');
          return;
        }

        if (!tokenResponse.ok) {
          throw new Error(`Token failed: ${tokenResponse.status}`);
        }

        const { token } = await tokenResponse.json();

        // Create WebSocket with Bearer authentication
        const websocket = new WebSocket(
          'ws://localhost:8089/ws',
          [`Bearer.${token}`]
        );

        websocket.onopen = () => {
          setIsConnected(true);
          setWs(websocket);
          setConnectionError(null);

          // Send identification
          websocket.send(JSON.stringify({
            type: "identify",
            device_type: "desktop", // or "mobile"
            session_id: `session-${Date.now()}`
          }));
        };

        websocket.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            console.log('📥 WebSocket message:', message);

            // Handle server messages
            if (message.type === 'error') {
              setConnectionError(message.message);
            }
          } catch (parseError) {
            console.error('Failed to parse WebSocket message:', parseError);
          }
        };

        websocket.onclose = (event) => {
          setIsConnected(false);
          setWs(null);
          console.log('WebSocket closed:', event.code, event.reason);

          // Auto-reconnect if still authenticated
          if (auth.isAuthenticated && event.code !== 1000) {
            setTimeout(() => connectWebSocket(), 3000);
          }
        };

        websocket.onerror = (error) => {
          console.error('WebSocket error:', error);
          setConnectionError('Connection failed');
        };

      } catch (error: any) {
        console.error('WebSocket connection failed:', error);
        setConnectionError(error.message);
      }
    };

    connectWebSocket();

    return () => {
      ws?.close();
    };
  }, [auth.isAuthenticated]);

  return {
    ...auth,
    ws,
    isConnected,
    connectionError,
    sendMessage,
    joinChannel
  };
};
```

### **Usage in React Component**
```typescript
function AuthenticatedPairingApp() {
  const {
    isAuthenticated,
    user,
    logout,
    isConnected,
    connectionError,
    joinChannel
  } = useAuthWebSocket();

  const [channelId, setChannelId] = useState('');

  if (!isAuthenticated) {
    return <LoginComponent />;
  }

  return (
    <div className="app">
      <header>
        <h1>Welcome, {user?.name}</h1>
        <div className="status">
          Auth: {isAuthenticated ? '🟢' : '🔴'} |
          WebSocket: {isConnected ? '🟢' : '🔴'}
        </div>
        <button onClick={logout}>Logout</button>
      </header>

      {connectionError && (
        <div className="error">❌ {connectionError}</div>
      )}

      <main>
        <div className="pairing-section">
          <input
            type="text"
            value={channelId}
            onChange={(e) => setChannelId(e.target.value)}
            placeholder="Channel ID (e.g., pair-123456)"
          />
          <button
            onClick={() => joinChannel(channelId, 'desktop')}
            disabled={!isConnected || !channelId}
          >
            Join Channel
          </button>
        </div>
      </main>
    </div>
  );
}
```

---

## 🚨 WebSocket Critical Points

### **Field Names Matter!**
```typescript
// ❌ WRONG - Will cause validation error
{
  type: "join_channel",
  channelId: "pair-123456",  // Should be "channel"
  device_type: "desktop"     // Missing "session_id"
}

// ✅ CORRECT
{
  type: "join_channel",
  channel: "pair-123456",    // Correct field name
  device_type: "desktop",
  session_id: "session-123"  // Required field
}
```

### **Rate Limiting Prevention**
```typescript
// ❌ WRONG - Causes rate limit spam
useEffect(() => {
  getWebSocketToken(); // No dependencies = infinite loop!
});

// ✅ CORRECT - Controlled execution
useEffect(() => {
  if (isAuthenticated) {
    getWebSocketToken();
  }
}, [isAuthenticated]); // Proper dependencies

// ✅ CORRECT - With retry delays
const retryWithExponentialBackoff = (attempt: number) => {
  const delay = Math.min(Math.pow(2, attempt) * 1000, 30000); // Max 30 seconds
  setTimeout(() => {
    getWebSocketToken();
  }, delay);
};
```

---

De authenticatie is nu **production-ready** met 8-uur tokens, automatic refresh, én WebSocket Bearer token authenticatie! 🚀