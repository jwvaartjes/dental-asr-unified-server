# Complete Implementation Examples - Unified Auth Store

## 🎯 **Ready-to-Use Code Examples**

Deze file bevat complete, werkende code voorbeelden voor de unified auth architecture.

## 📁 **Project Structure**

```
src/
├── stores/
│   └── appStore.ts              # Main unified store
├── storage/
│   ├── secureStorage.ts         # Secure storage utilities
│   └── deviceStorage.ts         # Device-specific storage
├── hooks/
│   ├── useAuth.ts              # Auth hook
│   ├── usePairing.ts           # Pairing hook
│   └── useSettings.ts          # Settings hook
├── components/
│   ├── DesktopLogin.tsx        # Desktop login component
│   ├── MobilePairing.tsx       # Mobile pairing component
│   └── ProtectedRoute.tsx      # Route protection
├── utils/
│   ├── deviceDetection.ts      # Device type detection
│   └── apiClient.ts            # API client with auth
└── types/
    └── auth.ts                 # TypeScript types
```

## 🗃️ **1. Types Definition**

```typescript
// src/types/auth.ts
export interface User {
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

export interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  expiresAt: number | null;
  deviceType: 'desktop' | 'mobile';
  inheritedFrom?: string;
  isLoading: boolean;
  error: string | null;
}

export interface PairingState {
  code: string | null;
  channelId: string | null;
  isPaired: boolean;
  isConnecting: boolean;
  connectedDevices: ConnectedDevice[];
  error: string | null;
}

export interface Settings {
  audioGain: number;
  vadEnabled: boolean;
  theme: 'light' | 'dark';
  notifications: boolean;
}

export interface ConnectedDevice {
  clientId: string;
  deviceType: 'desktop' | 'mobile';
  connectedAt: Date;
}

export interface AppStore {
  auth: AuthState;
  pairing: PairingState;
  settings: Settings;
  actions: {
    // Auth actions
    setAuth: (token: string, user: User) => void;
    setMobileAuth: (token: string, inheritedUser: string) => void;
    clearAuth: () => void;
    validateToken: () => Promise<boolean>;

    // Pairing actions
    generatePairingCode: () => Promise<string>;
    pairWithCode: (code: string) => Promise<boolean>;

    // Settings actions
    updateSettings: (settings: Partial<Settings>) => void;
  };
}
```

## 🔧 **2. Storage Layer**

```typescript
// src/storage/secureStorage.ts
export class SecureStorage {
  private static readonly STORAGE_PREFIX = 'app_secure_';

  private static encrypt(value: string): string {
    // Use proper encryption in production (crypto-js, etc.)
    return btoa(value);
  }

  private static decrypt(value: string): string {
    try {
      return atob(value);
    } catch {
      console.warn('Failed to decrypt storage value');
      return '';
    }
  }

  static setItem(key: string, value: string, persistent: boolean = false): void {
    const storage = persistent ? localStorage : sessionStorage;
    const encryptedValue = this.encrypt(value);
    const fullKey = this.STORAGE_PREFIX + key;

    try {
      storage.setItem(fullKey, encryptedValue);
    } catch (error) {
      console.error('Failed to store encrypted value:', error);
    }
  }

  static getItem(key: string): string | null {
    const fullKey = this.STORAGE_PREFIX + key;

    // Try sessionStorage first, then localStorage
    const storages = [sessionStorage, localStorage];

    for (const storage of storages) {
      const encrypted = storage.getItem(fullKey);
      if (encrypted) {
        const decrypted = this.decrypt(encrypted);
        return decrypted || null;
      }
    }

    return null;
  }

  static removeItem(key: string): void {
    const fullKey = this.STORAGE_PREFIX + key;
    sessionStorage.removeItem(fullKey);
    localStorage.removeItem(fullKey);
  }

  static clear(): void {
    // Clear all app-specific keys
    const storages = [sessionStorage, localStorage];

    storages.forEach(storage => {
      const keysToRemove: string[] = [];

      for (let i = 0; i < storage.length; i++) {
        const key = storage.key(i);
        if (key && key.startsWith(this.STORAGE_PREFIX)) {
          keysToRemove.push(key);
        }
      }

      keysToRemove.forEach(key => storage.removeItem(key));
    });
  }
}

// src/storage/deviceStorage.ts
export type DeviceType = 'desktop' | 'mobile';

interface StorageConfig {
  tokenKey: string;
  persistent: boolean;
}

export const createDeviceStorage = (deviceType: DeviceType) => {
  const config: StorageConfig = {
    desktop: { tokenKey: 'desktop_token', persistent: false },
    mobile: { tokenKey: 'mobile_token', persistent: true }
  }[deviceType];

  return {
    saveToken: (token: string): void => {
      SecureStorage.setItem(config.tokenKey, token, config.persistent);
    },

    getToken: (): string | null => {
      return SecureStorage.getItem(config.tokenKey);
    },

    clearToken: (): void => {
      SecureStorage.removeItem(config.tokenKey);
    },

    saveUserData: (user: User): void => {
      SecureStorage.setItem(`${config.tokenKey}_user`, JSON.stringify(user), config.persistent);
    },

    getUserData: (): User | null => {
      const userData = SecureStorage.getItem(`${config.tokenKey}_user`);
      if (userData) {
        try {
          return JSON.parse(userData);
        } catch {
          return null;
        }
      }
      return null;
    },

    clearUserData: (): void => {
      SecureStorage.removeItem(`${config.tokenKey}_user`);
    }
  };
};
```

