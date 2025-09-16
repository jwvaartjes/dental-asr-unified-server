# Mobile Frontend Implementation Guide

## Overview

This guide shows how to implement mobile device authentication that **inherits desktop authentication** through pairing codes. The mobile device will automatically get the same user credentials as the desktop that generated the pairing code.

## 🔧 Environment Configuration

First, ensure your environment variables are configured. Create a `.env` file in your project root:

```env
# Backend API URL
VITE_API_URL=http://localhost:8089

# WebSocket URL
VITE_WS_URL=ws://localhost:8089/ws
```

**Note**: For Vite projects, use `VITE_` prefix. For Create React App, use `REACT_APP_` prefix.

## 🔑 Authentication Flow

### 1. Mobile Token Request with Auth Inheritance

```javascript
// Mobile authentication with pairing code inheritance
async function authenticateMobile(pairCode, fallbackUsername = "mobile_user") {
    // Get API URL from environment variables
    const apiUrl = import.meta.env.VITE_API_URL;

    try {
        const response = await fetch(`${apiUrl}/api/auth/ws-token-mobile`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Origin': window.location.origin
            },
            body: JSON.stringify({
                pair_code: pairCode,           // 6-digit code from desktop
                username: fallbackUsername    // Used only if inheritance fails
            })
        });

        if (!response.ok) {
            throw new Error(`Authentication failed: ${response.status}`);
        }

        const data = await response.json();

        // Check if mobile inherited desktop authentication
        if (data.inherited_from) {
            console.log(`✅ Success: Inherited auth from ${data.inherited_from}`);
            console.log(`📱 Mobile is now authenticated as: ${data.inherited_from}`);
        } else {
            console.log(`⚠️ Using fallback authentication: ${fallbackUsername}`);
        }

        return {
            token: data.token,
            expiresIn: data.expires_in,
            inheritedFrom: data.inherited_from,
            pairingCode: data.pairing_code,
            isInherited: !!data.inherited_from
        };
    } catch (error) {
        console.error('Mobile authentication failed:', error);
        throw error;
    }
}
```

### 2. React Hook for Mobile Authentication

```javascript
// hooks/useMobileAuth.js
import { useState, useCallback } from 'react';

export const useMobileAuth = () => {
    const [authState, setAuthState] = useState({
        isAuthenticated: false,
        token: null,
        inheritedFrom: null,
        isInherited: false,
        loading: false,
        error: null
    });

    const authenticateWithPairCode = useCallback(async (pairCode) => {
        setAuthState(prev => ({ ...prev, loading: true, error: null }));

        try {
            const authResult = await authenticateMobile(pairCode, "mobile_fallback");

            // Store token for persistence (survives browser refresh)
            localStorage.setItem('mobile_auth_token', authResult.token);
            localStorage.setItem('mobile_inherited_from', authResult.inheritedFrom || '');

            setAuthState({
                isAuthenticated: true,
                token: authResult.token,
                inheritedFrom: authResult.inheritedFrom,
                isInherited: authResult.isInherited,
                loading: false,
                error: null
            });

            return authResult;
        } catch (error) {
            setAuthState(prev => ({
                ...prev,
                loading: false,
                error: error.message
            }));
            throw error;
        }
    }, []);

    const logout = useCallback(() => {
        localStorage.removeItem('mobile_auth_token');
        localStorage.removeItem('mobile_inherited_from');
        setAuthState({
            isAuthenticated: false,
            token: null,
            inheritedFrom: null,
            isInherited: false,
            loading: false,
            error: null
        });
    }, []);

    // Restore auth on page refresh
    const restoreAuth = useCallback(() => {
        const token = localStorage.getItem('mobile_auth_token');
        const inheritedFrom = localStorage.getItem('mobile_inherited_from');

        if (token) {
            setAuthState({
                isAuthenticated: true,
                token,
                inheritedFrom: inheritedFrom || null,
                isInherited: !!inheritedFrom,
                loading: false,
                error: null
            });
        }
    }, []);

    return {
        ...authState,
        authenticateWithPairCode,
        logout,
        restoreAuth
    };
};
```

### 3. Mobile Pairing Component

