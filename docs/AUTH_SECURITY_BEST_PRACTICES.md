# Authentication Security Best Practices

## 🔒 **Security Overview**

Deze guide documenteert de security best practices voor authentication token storage en management in je frontend applicatie, met focus op de trade-offs tussen httpOnly cookies en JWT tokens.

## 🏆 **Cookie vs JWT Security Comparison**

### **HttpOnly Cookies (Desktop Recommended)**
```typescript
// Backend sets cookie
response.set_cookie(
    key="session_token",
    value=token,
    httponly=True,        // ✅ XSS Protection
    secure=True,          // ✅ HTTPS Only
    samesite="strict"     // ✅ CSRF Protection
)

// Frontend - NO token management needed
fetch('/api/protected', {
    credentials: 'include'  // ✅ Automatic inclusion
});
```

**Security Benefits:**
- ✅ **Complete XSS Protection**: JavaScript cannot access token
- ✅ **CSRF Protection**: SameSite attribute prevents cross-site requests
- ✅ **Automatic HTTPS**: Secure flag ensures encrypted transmission
- ✅ **Browser-Managed**: No manual storage/retrieval needed
- ✅ **Automatic Expiry**: Browser handles cleanup

**Limitations:**
- ❌ **React Native**: Not supported in mobile apps
- ❌ **Cross-Domain**: Limited for multi-domain scenarios
- ❌ **API-First**: Harder for pure API architectures

### **JWT Tokens (Mobile Necessary)**
```typescript
// Manual token management
const token = await SecureStorage.getToken('auth_token');
fetch('/api/protected', {
    headers: { 'Authorization': `Bearer ${token}` }
});
```

**Security Benefits:**
- ✅ **Universal Support**: Works everywhere (web, mobile, API)
- ✅ **Stateless**: No server-side storage needed
- ✅ **Cross-Domain**: Easy to use across different domains
- ✅ **API-Friendly**: Standard Authorization header

**Security Challenges:**
- ⚠️ **XSS Vulnerable**: Accessible to malicious scripts
- ⚠️ **Storage Risk**: Exposed in localStorage/sessionStorage
- ⚠️ **Manual Management**: Requires proper implementation
- ⚠️ **Token Leakage**: Can be logged or exposed accidentally

### **Security Comparison Matrix**

| Aspect | HttpOnly Cookies | JWT Tokens | Hybrid Approach |
|--------|------------------|------------|-----------------|
| **XSS Protection** | ✅ Complete | ❌ Vulnerable | ✅ Platform-optimized |
| **CSRF Protection** | ✅ Built-in | ⚠️ Manual | ✅ Comprehensive |
| **Mobile Support** | ❌ Impossible | ✅ Works | ✅ Works |
| **Implementation** | ✅ Automatic | ⚠️ Manual | ✅ Abstracted |
| **Storage Security** | ✅ Browser-managed | ⚠️ App-managed | ✅ Best per platform |
| **Network Security** | ✅ Automatic HTTPS | ⚠️ Manual HTTPS | ✅ Enforced |

### **Recommendation: Device-Aware Strategy**

```typescript
// Optimal approach per platform
const AUTH_STRATEGY = {
    desktop: 'httpOnly_cookies',    // Maximum security
    mobile: 'encrypted_jwt',        // Necessary compromise
    api: 'jwt_tokens'              // Standard for APIs
};
```

## 🎯 **Security Threats & Mitigations**

### **Threat 1: XSS (Cross-Site Scripting)**
**Risk:** Malicious scripts kunnen tokens uit localStorage/sessionStorage stelen.

**Mitigations:**
```typescript
// 1. Token Encryption
class SecureStorage {
  private static readonly ENCRYPTION_KEY = 'your-app-specific-key';

  private static encrypt(value: string): string {
    // Use crypto-js or Web Crypto API in production
    return btoa(value); // Simple encoding for demo
  }

  private static decrypt(value: string): string {
    try {
      return atob(value);
    } catch {
      return '';
    }
  }

  // Never store plain text tokens
  static setToken(key: string, token: string): void {
    const encrypted = this.encrypt(token);
    sessionStorage.setItem(key, encrypted);
  }
}

// 2. Content Security Policy
// In your HTML or via headers
const CSP_HEADER = `
  default-src 'self';
  script-src 'self' 'unsafe-inline';
  connect-src 'self' ${process.env.VITE_API_URL};
  style-src 'self' 'unsafe-inline';