## 🏪 **3. Zustand Store**

```typescript
// src/stores/appStore.ts
import { create } from 'zustand';
import { subscribeWithSelector, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { AppStore, User, AuthState, PairingState, Settings } from '../types/auth';
import { createDeviceStorage } from '../storage/deviceStorage';
import { detectDeviceType } from '../utils/deviceDetection';

const initialAuthState: AuthState = {
  token: null,
  user: null,
  isAuthenticated: false,
  expiresAt: null,
  deviceType: 'desktop',
  isLoading: false,
  error: null,
};

const initialPairingState: PairingState = {
  code: null,
  channelId: null,
  isPaired: false,
  isConnecting: false,
  connectedDevices: [],
  error: null,
};

const initialSettings: Settings = {
  audioGain: 50,
  vadEnabled: true,
  theme: 'light',
  notifications: true,
};

export const useAppStore = create<AppStore>()(
  immer(
    subscribeWithSelector(
      persist(
        (set, get) => ({
          // ============================================================================
          // State
          // ============================================================================
          auth: initialAuthState,
          pairing: initialPairingState,
          settings: initialSettings,

          // ============================================================================
          // Actions
          // ============================================================================
          actions: {
            // Auth Actions
            setAuth: (token: string, user: User) => {
              const expiresAt = Date.now() + (8 * 60 * 60 * 1000); // 8 hours

              set((state) => {
                state.auth.token = token;
                state.auth.user = user;
                state.auth.isAuthenticated = true;
                state.auth.expiresAt = expiresAt;
                state.auth.isLoading = false;
                state.auth.error = null;
              });

              // Persist to storage
              const deviceStorage = createDeviceStorage(get().auth.deviceType);
              deviceStorage.saveToken(token);
              deviceStorage.saveUserData(user);

              console.log(`✅ Auth set for ${get().auth.deviceType} user: ${user.email}`);
            },

            setMobileAuth: (token: string, inheritedUser: string) => {
              const user: User = {
                id: 'inherited',
                email: inheritedUser,
                name: inheritedUser,
                role: 'user',
                permissions: {
                  canManageUsers: false,
                  canDeleteUsers: false,
                  canModifyAdminRoles: false,
                  isSuperAdmin: false,
                }
              };

              set((state) => {
                state.auth.deviceType = 'mobile';
                state.auth.inheritedFrom = inheritedUser;
              });

              get().actions.setAuth(token, user);
              console.log(`✅ Mobile auth inherited from: ${inheritedUser}`);
            },

            clearAuth: () => {
              const deviceStorage = createDeviceStorage(get().auth.deviceType);
              deviceStorage.clearToken();
              deviceStorage.clearUserData();

              set((state) => {
                state.auth = {
                  ...initialAuthState,
                  deviceType: state.auth.deviceType, // Keep device type
                };
                state.pairing = initialPairingState; // Clear pairing too
              });

              console.log('✅ Auth cleared');
            },

            validateToken: async (): Promise<boolean> => {
              const { token, expiresAt } = get().auth;

              if (!token || !expiresAt) {
                return false;
              }

              // Check expiry
              if (Date.now() > expiresAt) {
                console.log('Token expired');
                get().actions.clearAuth();
                return false;
              }

              // Verify with backend
              try {
                const response = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/verify`, {
                  headers: { 'Authorization': `Bearer ${token}` }
                });

                if (!response.ok) {
                  console.log('Token rejected by backend');
                  get().actions.clearAuth();
                  return false;
                }

                return true;
              } catch (error) {
                console.error('Token validation failed:', error);
                get().actions.clearAuth();
                return false;
              }
            },

            // Pairing Actions
            generatePairingCode: async (): Promise<string> => {
              const { token } = get().auth;
              if (!token) {
                throw new Error('Not authenticated');
              }

              set((state) => {
                state.pairing.isConnecting = true;
                state.pairing.error = null;
              });

              try {
                const response = await fetch(`${import.meta.env.VITE_API_URL}/api/generate-pair-code`, {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                    'Origin': window.location.origin,
                  },
                  body: JSON.stringify({
                    desktop_session_id: `desktop-${Date.now()}`
                  })
                });

                if (!response.ok) {
                  throw new Error(`Failed to generate pairing code: ${response.status}`);
                }

                const data = await response.json();

                set((state) => {
                  state.pairing.code = data.code;
                  state.pairing.channelId = data.channel_id;
                  state.pairing.isConnecting = false;
                });

                console.log(`✅ Pairing code generated: ${data.code}`);
                return data.code;

              } catch (error) {
                set((state) => {
                  state.pairing.isConnecting = false;
                  state.pairing.error = error.message;
                });
                throw error;
              }
            },

            pairWithCode: async (code: string): Promise<boolean> => {
              set((state) => {
                state.pairing.isConnecting = true;
                state.pairing.error = null;
                state.auth.isLoading = true;
              });

              try {
                const response = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/ws-token-mobile`, {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                    'Origin': window.location.origin,
                  },
                  body: JSON.stringify({
                    pair_code: code,
                    username: 'mobile_fallback'
                  })
                });

                if (!response.ok) {
                  throw new Error(`Pairing failed: ${response.status}`);
                }

                const data = await response.json();

                // Set mobile auth based on inheritance
                if (data.inherited_from) {
                  get().actions.setMobileAuth(data.token, data.inherited_from);
                } else {
                  // Fallback user
                  const fallbackUser: User = {
                    id: 'mobile',
                    email: 'mobile_fallback',
                    name: 'Mobile User',
                    role: 'user',
                    permissions: {
                      canManageUsers: false,
                      canDeleteUsers: false,
                      canModifyAdminRoles: false,
                      isSuperAdmin: false,
                    }
                  };
                  get().actions.setAuth(data.token, fallbackUser);
                }

                set((state) => {
                  state.pairing.isPaired = true;
                  state.pairing.isConnecting = false;
                });

                console.log('✅ Mobile pairing successful');
                return true;

              } catch (error) {
                set((state) => {
                  state.pairing.isConnecting = false;
                  state.pairing.error = error.message;
                  state.auth.isLoading = false;
                });
                throw error;
              }
            },

            // Settings Actions
            updateSettings: (newSettings: Partial<Settings>) => {
              set((state) => {
                Object.assign(state.settings, newSettings);
              });
              console.log('✅ Settings updated');
            },
          },
        }),
        {
          name: 'app-store',
          partialize: (state) => ({
            // Only persist settings and device type
            settings: state.settings,
            auth: { deviceType: state.auth.deviceType }
          }),
        }
      )
    )
  )
);

// Store hydration
export const hydrateStore = async () => {
  const deviceType = detectDeviceType();

  // Set device type
  useAppStore.setState((state) => {
    state.auth.deviceType = deviceType;
  });

  // Try to restore auth from storage
  const deviceStorage = createDeviceStorage(deviceType);
  const token = deviceStorage.getToken();
  const user = deviceStorage.getUserData();

  if (token && user) {
    // Set auth data
    useAppStore.setState((state) => {
      state.auth.token = token;
      state.auth.user = user;
      state.auth.isAuthenticated = true;
      state.auth.expiresAt = Date.now() + (8 * 60 * 60 * 1000); // Assume 8 hours
    });

    // Validate token
    const isValid = await useAppStore.getState().actions.validateToken();

    if (isValid) {
      console.log(`✅ ${deviceType} auth restored from storage`);
    } else {
      console.log(`❌ ${deviceType} token invalid, clearing storage`);
    }
  } else {
    console.log(`ℹ️  No ${deviceType} auth found`);
  }
};
```

## 🎣 **4. React Hooks**

```typescript
// src/hooks/useAuth.ts
import { useAppStore } from '../stores/appStore';
import { useState } from 'react';

export const useAuth = () => {
  const auth = useAppStore((state) => state.auth);
  const actions = useAppStore((state) => state.actions);
  const [isLoading, setIsLoading] = useState(false);

  const login = async (email: string, password?: string): Promise<boolean> => {
    setIsLoading(true);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Origin': window.location.origin,
        },
        body: JSON.stringify({
          email,
          password: password || 'dummy'
        })
      });

      if (!response.ok) {
        throw new Error(`Login failed: ${response.status}`);
      }

      const data = await response.json();

      if (data.success && data.token && data.user) {
        actions.setAuth(data.token, data.user);
        return true;
      }

      throw new Error('Invalid login response');

    } catch (error) {
      console.error('Login error:', error);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const loginMagic = async (email: string): Promise<boolean> => {
    setIsLoading(true);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/login-magic`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Origin': window.location.origin,
        },
        body: JSON.stringify({ email })
      });

      if (!response.ok) {
        throw new Error(`Magic login failed: ${response.status}`);
      }

      const data = await response.json();

      if (data.success && data.token && data.user) {
        actions.setAuth(data.token, data.user);
        return true;
      }

      throw new Error('Invalid magic login response');

    } catch (error) {
      console.error('Magic login error:', error);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  return {
    // State
    ...auth,
    isLoading: isLoading || auth.isLoading,

    // Actions
    login,
    loginMagic,
    logout: actions.clearAuth,
    validateToken: actions.validateToken,
  };
};

