# 🔐 **Frontend Auto-Logout Implementation Guide**

## **Token Expiration & Automatic Logout System**

### **🎯 Problem Solved:**
Frontend receives "Desktop authentication required" when token expires, causing infinite reconnection loops without user awareness.

### **✅ Backend Support:**
New endpoint available: `GET /api/auth/token-status`

**Response format:**
```json
// Valid token
{
  "valid": true,
  "expired": false,
  "authenticated": true,
  "expires_at": "2025-09-17T22:00:00Z",
  "time_until_expiry_seconds": 7200,
  "time_until_expiry_minutes": 120,
  "should_refresh_soon": false
}

// Expired token
{
  "valid": false,
  "expired": true,
  "reason": "token_expired",
  "expires_at": "2025-09-17T14:00:00Z",
  "action_required": "logout"
}

// No token
{
  "valid": false,
  "expired": false,
  "reason": "no_token",
  "action_required": "login"
}
```

## **🔧 Frontend Implementation Requirements**

### **1. Pre-Connection Token Validation**

```typescript
// Check token before any WebSocket connection attempt
const checkTokenBeforeConnect = async (): Promise<boolean> => {
  try {
    const response = await fetch('/api/auth/token-status');
    const tokenStatus = await response.json();

    if (tokenStatus.expired) {
      await autoLogout('Session expired. Please log in again.');
      return false;
    }

    if (!tokenStatus.valid) {
      await autoLogout('Authentication required. Please log in.');
      return false;
    }

    // Warn if token expires soon (< 30 minutes)
    if (tokenStatus.should_refresh_soon) {
      showExpirationWarning(`Session expires in ${tokenStatus.time_until_expiry_minutes} minutes`);
    }

    return true;

  } catch (error) {
    console.error('Token validation failed:', error);
    await autoLogout('Authentication check failed. Please log in again.');
    return false;
  }
};

// Use before WebSocket connection
const connectWebSocket = async () => {
  const tokenValid = await checkTokenBeforeConnect();
  if (!tokenValid) {
    return; // Don't attempt connection with invalid token
  }

  // Proceed with WebSocket connection...
  websocket = new WebSocket(WS_URL);
};
```

### **2. Enhanced Device Identification**

```typescript
// Send enhanced identification message
const identifyDevice = async () => {
  const identifyMessage = {
    type: "identify",
    device_type: "desktop", // or "mobile"
    session_id: `desktop-${Date.now()}-${generateRandomId()}`,
    user_agent: navigator.userAgent
  };

  websocket.send(JSON.stringify(identifyMessage));

  // Wait for identification confirmation
  await waitForMessage("identified", 5000);
};

// Generate unique session ID
const generateRandomId = () => {
  return Math.random().toString(36).substring(2, 15);
};
```

### **3. WebSocket Authentication Error Handling**

```typescript
// Enhanced WebSocket error handling
websocket.onerror = (error) => {
  console.error('WebSocket error:', error);

  // Check if it's an authentication error
  if (error.message && error.message.includes('authentication')) {
    autoLogout('WebSocket authentication failed. Session may have expired.');
  }
};

websocket.onclose = (event) => {
  console.log('WebSocket closed:', event.code, event.reason);

  // Check for authentication-related close codes
  if (event.code === 1008) { // Policy Violation (auth failure)
    autoLogout('Connection rejected due to authentication failure.');
    return;
  }

  // For other disconnects, check token status before reconnecting
  checkTokenBeforeReconnect();
};

const checkTokenBeforeReconnect = async () => {
  const tokenValid = await checkTokenBeforeConnect();
  if (tokenValid) {
    // Token still valid, safe to reconnect
    setTimeout(() => reconnect(), getBackoffDelay());
  }
  // If token invalid, autoLogout already called
};
```

### **4. Disconnect Event Handling**

```typescript
// Handle disconnect notifications from paired devices
websocket.onmessage = (event) => {
  const msg = JSON.parse(event.data);

  // Handle device disconnect notifications
  if (msg.type === 'desktop_disconnected') {
    if (msg.force_disconnect) {
      websocket.close();
      showNotification('Desktop connection lost - Reconnection required');
    }
  }

  if (msg.type === 'mobile_disconnected') {
    showNotification('Mobile device disconnected');
    // Desktop can continue without mobile
  }

  if (msg.type === 'connection_timeout') {
    if (msg.reason === 'security_unidentified') {
      showSecurityAlert('Connection blocked: Device identification required');
    } else {
      showNotification(`Connection timed out: ${msg.reason}`);
    }
    websocket.close();
  }

  if (msg.type === 'server_restarting') {
    showNotification('Server restarting - reconnecting automatically...');
    setTimeout(() => reconnect(), msg.reconnect_in || 5000);
  }
};
```

### **5. Automatic Logout Implementation**