`;
```

### **Threat 2: CSRF (Cross-Site Request Forgery)**
**Risk:** Unauthorized requests van andere websites.

**Mitigations:**
```typescript
// 1. Origin Validation
const makeAuthenticatedRequest = async (url: string, data?: any) => {
  return fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${getToken()}`,
      'Origin': window.location.origin,  // Always send origin
    },
    body: JSON.stringify(data)
  });
};

// 2. Custom Headers (Backend should validate)
const CUSTOM_HEADERS = {
  'X-Requested-With': 'XMLHttpRequest',
  'X-App-Version': '1.0.0',
};
```

### **Threat 3: Token Theft via Storage**
**Risk:** Malicious extensions/scripts accessing storage.

**Mitigations:**
```typescript
// 1. Minimal Storage Duration
const TOKEN_STORAGE_STRATEGY = {
  desktop: {
    storage: sessionStorage,     // Cleared on tab close
    duration: '8 hours',
    autoRefresh: true,
  },
  mobile: {
    storage: localStorage,       // Persists across app restarts
    duration: '8 hours',
    encryption: 'enhanced',      // Extra encryption for mobile
  }
};

// 2. Token Rotation
class TokenManager {
  static async refreshToken(): Promise<string | null> {
    const currentToken = this.getToken();
    if (!currentToken) return null;

    try {
      const response = await fetch('/api/auth/refresh', {
        headers: { 'Authorization': `Bearer ${currentToken}` }
      });

      if (response.ok) {
        const { token: newToken } = await response.json();

        // Replace old token immediately
        this.clearToken();
        this.setToken(newToken);

        return newToken;
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
      this.clearToken();
    }

    return null;
  }
}
```

## 🛡️ **Storage Security Layers**

### **Layer 1: Encryption**
```typescript
// Enhanced encryption using Web Crypto API
class CryptoStorage {
  private static async generateKey(): Promise<CryptoKey> {
    return await crypto.subtle.generateKey(
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt', 'decrypt']
    );
  }

  private static async encrypt(data: string, key: CryptoKey): Promise<string> {
    const encoder = new TextEncoder();
    const dataBuffer = encoder.encode(data);
    const iv = crypto.getRandomValues(new Uint8Array(12));

    const encryptedBuffer = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv },
      key,
      dataBuffer
    );

    // Combine IV + encrypted data
    const combined = new Uint8Array(iv.length + encryptedBuffer.byteLength);
    combined.set(iv);
    combined.set(new Uint8Array(encryptedBuffer), iv.length);

    return btoa(String.fromCharCode(...combined));
  }

  private static async decrypt(encryptedData: string, key: CryptoKey): Promise<string> {
    const combined = new Uint8Array(
      atob(encryptedData).split('').map(char => char.charCodeAt(0))
    );

    const iv = combined.slice(0, 12);
    const data = combined.slice(12);

    const decryptedBuffer = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv },
      key,
      data
    );

    return new TextDecoder().decode(decryptedBuffer);
  }

  // Public methods
  static async setSecureToken(key: string, token: string): Promise<void> {
    const cryptoKey = await this.generateKey();
    const encrypted = await this.encrypt(token, cryptoKey);

    // Store encrypted token
    sessionStorage.setItem(key, encrypted);

    // Store key reference (not the actual key)
    sessionStorage.setItem(`${key}_ref`, 'crypto-key-generated');
  }
}
```

### **Layer 2: Token Validation**
```typescript
// Token validation with signature verification
class TokenValidator {
  private static readonly TOKEN_PATTERN = /^[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]*$/;

  static isValidFormat(token: string): boolean {
    return this.TOKEN_PATTERN.test(token);
  }