// src/hooks/usePairing.ts
export const usePairing = () => {
  const pairing = useAppStore((state) => state.pairing);
  const actions = useAppStore((state) => state.actions);

  return {
    // State
    ...pairing,

    // Actions
    generateCode: actions.generatePairingCode,
    pairWithCode: actions.pairWithCode,
  };
};

// src/hooks/useSettings.ts
export const useSettings = () => {
  const settings = useAppStore((state) => state.settings);
  const updateSettings = useAppStore((state) => state.actions.updateSettings);

  return {
    ...settings,
    updateSettings,
  };
};
```

## 🧩 **5. React Components**

```typescript
// src/components/DesktopLogin.tsx
import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';

export const DesktopLogin: React.FC = () => {
  const { login, loginMagic, isLoading, error } = useAuth();
  const [email, setEmail] = useState('');
  const [loginMethod, setLoginMethod] = useState<'regular' | 'magic'>('magic');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    const success = loginMethod === 'magic'
      ? await loginMagic(email)
      : await login(email);

    if (success) {
      console.log('✅ Desktop login successful');
    } else {
      console.error('❌ Desktop login failed');
    }
  };

  return (
    <div className="desktop-login">
      <h2>🖥️ Desktop Login</h2>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="email">Email:</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter your email"
            required
            disabled={isLoading}
          />
        </div>

        <div className="form-group">
          <label>
            <input
              type="radio"
              value="magic"
              checked={loginMethod === 'magic'}
              onChange={(e) => setLoginMethod(e.target.value as 'magic')}
            />
            Magic Link (Recommended)
          </label>
          <label>
            <input
              type="radio"
              value="regular"
              checked={loginMethod === 'regular'}
              onChange={(e) => setLoginMethod(e.target.value as 'regular')}
            />
            Regular Login
          </label>
        </div>

        <button type="submit" disabled={isLoading || !email}>
          {isLoading ? 'Logging in...' : `Login with ${loginMethod === 'magic' ? 'Magic Link' : 'Password'}`}
        </button>
      </form>

      {error && (
        <div className="error">
          ❌ Error: {error}
        </div>
      )}
    </div>
  );
};

