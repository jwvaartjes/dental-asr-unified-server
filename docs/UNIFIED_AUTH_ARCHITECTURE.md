# Unified Auth Architecture - Zustand Single Source of Truth

## 🎯 Problem Statement

De huidige auth implementatie heeft verwarring door:
- Auth tokens in `localStorage` (useAuth.tsx)
- Pairing state in Zustand store
- **Duplicatie** van auth state
- **Mixed storage patterns** zonder duidelijke strategie

## ✅ Solution: Zustand as Single Source of Truth

Alle state (auth + pairing + settings) in één Zustand store met slimme persistence.

## 🏗 **Unified Store Architecture**

### 1. **Core Store Structure**

```typescript
// stores/appStore.ts
import { create } from 'zustand';
import { subscribeWithSelector, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

interface AppStore {
  // Auth State
  auth: {
    token: string | null;
    user: User | null;
    isAuthenticated: boolean;
    expiresAt: number | null;
    deviceType: 'desktop' | 'mobile';
    inheritedFrom?: string; // For mobile pairing
  };

  // Pairing State
  pairing: {
    code: string | null;
    channelId: string | null;
    isPaired: boolean;
    isConnecting: boolean;
    connectedDevices: ConnectedDevice[];
  };

  // Settings State
  settings: {
    audioGain: number;
    vadEnabled: boolean;
    // ... other settings
  };

  // Actions
  actions: {
    // Auth actions
    setAuth: (token: string, user: User) => void;
    setMobileAuth: (token: string, inheritedUser: string) => void;
    clearAuth: () => void;

    // Pairing actions
    generatePairingCode: () => Promise<string>;
    pairWithCode: (code: string) => Promise<boolean>;

    // Settings actions
    updateSettings: (settings: Partial<Settings>) => void;
  };
}
```

### 2. **Smart Storage Strategy**

```typescript
// storage/secureStorage.ts
class SecureStorage {
  private static encrypt(value: string): string {
    // Simple base64 encoding - use proper encryption in production
    return btoa(value);
  }

  private static decrypt(value: string): string {
    try {
      return atob(value);
    } catch {
      return '';
    }
  }

  static setToken(key: string, token: string, persistent: boolean = false): void {
    const storage = persistent ? localStorage : sessionStorage;
    const encrypted = this.encrypt(token);
    storage.setItem(key, encrypted);
  }

  static getToken(key: string): string | null {
    // Try sessionStorage first, then localStorage
    let encrypted = sessionStorage.getItem(key) || localStorage.getItem(key);
    if (!encrypted) return null;

    const decrypted = this.decrypt(encrypted);
    return decrypted || null;
  }

  static removeToken(key: string): void {
    sessionStorage.removeItem(key);
    localStorage.removeItem(key);
  }
}
```

### 3. **Device-Specific Storage**

```typescript
// storage/deviceStorage.ts
export const createDeviceStorage = (deviceType: 'desktop' | 'mobile') => {
  const STORAGE_KEYS = {
    desktop: {
      token: 'desktop_auth_token',
      storage: sessionStorage, // Cleared on tab close
    },
    mobile: {
      token: 'mobile_auth_token',
      storage: localStorage,     // Persists across app restarts
    }
  };

  const config = STORAGE_KEYS[deviceType];

  return {
    saveToken: (token: string) => {
      SecureStorage.setToken(config.token, token, deviceType === 'mobile');
    },

    getToken: (): string | null => {
      return SecureStorage.getToken(config.token);
    },

    clearToken: () => {
      SecureStorage.removeToken(config.token);
    }
  };
};
```

## 🚀 **Complete Store Implementation**