  static isExpired(token: string): boolean {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const exp = payload.exp * 1000; // Convert to milliseconds
      return Date.now() > exp;
    } catch {
      return true; // Invalid token = expired
    }
  }

  static async validateWithBackend(token: string): Promise<boolean> {
    try {
      const response = await fetch('/api/auth/verify', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      return response.ok;
    } catch {
      return false;
    }
  }

  static async fullValidation(token: string): Promise<boolean> {
    // 1. Format check
    if (!this.isValidFormat(token)) {
      console.warn('Invalid token format');
      return false;
    }

    // 2. Expiry check
    if (this.isExpired(token)) {
      console.warn('Token expired');
      return false;
    }

    // 3. Backend verification
    const isValid = await this.validateWithBackend(token);
    if (!isValid) {
      console.warn('Token rejected by backend');
      return false;
    }

    return true;
  }
}
```

### **Layer 3: Access Control**
```typescript
// Role-based access control
class AuthGuard {
  private static readonly ROLE_HIERARCHY = {
    'user': 0,
    'admin': 1,
    'super_admin': 2
  };

  static hasPermission(userRole: string, requiredRole: string): boolean {
    const userLevel = this.ROLE_HIERARCHY[userRole] ?? -1;
    const requiredLevel = this.ROLE_HIERARCHY[requiredRole] ?? 999;
    return userLevel >= requiredLevel;
  }

  static canAccessRoute(user: any, route: string): boolean {
    const routePermissions = {
      '/admin': 'admin',
      '/super-admin': 'super_admin',
      '/user-management': 'admin',
      // ... define route permissions
    };

    const requiredRole = routePermissions[route];
    if (!requiredRole) return true; // Public route

    return this.hasPermission(user?.role, requiredRole);
  }

  // HOC for protecting components
  static withRoleGuard<P extends object>(
    Component: React.ComponentType<P>,
    requiredRole: string
  ) {
    return (props: P) => {
      const { user } = useAppStore(state => state.auth);

      if (!user || !this.hasPermission(user.role, requiredRole)) {
        return <div>Access Denied</div>;
      }

      return <Component {...props} />;
    };
  }
}
```

## 🚨 **Security Monitoring**

### **Intrusion Detection**
```typescript
// Detect suspicious activity
class SecurityMonitor {
  private static readonly MAX_FAILED_ATTEMPTS = 5;
  private static readonly LOCKOUT_DURATION = 15 * 60 * 1000; // 15 minutes

  private static getFailedAttempts(): number {
    return parseInt(localStorage.getItem('failed_auth_attempts') || '0');
  }

  private static setFailedAttempts(count: number): void {
    localStorage.setItem('failed_auth_attempts', count.toString());
    if (count > 0) {
      localStorage.setItem('last_failed_attempt', Date.now().toString());
    }
  }

  static recordFailedAttempt(): boolean {
    const current = this.getFailedAttempts();
    const newCount = current + 1;

    this.setFailedAttempts(newCount);

    if (newCount >= this.MAX_FAILED_ATTEMPTS) {
      console.warn('🚨 Account temporarily locked due to failed attempts');
      return true; // Account locked
    }

    return false;
  }

  static isAccountLocked(): boolean {
    const failedAttempts = this.getFailedAttempts();

    if (failedAttempts < this.MAX_FAILED_ATTEMPTS) {
      return false;
    }

    const lastAttempt = parseInt(localStorage.getItem('last_failed_attempt') || '0');
    const timeSinceLastAttempt = Date.now() - lastAttempt;

    if (timeSinceLastAttempt > this.LOCKOUT_DURATION) {
      // Lockout expired, reset counter
      this.clearFailedAttempts();
      return false;
    }

    return true;
  }

  static clearFailedAttempts(): void {
    localStorage.removeItem('failed_auth_attempts');
    localStorage.removeItem('last_failed_attempt');
  }

  // Monitor for suspicious patterns
  static detectSuspiciousActivity(): void {
    const patterns = {
      rapidTokenRefresh: this.checkRapidTokenRefresh(),
      multipleTabsAuth: this.checkMultipleTabsAuth(),
      unusualApiCalls: this.checkUnusualApiCalls(),
    };

    Object.entries(patterns).forEach(([pattern, detected]) => {
      if (detected) {
        console.warn(`🚨 Suspicious activity detected: ${pattern}`);
        // Could trigger additional security measures
      }
    });
  }