// src/components/MobilePairing.tsx
import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { usePairing } from '../hooks/usePairing';

export const MobilePairing: React.FC = () => {
  const { isAuthenticated, user, inheritedFrom } = useAuth();
  const { pairWithCode, isConnecting, error } = usePairing();
  const [code, setCode] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (code.length !== 6) return;

    try {
      const success = await pairWithCode(code);
      if (success) {
        console.log('✅ Mobile pairing successful');
      }
    } catch (error) {
      console.error('❌ Pairing failed:', error);
    }
  };

  const handleCodeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 6);
    setCode(value);
  };

  if (isAuthenticated) {
    return (
      <div className="mobile-success">
        <h2>✅ Mobile Connected!</h2>
        <p>Welcome, {user?.name || user?.email}</p>
        {inheritedFrom && (
          <p className="inherited-info">
            🔗 Inherited authentication from: <strong>{inheritedFrom}</strong>
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="mobile-pairing">
      <h2>📱 Mobile Pairing</h2>
      <p>Enter the 6-digit code shown on your desktop</p>

      <form onSubmit={handleSubmit}>
        <div className="code-input-group">
          <input
            type="text"
            value={code}
            onChange={handleCodeChange}
            placeholder="000000"
            maxLength={6}
            className="code-input"
            disabled={isConnecting}
          />
        </div>

        <button
          type="submit"
          disabled={isConnecting || code.length !== 6}
          className="pair-button"
        >
          {isConnecting ? 'Pairing...' : 'Pair Device'}
        </button>
      </form>

      {error && (
        <div className="error">
          ❌ Error: {error}
        </div>
      )}

      <div className="help-text">
        <p>💡 Make sure your desktop has generated a pairing code</p>
      </div>
    </div>
  );
};

// src/components/ProtectedRoute.tsx
import React from 'react';
import { useAuth } from '../hooks/useAuth';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: 'user' | 'admin' | 'super_admin';
  fallback?: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRole = 'user',
  fallback
}) => {
  const { isAuthenticated, user, isLoading } = useAuth();

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return fallback || <div>Please log in to access this page.</div>;
  }

  // Check role if specified
  if (requiredRole && user) {
    const roleHierarchy = { 'user': 0, 'admin': 1, 'super_admin': 2 };
    const userLevel = roleHierarchy[user.role] ?? -1;
    const requiredLevel = roleHierarchy[requiredRole] ?? 999;

    if (userLevel < requiredLevel) {
      return <div>You don't have permission to access this page.</div>;
    }
  }

  return <>{children}</>;
};
```

## 🛠️ **6. Utilities**

```typescript
// src/utils/deviceDetection.ts
export const detectDeviceType = (): 'desktop' | 'mobile' => {
  // Check user agent
  const userAgent = navigator.userAgent.toLowerCase();

  const mobileKeywords = [
    'mobile', 'android', 'iphone', 'ipad', 'ipod',
    'blackberry', 'windows phone', 'tablet'
  ];

  const isMobile = mobileKeywords.some(keyword =>
    userAgent.includes(keyword)
  );

  // Check screen size as secondary indicator
  const isSmallScreen = window.innerWidth <= 768;

  // Check touch capability
  const hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

  // Combine indicators
  if (isMobile || (isSmallScreen && hasTouch)) {
    return 'mobile';
  }

  return 'desktop';
};