```javascript
// components/MobilePairingForm.jsx
import React, { useState } from 'react';
import { useMobileAuth } from '../hooks/useMobileAuth';

export const MobilePairingForm = ({ onSuccess }) => {
    const [pairCode, setPairCode] = useState('');
    const { authenticateWithPairCode, loading, error } = useMobileAuth();

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (pairCode.length !== 6) {
            alert('Please enter a valid 6-digit pairing code');
            return;
        }

        try {
            const authResult = await authenticateWithPairCode(pairCode);

            if (authResult.isInherited) {
                alert(`✅ Successfully paired! You are now authenticated as: ${authResult.inheritedFrom}`);
            } else {
                alert('⚠️ Paired with fallback authentication');
            }

            onSuccess?.(authResult);
        } catch (error) {
            alert(`❌ Pairing failed: ${error.message}`);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="mobile-pairing-form">
            <h2>📱 Mobile Device Pairing</h2>
            <p>Enter the 6-digit code shown on the desktop</p>

            <input
                type="text"
                value={pairCode}
                onChange={(e) => setPairCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="000000"
                maxLength={6}
                className="pair-code-input"
                disabled={loading}
            />

            <button type="submit" disabled={loading || pairCode.length !== 6}>
                {loading ? 'Pairing...' : 'Pair Device'}
            </button>

            {error && <div className="error">{error}</div>}
        </form>
    );
};
```

## 🔌 WebSocket Connection with Inherited Auth

### 1. Mobile WebSocket Hook

```javascript
// hooks/useMobileWebSocket.js
import { useState, useEffect, useRef, useCallback } from 'react';

export const useMobileWebSocket = (authToken) => {
    const [connectionState, setConnectionState] = useState({
        isConnected: false,
        error: null,
        messages: []
    });

    const websocketRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);

    const connect = useCallback(() => {
        if (!authToken) {
            console.warn('No auth token available for WebSocket connection');
            return;
        }

        try {
            // Get WebSocket URL from environment variables
            const wsUrl = import.meta.env.VITE_WS_URL;
            const subprotocol = `Bearer.${authToken}`;

            console.log('📱 Mobile connecting to WebSocket with inherited auth...');

            websocketRef.current = new WebSocket(wsUrl, [subprotocol]);

            websocketRef.current.onopen = () => {
                console.log('✅ Mobile WebSocket connected');
                setConnectionState(prev => ({
                    ...prev,
                    isConnected: true,
                    error: null
                }));

                // Send mobile identification
                const identifyMessage = {
                    type: 'identify',
                    device_type: 'mobile',
                    session_id: `mobile-${Date.now()}`
                };

                websocketRef.current.send(JSON.stringify(identifyMessage));
            };

            websocketRef.current.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    console.log('📱 Mobile received:', message);

                    setConnectionState(prev => ({
                        ...prev,
                        messages: [...prev.messages, message]
                    }));
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };

            websocketRef.current.onclose = (event) => {
                console.log('📱 Mobile WebSocket closed:', event.code, event.reason);
                setConnectionState(prev => ({
                    ...prev,
                    isConnected: false
                }));

                // Auto-reconnect after 3 seconds
                if (authToken) {
                    reconnectTimeoutRef.current = setTimeout(connect, 3000);
                }
            };

            websocketRef.current.onerror = (error) => {
                console.error('📱 Mobile WebSocket error:', error);
                setConnectionState(prev => ({
                    ...prev,
                    error: 'Connection failed'
                }));
            };

        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            setConnectionState(prev => ({
                ...prev,
                error: error.message
            }));
        }
    }, [authToken]);

    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
        }

        if (websocketRef.current) {
            websocketRef.current.close();
            websocketRef.current = null;
        }

        setConnectionState({
            isConnected: false,
            error: null,
            messages: []
        });
    }, []);

    const sendMessage = useCallback((message) => {
        if (websocketRef.current?.readyState === WebSocket.OPEN) {
            websocketRef.current.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket not connected, cannot send message');
        }
    }, []);

    // Auto-connect when token is available
    useEffect(() => {
        if (authToken) {
            connect();
        }

        return () => {
            disconnect();
        };
    }, [authToken, connect, disconnect]);

    return {
        ...connectionState,
        connect,
        disconnect,
        sendMessage
    };
};
```

### 2. Complete Mobile App Component

