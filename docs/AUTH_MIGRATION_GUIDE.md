# Migration Guide: From Mixed Auth to Unified Zustand Architecture

## 🎯 **Migration Overview**

Deze guide helpt je migreren van de huidige mixed architecture naar een unified Zustand-based approach.

### **Current State → Target State**

```
BEFORE (Mixed):
├── useAuth.tsx         → localStorage direct
├── pairingStore.ts     → Zustand + localStorage
├── AuthContextSimple  → Cookie attempts
└── Duplicate auth state

AFTER (Unified):
└── appStore.ts         → Single Zustand store
    ├── Smart device storage
    ├── No duplicate state
    └── Clear separation
```

## 🚧 **Step-by-Step Migration**

### **Step 1: Create New Unified Store**

First, create the new store structure (following the Unified Architecture doc):

```bash
# Create new structure
mkdir src/stores
mkdir src/storage
mkdir src/hooks/unified

# Files to create
src/stores/appStore.ts          # Main unified store
src/storage/secureStorage.ts    # Secure storage utilities
src/storage/deviceStorage.ts    # Device-specific storage
src/hooks/unified/useAuth.ts    # New auth hook
src/hooks/unified/usePairing.ts # New pairing hook
```

### **Step 2: Implement Storage Layer**

```typescript
// src/storage/secureStorage.ts
export class SecureStorage {
  private static encrypt(value: string): string {
    return btoa(value); // Use proper encryption in production
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
    let encrypted = sessionStorage.getItem(key) || localStorage.getItem(key);
    if (!encrypted) return null;
    return this.decrypt(encrypted) || null;
  }

  static removeToken(key: string): void {
    sessionStorage.removeItem(key);
    localStorage.removeItem(key);
  }
}

// src/storage/deviceStorage.ts
export const createDeviceStorage = (deviceType: 'desktop' | 'mobile') => {
  const config = {
    desktop: { token: 'desktop_auth_token', persistent: false },
    mobile: { token: 'mobile_auth_token', persistent: true }
  }[deviceType];

  return {
    saveToken: (token: string) => {
      SecureStorage.setToken(config.token, token, config.persistent);
    },
    getToken: () => SecureStorage.getToken(config.token),
    clearToken: () => SecureStorage.removeToken(config.token),
  };
};
```

### **Step 3: Data Migration from Old Storage**

```typescript
// src/migration/migrateAuth.ts
export const migrateAuthData = async (): Promise<{
  token: string | null;
  user: any | null;
  deviceType: 'desktop' | 'mobile';
}> => {
  console.log('🔄 Migrating auth data...');

  // Check for existing tokens in various locations
  const sources = [
    // From old useAuth implementation
    { key: 'auth_token', storage: localStorage, source: 'useAuth' },

    // From mobile pairing
    { key: 'mobile_auth_token', storage: localStorage, source: 'mobile' },

    // From any sessionStorage
    { key: 'auth_token', storage: sessionStorage, source: 'session' },
  ];

  let token: string | null = null;
  let user: any | null = null;
  let deviceType: 'desktop' | 'mobile' = 'desktop';

  for (const source of sources) {
    const foundToken = source.storage.getItem(source.key);
    if (foundToken) {
      console.log(`✅ Found token in ${source.source}`);
      token = foundToken;

      // Determine device type from source
      if (source.source === 'mobile') {
        deviceType = 'mobile';
      }

      break;
    }
  }

  // Try to get user data
  const userData = localStorage.getItem('user_data');
  if (userData) {
    try {
      user = JSON.parse(userData);
      console.log('✅ Found user data');
    } catch (e) {
      console.warn('⚠️  Could not parse user data');
    }
  }

  // Check for mobile inherited user
  const inheritedFrom = localStorage.getItem('mobile_inherited_from');
  if (inheritedFrom && deviceType === 'mobile') {
    user = {
      id: 'inherited',
      email: inheritedFrom,
      name: inheritedFrom,
      role: 'user',
      permissions: {
        canManageUsers: false,
        canDeleteUsers: false,
        canModifyAdminRoles: false,
        isSuperAdmin: false,
      }
    };
    console.log(`✅ Found inherited user: ${inheritedFrom}`);
  }

  return { token, user, deviceType };
};

// src/migration/cleanupOldStorage.ts
export const cleanupOldStorage = () => {
  console.log('🧹 Cleaning up old storage...');

  const keysToRemove = [
    // Old auth keys
    'auth_token',
    'user_data',

    // Old mobile keys
    'mobile_auth_token',
    'mobile_inherited_from',

    // Any other old keys you want to clean
  ];

  keysToRemove.forEach(key => {
    localStorage.removeItem(key);
    sessionStorage.removeItem(key);
  });

  console.log('✅ Old storage cleaned');
};
```