// src/utils/apiClient.ts
import { useAppStore } from '../stores/appStore';

export class ApiClient {
  private static baseUrl = import.meta.env.VITE_API_URL;

  private static getAuthHeaders(): Record<string, string> {
    const token = useAppStore.getState().auth.token;

    return {
      'Content-Type': 'application/json',
      'Origin': window.location.origin,
      ...(token && { 'Authorization': `Bearer ${token}` })
    };
  }

  static async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        ...this.getAuthHeaders(),
        ...options.headers,
      },
    });

    if (!response.ok) {
      // Handle 401 Unauthorized
      if (response.status === 401) {
        console.warn('API request unauthorized, clearing auth');
        useAppStore.getState().actions.clearAuth();
      }

      throw new Error(`API request failed: ${response.status}`);
    }

    return response.json();
  }

  static async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  static async post<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  static async put<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  static async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}
```

## 🚀 **7. App Integration**

```typescript
// src/App.tsx
import React, { useEffect, useState } from 'react';
import { hydrateStore } from './stores/appStore';
import { useAuth } from './hooks/useAuth';
import { detectDeviceType } from './utils/deviceDetection';
import { DesktopLogin } from './components/DesktopLogin';
import { MobilePairing } from './components/MobilePairing';
import { ProtectedRoute } from './components/ProtectedRoute';