```javascript
// components/MobileApp.jsx
import React, { useEffect, useState } from 'react';
import { useMobileAuth } from '../hooks/useMobileAuth';
import { useMobileWebSocket } from '../hooks/useMobileWebSocket';
import { MobilePairingForm } from './MobilePairingForm';

export const MobileApp = () => {
    const {
        isAuthenticated,
        token,
        inheritedFrom,
        isInherited,
        restoreAuth,
        logout
    } = useMobileAuth();

    const {
        isConnected,
        messages,
        sendMessage,
        error: wsError
    } = useMobileWebSocket(token);

    // Restore authentication on component mount
    useEffect(() => {
        restoreAuth();
    }, [restoreAuth]);

    const handlePairingSuccess = (authResult) => {
        console.log('🎉 Mobile successfully paired and authenticated!');
        console.log('Auth result:', authResult);
    };

    const handleSendTestMessage = () => {
        sendMessage({
            type: 'test_message',
            content: 'Hello from mobile!',
            timestamp: new Date().toISOString()
        });
    };

    if (!isAuthenticated) {
        return (
            <div className="mobile-app">
                <MobilePairingForm onSuccess={handlePairingSuccess} />
            </div>
        );
    }

    return (
        <div className="mobile-app">
            <header className="mobile-header">
                <h1>📱 Mobile Device</h1>
                <div className="auth-status">
                    {isInherited ? (
                        <p>✅ Authenticated as: <strong>{inheritedFrom}</strong> (inherited from desktop)</p>
                    ) : (
                        <p>⚠️ Using fallback authentication</p>
                    )}
                </div>
                <button onClick={logout} className="logout-btn">Logout</button>
            </header>

            <main className="mobile-content">
                <section className="connection-status">
                    <h3>Connection Status</h3>
                    <p>WebSocket: {isConnected ? '🟢 Connected' : '🔴 Disconnected'}</p>
                    {wsError && <p className="error">Error: {wsError}</p>}
                </section>

                <section className="message-section">
                    <h3>Messages</h3>
                    <button onClick={handleSendTestMessage} disabled={!isConnected}>
                        Send Test Message
                    </button>

                    <div className="messages-list">
                        {messages.map((msg, index) => (
                            <div key={index} className="message">
                                <strong>{msg.type}:</strong> {JSON.stringify(msg, null, 2)}
                            </div>
                        ))}
                    </div>
                </section>
            </main>
        </div>
    );
};
```

## 📱 Usage Example

```javascript
// App.jsx - Mobile implementation
import React from 'react';
import { MobileApp } from './components/MobileApp';

function App() {
    return (
        <div className="App">
            <MobileApp />
        </div>
    );
}

export default App;
```

## 🔍 Testing the Mobile Implementation

### 1. Test Auth Inheritance

```javascript
// Test script for mobile auth inheritance
async function testMobileAuthInheritance() {
    const pairCode = "123456"; // Get from desktop
    const apiUrl = import.meta.env.VITE_API_URL;

    try {
        const response = await fetch(`${apiUrl}/api/auth/ws-token-mobile`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Origin': window.location.origin
            },
            body: JSON.stringify({
                pair_code: pairCode,
                username: "test_mobile_user"
            })
        });

        const data = await response.json();

        console.log('Response:', data);
        console.log('Inherited from:', data.inherited_from);
        console.log('Is inherited:', !!data.inherited_from);
    } catch (error) {
        console.error('Test failed:', error);
    }
}
```

## 🎯 Key Implementation Points

### 1. **Auth Inheritance Priority**
- Mobile **ALWAYS** tries to inherit desktop auth first
- Only falls back to provided username if inheritance fails
- Clear indication to user whether auth was inherited

### 2. **Token Persistence**
- Mobile tokens survive browser refresh (localStorage)
- 8-hour token lifespan matches desktop
- Automatic restoration on app load

### 3. **WebSocket Authentication**
- Uses inherited token for WebSocket connection
- Bearer token in subprotocol format
- Auto-reconnection with inherited credentials

### 4. **Error Handling**
- Clear feedback on pairing success/failure
- Graceful fallback authentication
- Connection state management

### 5. **User Experience**
- Visual indication of inherited vs fallback auth
- Real-time connection status
- Message history display

## 🌍 Environment Variables Reference

### Vite Projects (Recommended)
```javascript
// Access environment variables
const apiUrl = import.meta.env.VITE_API_URL;
const wsUrl = import.meta.env.VITE_WS_URL;
```

### Create React App
```javascript
// Access environment variables
const apiUrl = process.env.REACT_APP_API_URL;
const wsUrl = process.env.REACT_APP_WS_URL;
```

### Next.js
```javascript
// Access environment variables
const apiUrl = process.env.NEXT_PUBLIC_API_URL;
const wsUrl = process.env.NEXT_PUBLIC_WS_URL;
```

## 🚀 Production Configuration

For production deployment, update your environment variables:

```env
# Production
VITE_API_URL=https://your-api-domain.com
VITE_WS_URL=wss://your-api-domain.com/ws
```

This implementation ensures mobile devices seamlessly inherit desktop authentication through the pairing system, providing a unified user experience across devices.