### **Step 4: Update App Initialization**

```typescript
// src/App.tsx
import { useEffect, useState } from 'react';
import { useAppStore } from './stores/appStore';
import { migrateAuthData, cleanupOldStorage } from './migration/migrateAuth';

function App() {
  const [migrationComplete, setMigrationComplete] = useState(false);
  const actions = useAppStore(state => state.actions);

  useEffect(() => {
    const performMigration = async () => {
      try {
        console.log('🚀 Starting auth migration...');

        // Step 1: Migrate existing data
        const { token, user, deviceType } = await migrateAuthData();

        // Step 2: Set device type in store
        useAppStore.setState(state => {
          state.auth.deviceType = deviceType;
        });

        // Step 3: If we have valid auth data, restore it
        if (token && user) {
          // Validate token first
          const isValid = await actions.validateToken();
          if (isValid) {
            actions.setAuth(token, user);
            console.log(`✅ ${deviceType} auth restored successfully`);
          } else {
            console.log('❌ Token validation failed, starting fresh');
          }
        }

        // Step 4: Clean up old storage
        cleanupOldStorage();

        console.log('✅ Migration completed');
        setMigrationComplete(true);

      } catch (error) {
        console.error('❌ Migration failed:', error);
        setMigrationComplete(true); // Continue anyway
      }
    };

    performMigration();
  }, []);

  // Show loading during migration
  if (!migrationComplete) {
    return (
      <div className="migration-loading">
        <h2>🔄 Updating authentication...</h2>
        <p>Please wait while we migrate your session.</p>
      </div>
    );
  }

  return (
    <div className="App">
      {/* Your app content */}
    </div>
  );
}
```

### **Step 5: Replace Old Auth Components**

#### **Before (useAuth.tsx):**
```typescript
// ❌ OLD - Remove this
const { login, logout, isAuthenticated, user } = useAuth();
```

#### **After (New unified hooks):**
```typescript
// ✅ NEW - Use this
import { useAuth } from './hooks/unified/useAuth';
import { usePairing } from './hooks/unified/usePairing';

const { login, logout, isAuthenticated, user } = useAuth();
const { generateCode, pairWithCode, isPaired } = usePairing();
```

### **Step 6: Update Components**

#### **Desktop Login Component:**
```typescript
// src/components/DesktopLogin.tsx
import { useAuth } from '../hooks/unified/useAuth';

export const DesktopLogin = () => {
  const { login, isLoading, error } = useAuth();
  const [email, setEmail] = useState('');

  const handleLogin = async () => {
    const success = await login(email);
    if (success) {
      console.log('✅ Desktop login successful');
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
        {isLoading ? 'Logging in...' : 'Login'}
      </button>
      {error && <p className="error">{error}</p>}
    </div>
  );
};
```