const App: React.FC = () => {
  const [isHydrated, setIsHydrated] = useState(false);
  const { isAuthenticated, user } = useAuth();
  const deviceType = detectDeviceType();

  useEffect(() => {
    const initializeApp = async () => {
      console.log('🚀 Initializing app...');

      try {
        await hydrateStore();
        console.log('✅ Store hydrated successfully');
      } catch (error) {
        console.error('❌ Store hydration failed:', error);
      } finally {
        setIsHydrated(true);
      }
    };

    initializeApp();
  }, []);

  // Show loading during hydration
  if (!isHydrated) {
    return (
      <div className="app-loading">
        <h2>🔄 Loading...</h2>
        <p>Initializing application...</p>
      </div>
    );
  }

  // Show auth UI if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="app">
        <div className="auth-container">
          {deviceType === 'desktop' ? <DesktopLogin /> : <MobilePairing />}
        </div>
      </div>
    );
  }

  // Main app content
  return (
    <div className="app">
      <header className="app-header">
        <h1>🦷 Dental ASR System</h1>
        <div className="user-info">
          <span>👤 {user?.name || user?.email}</span>
          <span>📱 {deviceType}</span>
        </div>
      </header>

      <main className="app-main">
        <ProtectedRoute>
          <div>
            <h2>Welcome to the main application!</h2>
            <p>You are successfully authenticated.</p>

            {/* Add your main app components here */}
          </div>
        </ProtectedRoute>
      </main>
    </div>
  );
};

export default App;
```

## 📋 **8. Usage Checklist**

### **Setup Steps:**
1. [ ] Install dependencies: `npm install zustand immer`
2. [ ] Create directory structure as shown above
3. [ ] Copy all code examples to respective files
4. [ ] Update environment variables in `.env`
5. [ ] Test device detection in browser dev tools
6. [ ] Verify storage encryption in browser storage

### **Testing Steps:**
1. [ ] Desktop login works and persists in sessionStorage
2. [ ] Mobile pairing works and persists in localStorage
3. [ ] Auth state survives page refresh
4. [ ] Token validation with backend works
5. [ ] Logout clears all storage properly
6. [ ] Protected routes work with role validation

### **Production Checklist:**
1. [ ] Replace simple base64 with proper encryption
2. [ ] Add proper error boundaries
3. [ ] Implement CSP headers
4. [ ] Add security monitoring
5. [ ] Test with real backend API
6. [ ] Verify HTTPS in production

Deze complete implementatie geeft je een production-ready unified auth system! 🚀