```typescript
const autoLogout = async (reason: string) => {
  console.log('Auto-logout triggered:', reason);

  try {
    // 1. Clear all authentication state
    clearAuthTokens();
    clearConnectionState();
    clearPairingState();

    // 2. Close any active WebSocket connections
    if (websocket && websocket.readyState === WebSocket.OPEN) {
      websocket.close(1000, 'Auto-logout');
    }

    // 3. Clear local storage / session storage
    localStorage.removeItem('session_token');
    localStorage.removeItem('pairing_code');
    sessionStorage.clear();

    // 4. Reset all application state
    setAuthenticated(false);
    setUser(null);
    setPairingCode(null);
    setConnectionState('disconnected');
    setInitializationAttempted(false);

    // 5. Show user notification
    showNotification({
      type: 'warning',
      message: reason,
      duration: 5000
    });

    // 6. Redirect to login page
    router.push('/login');

  } catch (error) {
    console.error('Error during auto-logout:', error);
    // Force page reload as fallback
    window.location.href = '/login';
  }
};

const clearAuthTokens = () => {
  // Clear all possible token storage locations
  localStorage.removeItem('auth_token');
  localStorage.removeItem('session_token');
  localStorage.removeItem('jwt_token');
  sessionStorage.removeItem('auth_token');

  // Clear any auth cookies (if accessible)
  document.cookie = 'session_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
};

const clearConnectionState = () => {
  // Reset all connection-related state
  setConnectionState('disconnected');
  setInitializationAttempted(false);
  setConnected(false);
  setClientId(null);
};

const clearPairingState = () => {
  // Reset all pairing-related state
  setPairingCode(null);
  setChannel(null);
  setPairedDevice(null);
  setDeviceType(null);
};
```

### **6. Proactive Token Monitoring**

```typescript
// Check token status periodically (every 5 minutes)
const startTokenMonitoring = () => {
  const checkInterval = setInterval(async () => {
    try {
      const response = await fetch('/api/auth/token-status');
      const tokenStatus = await response.json();

      if (tokenStatus.expired) {
        clearInterval(checkInterval);
        await autoLogout('Session expired.');
        return;
      }

      // Warn when token expires soon (30 minutes)
      if (tokenStatus.should_refresh_soon) {
        showExpirationWarning(
          `Session expires in ${tokenStatus.time_until_expiry_minutes} minutes. ` +
          'You may need to log in again soon.'
        );
      }

    } catch (error) {
      console.error('Token monitoring error:', error);
      // Don't auto-logout on monitoring errors, but log for debugging
    }
  }, 5 * 60 * 1000); // Check every 5 minutes

  // Clean up on component unmount
  return () => clearInterval(checkInterval);
};

// Start monitoring after successful login
useEffect(() => {
  if (authenticated) {
    const cleanup = startTokenMonitoring();
    return cleanup;
  }
}, [authenticated]);
```

### **7. User Experience Enhancements**

```typescript
// Show user-friendly expiration warnings
const showExpirationWarning = (message: string) => {
  showNotification({
    type: 'info',
    message: message,
    action: {
      label: 'Extend Session',
      onClick: () => {
        // Refresh token or redirect to re-login
        window.location.href = '/login?return=' + encodeURIComponent(window.location.pathname);
      }
    },
    duration: 10000 // 10 seconds
  });
};

// Handle connection failures gracefully
const handleConnectionFailure = async (error: any) => {
  // Check if it's a token issue first
  const tokenValid = await checkTokenBeforeConnect();

  if (!tokenValid) {
    // Token issue already handled by autoLogout
    return;
  }

  // Handle other connection issues
  console.error('Non-authentication connection error:', error);
  showNotification({
    type: 'error',
    message: 'Connection failed. Retrying...',
    duration: 3000
  });

  // Retry with exponential backoff
  setTimeout(() => reconnect(), getBackoffDelay());
};
```

## **🎖️ Implementation Checklist**

### **Required Frontend Changes:**
- [ ] **Add token validation** before WebSocket connections
- [ ] **Implement autoLogout function** with complete state cleanup
- [ ] **Add periodic token monitoring** (every 5 minutes)
- [ ] **Handle WebSocket auth errors** gracefully
- [ ] **Add expiration warnings** (30 minutes before expiry)
- [ ] **Update reconnection logic** to check token first
- [ ] **Enhanced device identification** with session_id
- [ ] **Disconnect event handling** for paired devices

### **User Experience Improvements:**
- [ ] **Clear error messages** for different failure types
- [ ] **Proactive expiration warnings** with action buttons
- [ ] **Graceful session extension** options
- [ ] **Automatic state cleanup** on logout
- [ ] **Smooth login redirects** with return URLs
- [ ] **Device disconnect notifications** for pairing

### **Testing Requirements:**
- [ ] **Test auto-logout** with expired tokens
- [ ] **Verify state cleanup** after logout
- [ ] **Test reconnection** after fresh login
- [ ] **Validate expiration warnings** appear correctly
- [ ] **Confirm no infinite loops** after logout
- [ ] **Test disconnect notifications** between paired devices

## **🚀 Result: Smooth User Experience**

With these implementations, users will experience:
- ✅ **Automatic logout** when tokens expire (no more connection loops)
- ✅ **Proactive warnings** before expiration
- ✅ **Clean state management** and proper cleanup
- ✅ **Clear error messages** and user guidance
- ✅ **Seamless re-authentication** flow
- ✅ **Enhanced device identification** with session tracking
- ✅ **Graceful disconnect handling** for paired devices

**The authentication system becomes production-grade with excellent UX!** 🎯✨