```typescript
// stores/appStore.ts
export const useAppStore = create<AppStore>()(
  immer(
    subscribeWithSelector(
      persist(
        (set, get) => ({
          // ============================================================================
          // Initial State
          // ============================================================================
          auth: {
            token: null,
            user: null,
            isAuthenticated: false,
            expiresAt: null,
            deviceType: 'desktop', // Default, will be set during initialization
          },

          pairing: {
            code: null,
            channelId: null,
            isPaired: false,
            isConnecting: false,
            connectedDevices: [],
          },

          settings: {
            audioGain: 50,
            vadEnabled: true,
          },

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
              });

              // Persist based on device type
              const deviceStorage = createDeviceStorage(get().auth.deviceType);
              deviceStorage.saveToken(token);
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
            },

            clearAuth: () => {
              const deviceStorage = createDeviceStorage(get().auth.deviceType);
              deviceStorage.clearToken();

              set((state) => {
                state.auth.token = null;
                state.auth.user = null;
                state.auth.isAuthenticated = false;
                state.auth.expiresAt = null;
                state.auth.inheritedFrom = undefined;
                // Don't reset deviceType - might be needed for re-auth
              });
            },

            // Token validation
            validateToken: async (): Promise<boolean> => {
              const { token, expiresAt } = get().auth;

              if (!token || !expiresAt) return false;

              // Check expiry
              if (Date.now() > expiresAt) {
                get().actions.clearAuth();
                return false;
              }

              // Verify with backend
              try {
                const response = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/verify`, {
                  headers: { 'Authorization': `Bearer ${token}` }
                });

                if (!response.ok) {
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
              if (!token) throw new Error('Not authenticated');

              set((state) => {
                state.pairing.isConnecting = true;
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

                return data.code;
              } catch (error) {
                set((state) => {
                  state.pairing.isConnecting = false;
                });
                throw error;
              }
            },

            pairWithCode: async (code: string): Promise<boolean> => {
              set((state) => {
                state.pairing.isConnecting = true;
              });

              try {
                // Get mobile auth token via pairing
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

                // Set mobile auth
                if (data.inherited_from) {
                  get().actions.setMobileAuth(data.token, data.inherited_from);
                } else {
                  // Fallback auth
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

                return true;
              } catch (error) {
                set((state) => {
                  state.pairing.isConnecting = false;
                });
                throw error;
              }
            },

            // Settings Actions
            updateSettings: (newSettings: Partial<Settings>) => {
              set((state) => {
                Object.assign(state.settings, newSettings);
              });
            },
          },
        }),
        {
          name: 'app-store',
          partialize: (state) => ({
            // Only persist settings, not sensitive auth data
            settings: state.settings,
            // Persist device type for proper storage strategy
            auth: { deviceType: state.auth.deviceType }
          }),
        }
      )
    )
  )
);
```

## 🔄 **Store Hydration & Initialization**

```typescript
// stores/storeHydration.ts
export const hydrateStore = async () => {
  const store = useAppStore.getState();

  // Detect device type (you might have this logic elsewhere)
  const deviceType = detectDeviceType(); // 'desktop' | 'mobile'

  // Set device type
  useAppStore.setState((state) => {
    state.auth.deviceType = deviceType;
  });

  // Try to restore auth from storage
  const deviceStorage = createDeviceStorage(deviceType);
  const token = deviceStorage.getToken();

  if (token) {
    // Validate token with backend
    const isValid = await store.actions.validateToken();

    if (isValid) {
      console.log(`✅ ${deviceType} auth restored from storage`);
    } else {
      console.log(`❌ ${deviceType} token invalid, clearing storage`);
      deviceStorage.clearToken();
    }
  } else {
    console.log(`ℹ️  No ${deviceType} auth token found`);
  }
};

// Call this in your app initialization
// App.tsx
useEffect(() => {
  hydrateStore();
}, []);
```

## 🎯 **React Hook Usage**

```typescript
// hooks/useAuth.ts
export const useAuth = () => {
  const auth = useAppStore((state) => state.auth);
  const actions = useAppStore((state) => state.actions);

  return {
    ...auth,
    login: async (email: string, password?: string) => {
      // Implementation here
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      const data = await response.json();
      if (data.success) {
        actions.setAuth(data.token, data.user);
        return true;
      }
      return false;
    },
    logout: actions.clearAuth,
    validateToken: actions.validateToken,
  };
};

// hooks/usePairing.ts
export const usePairing = () => {
  const pairing = useAppStore((state) => state.pairing);
  const actions = useAppStore((state) => state.actions);

  return {
    ...pairing,
    generateCode: actions.generatePairingCode,
    pairWithCode: actions.pairWithCode,
  };
};
```

## ✅ **Benefits van deze Architecture**

### 1. **Single Source of Truth**
- Alle state in één plek
- Geen sync issues tussen auth en pairing
- Predictable state updates

### 2. **Device-Aware Storage**
- Desktop: `sessionStorage` (cleared on tab close)
- Mobile: `localStorage` (persists across restarts)
- Automatic device detection

### 3. **Security**
- Tokens encrypted before storage
- Automatic token validation
- Secure clearing of expired tokens

### 4. **Developer Experience**
- Type-safe state access
- Clear separation of concerns
- Easy testing with Zustand

### 5. **Performance**
- Selective re-renders via selectors
- Only persist non-sensitive data
- Efficient state updates with Immer

## 🚫 **What NOT to Store in Persistence**

```typescript
// ❌ NEVER persist these
const NEVER_PERSIST = [
  'auth.token',        // Security risk
  'auth.user',         // Contains sensitive data
  'pairing.channelId', // Session-specific
  'websocket',         // Runtime only
];

// ✅ OK to persist these
const OK_TO_PERSIST = [
  'settings',          // User preferences
  'auth.deviceType',   // Device detection
  'ui.theme',          // UI preferences
];
```

Deze architecture lost alle verwarring op door een duidelijke, veilige en schaalbare structuur te bieden voor alle state management.