  private static checkRapidTokenRefresh(): boolean {
    // Implementation for detecting rapid token refresh attempts
    return false;
  }

  private static checkMultipleTabsAuth(): boolean {
    // Implementation for detecting multiple authentication tabs
    return false;
  }

  private static checkUnusualApiCalls(): boolean {
    // Implementation for detecting unusual API call patterns
    return false;
  }
}
```

### **Audit Logging**
```typescript
// Security event logging
class SecurityLogger {
  private static readonly LOG_EVENTS = {
    LOGIN_SUCCESS: 'login_success',
    LOGIN_FAILED: 'login_failed',
    TOKEN_REFRESH: 'token_refresh',
    LOGOUT: 'logout',
    PERMISSION_DENIED: 'permission_denied',
    SUSPICIOUS_ACTIVITY: 'suspicious_activity',
  };

  static logSecurityEvent(event: string, details: any = {}): void {
    const logEntry = {
      event,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      details,
    };

    // Log to console (development)
    console.log('🔐 Security Event:', logEntry);

    // Send to backend (production)
    if (process.env.NODE_ENV === 'production') {
      this.sendToBackend(logEntry);
    }

    // Store locally for debugging
    this.storeLocalLog(logEntry);
  }

  private static async sendToBackend(logEntry: any): Promise<void> {
    try {
      await fetch('/api/security/log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(logEntry)
      });
    } catch (error) {
      console.error('Failed to send security log:', error);
    }
  }

  private static storeLocalLog(logEntry: any): void {
    const logs = JSON.parse(localStorage.getItem('security_logs') || '[]');
    logs.push(logEntry);

    // Keep only last 50 logs
    if (logs.length > 50) {
      logs.splice(0, logs.length - 50);
    }

    localStorage.setItem('security_logs', JSON.stringify(logs));
  }

  static getLocalLogs(): any[] {
    return JSON.parse(localStorage.getItem('security_logs') || '[]');
  }
}
```

## 🚫 **Security Anti-Patterns**

### **❌ What NOT to Do:**

```typescript
// 1. Plain text storage
localStorage.setItem('token', 'plain-jwt-token'); // NEVER!

// 2. Tokens in URLs
window.location.href = `/dashboard?token=${token}`; // NEVER!

// 3. Tokens in console logs
console.log('User token:', token); // NEVER!

// 4. Long-lived tokens without refresh
const EXPIRES_IN = 365 * 24 * 60 * 60 * 1000; // 1 year - TOO LONG!

// 5. Ignoring HTTPS
fetch('http://api.example.com/auth', { ... }); // NEVER over HTTP!

// 6. Client-side role validation only
if (user.role === 'admin') {
  showAdminPanel(); // Backend must also validate!
}
```

### **✅ Security Checklist:**

- [ ] Tokens encrypted before storage
- [ ] sessionStorage for desktop, localStorage for mobile only
- [ ] Token expiration respected
- [ ] Backend validation for all auth operations
- [ ] HTTPS in production
- [ ] Content Security Policy implemented
- [ ] Failed attempt monitoring
- [ ] Security event logging
- [ ] Regular token refresh
- [ ] Proper logout cleanup
- [ ] Role-based access control
- [ ] Input validation for auth forms

## 🔧 **Production Security Configuration**

```typescript
// Environment-specific security settings
const SECURITY_CONFIG = {
  development: {
    encryption: 'basic',           // Simple base64
    tokenRefreshInterval: 30 * 60 * 1000,  // 30 minutes
    logging: 'verbose',
    failedAttemptLimit: 10,        // More lenient for testing
  },
  production: {
    encryption: 'aes-256-gcm',     // Strong encryption
    tokenRefreshInterval: 5 * 60 * 1000,   // 5 minutes
    logging: 'errors-only',
    failedAttemptLimit: 3,         // Strict for security
    additionalHeaders: {
      'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'X-XSS-Protection': '1; mode=block',
    }
  }
};

export const getSecurityConfig = () => {
  return SECURITY_CONFIG[process.env.NODE_ENV] || SECURITY_CONFIG.development;
};
```

Volg deze practices om je auth system veilig te houden! 🔒