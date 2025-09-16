/**
 * Complete Authentication Hook for React
 * Features: Auto-login after refresh, 8-hour tokens, auto-refresh, localStorage
 */

import { useState, useEffect, useCallback, createContext, useContext } from 'react';

// ============================================================================
// Types
// ============================================================================

interface User {
  id: string;
  email: string;
  name: string;
  role: 'user' | 'admin' | 'super_admin';
  permissions: {
    canManageUsers: boolean;
    canDeleteUsers: boolean;
    canModifyAdminRoles: boolean;
    isSuperAdmin: boolean;
  };
}

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: User | null;
  token: string | null;
  error: string | null;
}

interface AuthContextType extends AuthState {
  login: (email: string, password?: string) => Promise<boolean>;
  loginMagic: (email: string) => Promise<boolean>;
  logout: () => void;
  refreshToken: () => Promise<boolean>;
  clearError: () => void;
}

// ============================================================================
// Configuration
// ============================================================================

const AUTH_CONFIG = {
  API_BASE_URL: 'http://localhost:8089',
  TOKEN_KEY: 'auth_token',
  USER_KEY: 'user_data',
  REFRESH_BEFORE_EXPIRY: 30 * 60 * 1000, // 30 minutes before expiry
  TOKEN_DURATION: 8 * 60 * 60 * 1000, // 8 hours in milliseconds
} as const;

// ============================================================================
// Auth Context
// ============================================================================

const AuthContext = createContext<AuthContextType | null>(null);

// ============================================================================
// Auth Hook
// ============================================================================

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// ============================================================================
// Auth Provider Hook (Internal)
// ============================================================================

