# Mobile Auth Context Fix - JWT vs Cookie Issue

## 🚨 Problem

Na het pairen ziet de mobile app dit:
```
🔐 Initializing cookie-based auth...
❌ No valid session found
```

Dit gebeurt omdat de mobile app probeert cookie-based authenticatie te initialiseren **nadat** het al een JWT token heeft gekregen via pairing.

## 🎯 Root Cause

1. **Mobile paring succeeds** → JWT token received
2. **AuthContextSimple** initializes → Looks for cookies
3. **No cookies found** → Shows "No valid session found"
4. **JWT token ignored** → Auth context not updated

## ✅ Solution: Update Auth Context After Pairing

### 1. **Modify AuthContextSimple.tsx**

```typescript
// AuthContextSimple.tsx
import { useEffect, useState } from 'react';

export const AuthContextSimple = ({ children }) => {
  const [authState, setAuthState] = useState({
    isAuthenticated: false,
    user: null,
    token: null,
    loading: true
  });

  useEffect(() => {
    initializeAuth();
  }, []);

  const initializeAuth = async () => {
    console.log('📱 Initializing mobile authentication...');

    // Check for mobile pairing token in localStorage
    const mobileToken = localStorage.getItem('mobile_auth_token');
    const inheritedFrom = localStorage.getItem('mobile_inherited_from');

    if (mobileToken) {
      console.log('✅ Found mobile pairing token');

      // Verify the token with backend
      try {
        const response = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/verify`, {
          headers: {
            'Authorization': `Bearer ${mobileToken}`
          }
        });

        if (response.ok) {
          const userData = await response.json();

          setAuthState({
            isAuthenticated: true,
            user: userData.user || inheritedFrom,
            token: mobileToken,
            loading: false
          });

          console.log(`✅ Mobile auth restored: ${userData.user || inheritedFrom}`);
          return;
        }
      } catch (error) {
        console.error('Mobile token verification failed:', error);
        // Clear invalid token
        localStorage.removeItem('mobile_auth_token');
        localStorage.removeItem('mobile_inherited_from');
      }
    }

    // No valid mobile token found
    setAuthState({
      isAuthenticated: false,
      user: null,
      token: null,
      loading: false
    });
    console.log('ℹ️  No mobile session found - showing pairing form');
  };

  // Method to update auth after mobile pairing
  const updateMobileAuth = (token: string, inheritedFrom?: string) => {
    localStorage.setItem('mobile_auth_token', token);
    if (inheritedFrom) {
      localStorage.setItem('mobile_inherited_from', inheritedFrom);
    }

    setAuthState({
      isAuthenticated: true,
      user: inheritedFrom || 'mobile_user',
      token: token,
      loading: false
    });

    console.log(`✅ Mobile auth updated: ${inheritedFrom || 'mobile_user'}`);
  };

  const logout = () => {
    // Clear mobile auth
    localStorage.removeItem('mobile_auth_token');
    localStorage.removeItem('mobile_inherited_from');

    setAuthState({
      isAuthenticated: false,
      user: null,
      token: null,
      loading: false
    });

    console.log('📱 Mobile auth cleared');
  };

  return (
    <AuthContext.Provider value={{
      ...authState,
      updateMobileAuth,
      logout,
      refreshAuth: initializeAuth
    }}>
      {children}
    </AuthContext.Provider>
  );
};
```

### 2. **Update Mobile Pairing Component**

```typescript
// MobilePairingForm.tsx
import { useContext } from 'react';
import { AuthContext } from '../contexts/AuthContextSimple';

export const MobilePairingForm = ({ onSuccess }) => {
  const { updateMobileAuth } = useContext(AuthContext);
  const [pairCode, setPairCode] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const apiUrl = import.meta.env.VITE_API_URL;

      const response = await fetch(`${apiUrl}/api/auth/ws-token-mobile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Origin': window.location.origin
        },
        body: JSON.stringify({
          pair_code: pairCode,
          username: "mobile_fallback"
        })
      });

      if (!response.ok) {
        throw new Error(`Pairing failed: ${response.status}`);
      }

      const data = await response.json();

      // 🎯 KEY FIX: Update auth context immediately after pairing
      updateMobileAuth(data.token, data.inherited_from);

      if (data.inherited_from) {
        console.log(`✅ Successfully paired! Authenticated as: ${data.inherited_from}`);
      } else {
        console.log('⚠️ Paired with fallback authentication');
      }

      onSuccess?.(data);
    } catch (error) {
      console.error('Pairing failed:', error);
      alert(`❌ Pairing failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // ... rest of component
};
```

### 3. **Update Auth Context Types**

```typescript
// types/auth.ts
export interface AuthContextType {
  isAuthenticated: boolean;
  user: string | null;
  token: string | null;
  loading: boolean;
  updateMobileAuth: (token: string, inheritedFrom?: string) => void;
  logout: () => void;
  refreshAuth: () => Promise<void>;
}
```

## 🎯 Key Changes

### 1. **Mobile-Only Authentication**
- **Only JWT token-based auth** (from pairing)
- **No cookie fallback** (cookies don't work in mobile apps)

### 2. **Mobile Pairing Integration**
- Immediately update auth context after successful pairing
- Store token + inherited user info
- Skip cookie initialization if mobile token exists

### 3. **Clean Mobile Logout**
- Clear only mobile tokens (no cookie confusion)
- Simple session cleanup

## 🔄 Flow After Fix

```
1. Mobile app starts → Mobile AuthContext initializes
2. Check localStorage for mobile_auth_token ✅
3. If found → Verify with backend → Set authenticated ✅
4. If not found → Show pairing form (no cookie attempts) ✅
5. User enters pairing code → Gets JWT token ✅
6. updateMobileAuth() called → Auth context updated immediately ✅
7. No more "No valid session found" error ✅
```

## 🧪 Testing

After implementing this fix:

1. **Clear localStorage** completely
2. **Start mobile app** → Should show pairing form
3. **Enter valid pairing code** → Should immediately authenticate
4. **Refresh page** → Should stay authenticated (token restored)
5. **No cookie errors** should appear

This fix ensures mobile devices use **only JWT token-based auth** with no unnecessary cookie fallbacks that can't work anyway.