#### **Mobile Pairing Component:**
```typescript
// src/components/MobilePairing.tsx
import { useAuth } from '../hooks/unified/useAuth';
import { usePairing } from '../hooks/unified/usePairing';

export const MobilePairing = () => {
  const { isAuthenticated } = useAuth();
  const { pairWithCode, isConnecting } = usePairing();
  const [code, setCode] = useState('');

  const handlePairing = async () => {
    try {
      const success = await pairWithCode(code);
      if (success) {
        console.log('✅ Mobile pairing successful');
      }
    } catch (error) {
      console.error('❌ Pairing failed:', error);
    }
  };

  if (isAuthenticated) {
    return <div>✅ Authenticated successfully!</div>;
  }

  return (
    <div>
      <input
        type="text"
        value={code}
        onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
        placeholder="000000"
        maxLength={6}
      />
      <button onClick={handlePairing} disabled={isConnecting}>
        {isConnecting ? 'Pairing...' : 'Pair Device'}
      </button>
    </div>
  );
};
```

### **Step 7: Remove Old Files**

After testing the new implementation:

```bash
# Remove old auth files
rm src/hooks/useAuth.tsx                    # Old auth hook
rm src/contexts/AuthContextSimple.tsx      # Old auth context
rm src/docs/useAuth.tsx                     # Documentation files
rm src/docs/pairingStore.ts                # Old pairing store

# Keep these for reference initially, remove later:
# - Any other auth-related files from the old system
```

## 🧪 **Testing the Migration**

### **Test Scenarios:**

1. **Desktop User with Existing Session:**
   ```typescript
   // Before migration: localStorage has 'auth_token' and 'user_data'
   // After migration: Should be authenticated in new store
   // Storage: Token should be in sessionStorage (desktop pattern)
   ```

2. **Mobile User with Pairing Session:**
   ```typescript
   // Before migration: localStorage has 'mobile_auth_token' and 'mobile_inherited_from'
   // After migration: Should be authenticated as inherited user
   // Storage: Token should be in localStorage (mobile pattern)
   ```

3. **Fresh User (No Existing Session):**
   ```typescript
   // Before migration: No tokens
   // After migration: Should show login/pairing form
   // Storage: Clean slate
   ```

### **Testing Checklist:**

- [ ] Desktop login works
- [ ] Mobile pairing works
- [ ] Token persistence correct per device type
- [ ] Old storage is cleaned up
- [ ] Auth state survives page refresh
- [ ] Logout clears all storage
- [ ] Token validation works

## ⚠️ **Migration Warnings**

### **What to Watch For:**

1. **Data Loss Prevention:**
   ```typescript
   // Always backup before migration
   const backupOldData = () => {
     const backup = {
       auth_token: localStorage.getItem('auth_token'),
       user_data: localStorage.getItem('user_data'),
       mobile_auth_token: localStorage.getItem('mobile_auth_token'),
       // ... other important keys
     };
     console.log('Backup:', backup);
     return backup;
   };
   ```

2. **Gradual Migration:**
   ```typescript
   // Option: Run old and new systems in parallel temporarily
   const MIGRATION_FLAG = 'use_new_auth_system';

   const useNewAuth = localStorage.getItem(MIGRATION_FLAG) === 'true';

   if (useNewAuth) {
     // Use new unified store
   } else {
     // Use old auth system
   }
   ```

3. **Rollback Plan:**
   ```typescript
   // Keep rollback capability
   const rollbackMigration = () => {
     // Restore from backup
     // Switch back to old system
   };
   ```

## ✅ **Post-Migration Verification**

After migration is complete:

1. **Storage Inspection:**
   ```javascript
   // Check browser dev tools
   console.log('SessionStorage:', sessionStorage);
   console.log('LocalStorage:', localStorage);
   // Should see clean, organized storage
   ```

2. **Store State:**
   ```javascript
   // Check Zustand store
   console.log('App Store:', useAppStore.getState());
   // Should show unified state structure
   ```

3. **Functionality Test:**
   - Login/logout flows
   - Token refresh
   - Pairing functionality
   - Cross-tab behavior (desktop)
   - App restart behavior (mobile)

Volg deze guide stap-voor-stap om veilig te migreren naar de unified architecture!