const useAuthProvider = (): AuthContextType => {
  const [state, setState] = useState<AuthState>({
    isAuthenticated: false,
    isLoading: true,
    user: null,
    token: null,
    error: null,
  });

  // ============================================================================
  // Helper Functions
  // ============================================================================

  const setError = (error: string) => {
    setState(prev => ({ ...prev, error, isLoading: false }));
  };

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  const setAuthData = useCallback((token: string, user: User) => {
    // Store in localStorage
    localStorage.setItem(AUTH_CONFIG.TOKEN_KEY, token);
    localStorage.setItem(AUTH_CONFIG.USER_KEY, JSON.stringify(user));

    // Update state
    setState({
      isAuthenticated: true,
      isLoading: false,
      user,
      token,
      error: null,
    });
  }, []);

  const clearAuthData = useCallback(() => {
    // Clear localStorage
    localStorage.removeItem(AUTH_CONFIG.TOKEN_KEY);
    localStorage.removeItem(AUTH_CONFIG.USER_KEY);

    // Clear state
    setState({
      isAuthenticated: false,
      isLoading: false,
      user: null,
      token: null,
      error: null,
    });
  }, []);

  // ============================================================================
  // API Functions
  // ============================================================================

  const makeAuthRequest = async (endpoint: string, body?: any) => {
    const response = await fetch(`${AUTH_CONFIG.API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Origin': window.location.origin,
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: 'Network error' }));
      throw new Error(errorData.message || `HTTP ${response.status}`);
    }

    return response.json();
  };

  const verifyToken = async (token: string): Promise<boolean> => {
    try {
      const response = await fetch(`${AUTH_CONFIG.API_BASE_URL}/api/auth/verify`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Origin': window.location.origin,
        },
      });

      return response.ok;
    } catch (error) {
      console.error('Token verification failed:', error);
      return false;
    }
  };

  // ============================================================================
  // Auth Methods
  // ============================================================================

  const login = useCallback(async (email: string, password?: string): Promise<boolean> => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));

      const data = await makeAuthRequest('/api/auth/login', {
        email,
        password: password || 'dummy', // Backend accepts any password in dev
      });

      if (data.success && data.token && data.user) {
        setAuthData(data.token, data.user);
        return true;
      } else {
        setError('Login failed: Invalid response');
        return false;
      }
    } catch (error: any) {
      setError(`Login failed: ${error.message}`);
      return false;
    }
  }, [setAuthData]);

  const loginMagic = useCallback(async (email: string): Promise<boolean> => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));

      const data = await makeAuthRequest('/api/auth/login-magic', { email });

      if (data.success && data.token && data.user) {
        setAuthData(data.token, data.user);
        return true;
      } else {
        setError('Magic login failed: Invalid response');
        return false;
      }
    } catch (error: any) {
      setError(`Magic login failed: ${error.message}`);
      return false;
    }
  }, [setAuthData]);

  const logout = useCallback(() => {
    clearAuthData();
  }, [clearAuthData]);

  const refreshToken = useCallback(async (): Promise<boolean> => {
    try {
      const currentToken = localStorage.getItem(AUTH_CONFIG.TOKEN_KEY);
      if (!currentToken) return false;

      // For now, we'll just verify the existing token
      // You could implement a dedicated refresh endpoint
      const isValid = await verifyToken(currentToken);

      if (!isValid) {
        clearAuthData();
        return false;
      }

      return true;
    } catch (error) {
      console.error('Token refresh failed:', error);
      clearAuthData();
      return false;
    }
  }, [clearAuthData]);

  // ============================================================================
  // Initialization & Auto-refresh
  // ============================================================================

  // Check authentication status on mount
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const token = localStorage.getItem(AUTH_CONFIG.TOKEN_KEY);
        const userDataStr = localStorage.getItem(AUTH_CONFIG.USER_KEY);

        if (!token || !userDataStr) {
          setState(prev => ({ ...prev, isLoading: false }));
          return;
        }

        // Verify token is still valid
        const isValid = await verifyToken(token);

        if (isValid) {
          try {
            const userData = JSON.parse(userDataStr);
            setState({
              isAuthenticated: true,
              isLoading: false,
              user: userData,
              token,
              error: null,
            });
          } catch (parseError) {
            console.error('Failed to parse user data:', parseError);
            clearAuthData();
          }
        } else {
          // Token expired or invalid
          clearAuthData();
        }
      } catch (error) {
        console.error('Auth initialization failed:', error);
        clearAuthData();
      }
    };

    initializeAuth();
  }, [clearAuthData]);

  // Auto-refresh token before it expires
  useEffect(() => {
    if (!state.isAuthenticated || !state.token) return;

    const refreshInterval = setInterval(async () => {
      console.log('Checking token validity...');
      const success = await refreshToken();
      if (!success) {
        console.log('Token refresh failed, logging out');
      }
    }, AUTH_CONFIG.REFRESH_BEFORE_EXPIRY);

    return () => clearInterval(refreshInterval);
  }, [state.isAuthenticated, state.token, refreshToken]);

  // Return the auth context value
  return {
    ...state,
    login,
    loginMagic,
    logout,
    refreshToken,
    clearError,
  };
};

// ============================================================================
// Auth Provider Component
// ============================================================================

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const auth = useAuthProvider();
  return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>;
};

// ============================================================================
// Helper Hooks
// ============================================================================

// Hook for getting just the user info
export const useUser = (): User | null => {
  const { user } = useAuth();
  return user;
};

// Hook for checking if user has specific permission
export const usePermission = (permission: keyof User['permissions']): boolean => {
  const { user } = useAuth();
  return user?.permissions[permission] || false;
};

// Hook for role-based access
export const useRole = (): User['role'] | null => {
  const { user } = useAuth();
  return user?.role || null;
};

// ============================================================================
// Higher-Order Components
// ============================================================================

// HOC for protecting routes
export const withAuth = <P extends object>(
  Component: React.ComponentType<P>
): React.ComponentType<P> => {
  return (props: P) => {
    const { isAuthenticated, isLoading } = useAuth();

    if (isLoading) {
      return <div>Loading...</div>;
    }

    if (!isAuthenticated) {
      return <div>Please log in to access this page.</div>;
    }

    return <Component {...props} />;
  };
};

// HOC for role-based protection
export const withRole = <P extends object>(
  Component: React.ComponentType<P>,
  requiredRole: User['role']
): React.ComponentType<P> => {
  return (props: P) => {
    const { user, isAuthenticated, isLoading } = useAuth();

    if (isLoading) {
      return <div>Loading...</div>;
    }

    if (!isAuthenticated) {
      return <div>Please log in to access this page.</div>;
    }

    if (user?.role !== requiredRole) {
      return <div>You don't have permission to access this page.</div>;
    }

    return <Component {...props} />;
  };
};

// ============================================================================
// Usage Examples (commented out)
// ============================================================================

/*
// 1. Wrap your app with AuthProvider
function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/dashboard" element={<ProtectedDashboard />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

// 2. Use in login component
function LoginPage() {
  const { login, loginMagic, isLoading, error } = useAuth();
  const [email, setEmail] = useState('');

  const handleLogin = async () => {
    const success = await loginMagic(email);
    if (success) {
      // Redirect to dashboard
      navigate('/dashboard');
    }
  };

  return (
    <div>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
      />
      <button onClick={handleLogin} disabled={isLoading}>
        {isLoading ? 'Logging in...' : 'Login with Magic Link'}
      </button>
      {error && <p style={{color: 'red'}}>{error}</p>}
    </div>
  );
}

// 3. Use in protected component
function Dashboard() {
  const { user, logout } = useAuth();
  const canManageUsers = usePermission('canManageUsers');

  return (
    <div>
      <h1>Welcome, {user?.name}</h1>
      <p>Role: {user?.role}</p>
      {canManageUsers && <button>Manage Users</button>}
      <button onClick={logout}>Logout</button>
    </div>
  );
}

// 4. Protected route component
const ProtectedDashboard = withAuth(Dashboard);

// 5. Admin-only component
const AdminPanel = withRole(AdminSettings, 'admin');
*/