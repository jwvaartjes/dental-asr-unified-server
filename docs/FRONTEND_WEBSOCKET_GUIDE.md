# 🔌 Complete Frontend WebSocket Guide

**Comprehensive WebSocket integration for React frontend with Bearer authentication**

---

## 🚀 Quick Start

### 1. Get Authentication Token
```typescript
const getWebSocketToken = async (): Promise<string> => {
  const response = await fetch('http://localhost:8089/api/auth/ws-token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Origin': window.location.origin
    },
    body: JSON.stringify({ username: 'your-user' })
  });

  if (!response.ok) {
    throw new Error(`Failed to get WebSocket token: ${response.status}`);
  }

  const { token } = await response.json();
  return token;
};
```

### 2. Create WebSocket Connection
```typescript
const connectWebSocket = async (): Promise<WebSocket> => {
  const token = await getWebSocketToken();

  // ⚠️ CRITICAL: Use Bearer token in subprotocol
  const ws = new WebSocket('ws://localhost:8089/ws', [`Bearer.${token}`]);

  return new Promise((resolve, reject) => {
    ws.onopen = () => {
      console.log('✅ WebSocket connected');
      resolve(ws);
    };

    ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
      reject(error);
    };
  });
};
```

---

## 📤 WebSocket Message Formats

### ✅ Join Channel (Required after pairing)
```typescript
interface JoinChannelMessage {
  type: "join_channel";
  channel: string;        // ⚠️ MUST be "channel" NOT "channelId"
  device_type: "desktop" | "mobile";
  session_id: string;     // ⚠️ REQUIRED: unique session identifier
}

// Example usage:
ws.send(JSON.stringify({
  type: "join_channel",
  channel: "pair-123456",           // From pairing API response
  device_type: "desktop",           // or "mobile"
  session_id: "desktop-session-123" // Your unique session ID
}));
```

### ✅ Identify Device
```typescript
interface IdentifyMessage {
  type: "identify";
  device_type: "desktop" | "mobile";
  session_id: string;
}

ws.send(JSON.stringify({
  type: "identify",
  device_type: "desktop",
  session_id: "desktop-session-123"
}));
```

### ✅ Channel Message
```typescript
interface ChannelMessage {
  type: "channel_message";
  channelId: string;      // ⚠️ Note: "channelId" for channel_message type
  payload: any;
}

ws.send(JSON.stringify({
  type: "channel_message",
  channelId: "pair-123456",
  payload: {
    action: "settings_update",
    data: { volume: 75 }
  }
}));
```

### ✅ Mobile Initialization
```typescript
interface MobileInitMessage {
  type: "mobile_init";
  device_type: "mobile";
  pairing_code: string;   // 6-digit code from user input
  session_id: string;
}

ws.send(JSON.stringify({
  type: "mobile_init",
  device_type: "mobile",
  pairing_code: "123456",
  session_id: "mobile-session-456"
}));
```

### ✅ Ping/Pong (Keep-alive)
```typescript
// Send ping
ws.send(JSON.stringify({
  type: "ping",
  sequence: 1
}));

// Handle pong response
if (message.type === "pong") {
  console.log("Received pong:", message.sequence);
}
```

---

## 📥 Incoming Message Types

### Server Response Messages
```typescript
// Connection established
{
  type: "connected",
  client_id: "client_123456"
}

// Channel joined successfully
{
  type: "channel_joined",
  channel: "pair-123456"
}

// Device identified
{
  type: "identified",
  device_type: "desktop"
}

// Pairing success
{
  type: "pairing_success",
  code: "123456",
  message: "Devices paired successfully"
}

// Client joined channel
{
  type: "client_joined",
  client_id: "client_789012",
  device_type: "mobile"
}

// Client disconnected
{
  type: "mobile_disconnected",
  session_id: "client_789012",
  channel: "pair-123456",
  reason: "mobile_closed"
}

// Error messages
{
  type: "error",
  message: "Invalid message format",
  code: "VALIDATION_ERROR"
}
```

---

## 🎯 Complete React Hook Example

```typescript
import { useState, useEffect, useRef, useCallback } from 'react';

interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

interface UseWebSocketReturn {
  ws: WebSocket | null;
  isConnected: boolean;
  sendMessage: (message: WebSocketMessage) => void;
  joinChannel: (channelId: string, deviceType: 'desktop' | 'mobile', sessionId: string) => void;
  error: string | null;
}

export const useWebSocket = (): UseWebSocketReturn => {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(async () => {
    try {
      setError(null);

      // Get authentication token
      const tokenResponse = await fetch('http://localhost:8089/api/auth/ws-token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Origin': window.location.origin
        },
        body: JSON.stringify({ username: 'user' })
      });

      if (!tokenResponse.ok) {
        if (tokenResponse.status === 429) {
          // Rate limited - wait before retry
          const retryAfter = parseInt(tokenResponse.headers.get('retry-after') || '5');
          throw new Error(`Rate limited. Retry after ${retryAfter} seconds`);
        }
        throw new Error(`Token request failed: ${tokenResponse.status}`);
      }

      const { token } = await tokenResponse.json();

      // Create WebSocket connection with Bearer token
      const websocket = new WebSocket('ws://localhost:8089/ws', [`Bearer.${token}`]);

      websocket.onopen = () => {
        console.log('✅ WebSocket connected');
        setIsConnected(true);
        setWs(websocket);
        reconnectAttempts.current = 0;
      };

      websocket.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          console.log('📥 Received:', message);

          // Handle specific message types
          switch (message.type) {
            case 'connected':
              console.log('🔗 Connected with client ID:', message.client_id);
              break;
            case 'channel_joined':
              console.log('🎯 Joined channel:', message.channel);
              break;
            case 'error':
              console.error('🚨 WebSocket error:', message.message);
              setError(message.message);
              break;
          }
        } catch (parseError) {
          console.error('Failed to parse WebSocket message:', parseError);
        }
      };

      websocket.onclose = (event) => {
        console.log('🔌 WebSocket closed:', event.code, event.reason);
        setIsConnected(false);
        setWs(null);

        // Auto-reconnect with exponential backoff
        if (reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.pow(2, reconnectAttempts.current) * 1000; // 1s, 2s, 4s, 8s, 16s
          console.log(`🔄 Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current + 1})`);

          setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        } else {
          setError('Maximum reconnection attempts reached');
        }
      };

      websocket.onerror = (event) => {
        console.error('❌ WebSocket error:', event);
        setError('WebSocket connection error');
      };

    } catch (connectError: any) {
      console.error('Connection failed:', connectError);
      setError(connectError.message);

      // Retry with exponential backoff for rate limiting
      if (connectError.message.includes('Rate limited') && reconnectAttempts.current < maxReconnectAttempts) {
        const delay = Math.pow(2, reconnectAttempts.current) * 1000;
        setTimeout(() => {
          reconnectAttempts.current++;
          connect();
        }, delay);
      }
    }
  }, []);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (ws && isConnected) {
      ws.send(JSON.stringify(message));
      console.log('📤 Sent:', message);
    } else {
      console.warn('⚠️ Cannot send message: WebSocket not connected');
    }
  }, [ws, isConnected]);

  const joinChannel = useCallback((channelId: string, deviceType: 'desktop' | 'mobile', sessionId: string) => {
    sendMessage({
      type: "join_channel",
      channel: channelId,        // ⚠️ CORRECT: "channel" not "channelId"
      device_type: deviceType,
      session_id: sessionId      // ⚠️ REQUIRED field
    });
  }, [sendMessage]);

  // Connect on mount
  useEffect(() => {
    connect();
    return () => {
      ws?.close();
    };
  }, [connect]);

  return {
    ws,
    isConnected,
    sendMessage,
    joinChannel,
    error
  };
};
```

---

## 🎮 Usage in React Component

```typescript
function PairingComponent() {
  const { isConnected, sendMessage, joinChannel, error } = useWebSocket();
  const [channelId, setChannelId] = useState<string>('');
  const [deviceType] = useState<'desktop' | 'mobile'>('desktop');
  const sessionId = `${deviceType}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  const handleJoinChannel = () => {
    if (channelId && isConnected) {
      joinChannel(channelId, deviceType, sessionId);
    }
  };

  const handleSendMessage = () => {
    sendMessage({
      type: "channel_message",
      channelId: channelId,
      payload: {
        action: "test",
        data: { timestamp: new Date().toISOString() }
      }
    });
  };

  return (
    <div className="pairing-component">
      <div className="status">
        Status: {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
      </div>

      {error && (
        <div className="error">❌ {error}</div>
      )}

      <div className="controls">
        <input
          type="text"
          value={channelId}
          onChange={(e) => setChannelId(e.target.value)}
          placeholder="Enter channel ID (e.g., pair-123456)"
        />
        <button onClick={handleJoinChannel} disabled={!isConnected || !channelId}>
          Join Channel
        </button>
        <button onClick={handleSendMessage} disabled={!isConnected || !channelId}>
          Send Test Message
        </button>
      </div>
    </div>
  );
}
```

---

## 🚨 Common Mistakes & Fixes

### ❌ Wrong Message Format
```typescript
// WRONG:
{
  type: "join_channel",
  channelId: "pair-123456",  // Should be "channel"
  device_type: "desktop"     // Missing "session_id"
}

// CORRECT:
{
  type: "join_channel",
  channel: "pair-123456",    // ✅ Correct field name
  device_type: "desktop",
  session_id: "session-123"  // ✅ Required field
}
```

### ❌ Missing Bearer Token
```typescript
// WRONG:
new WebSocket('ws://localhost:8089/ws');

// CORRECT:
new WebSocket('ws://localhost:8089/ws', [`Bearer.${token}`]);
```

### ❌ Rate Limit Spam
```typescript
// WRONG - infinite loop:
useEffect(() => {
  getToken(); // No dependencies = infinite calls
});

// CORRECT - with proper dependencies:
useEffect(() => {
  getToken();
}, []); // Empty array = run once

// CORRECT - with retry delays:
const retryWithDelay = (attempt: number) => {
  const delay = Math.pow(2, attempt) * 1000; // Exponential backoff
  setTimeout(() => {
    getToken();
  }, delay);
};
```

---

## 🔧 Advanced Features

### Error Recovery
```typescript
const handleWebSocketError = (error: Event) => {
  console.error('WebSocket error:', error);

  // Close and attempt reconnection
  ws?.close();

  // Exponential backoff reconnection
  setTimeout(() => {
    connect();
  }, Math.pow(2, reconnectAttempts) * 1000);
};
```

### Message Queue
```typescript
const messageQueue = useRef<WebSocketMessage[]>([]);

const sendMessage = (message: WebSocketMessage) => {
  if (isConnected) {
    ws?.send(JSON.stringify(message));
  } else {
    // Queue message for when connection is restored
    messageQueue.current.push(message);
  }
};

// Process queued messages when connected
useEffect(() => {
  if (isConnected && messageQueue.current.length > 0) {
    messageQueue.current.forEach(message => {
      ws?.send(JSON.stringify(message));
    });
    messageQueue.current = [];
  }
}, [isConnected]);
```

### Heartbeat/Ping
```typescript
useEffect(() => {
  if (!isConnected) return;

  const pingInterval = setInterval(() => {
    sendMessage({
      type: "ping",
      sequence: Date.now()
    });
  }, 30000); // Every 30 seconds

  return () => clearInterval(pingInterval);
}, [isConnected, sendMessage]);
```

---

## 📊 WebSocket State Management

### With Zustand
```typescript
interface WebSocketStore {
  isConnected: boolean;
  channelId: string | null;
  messages: WebSocketMessage[];
  setConnected: (connected: boolean) => void;
  setChannelId: (channelId: string) => void;
  addMessage: (message: WebSocketMessage) => void;
}

const useWebSocketStore = create<WebSocketStore>((set) => ({
  isConnected: false,
  channelId: null,
  messages: [],
  setConnected: (connected) => set({ isConnected: connected }),
  setChannelId: (channelId) => set({ channelId }),
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  }))
}));
```

---

## 🐛 Debugging Tips

1. **Check WebSocket ReadyState:**
   ```javascript
   console.log('WebSocket state:', ws.readyState);
   // 0: CONNECTING, 1: OPEN, 2: CLOSING, 3: CLOSED
   ```

2. **Monitor Network Tab:** Look for WebSocket connection in browser DevTools

3. **Validate Message Format:** Use backend schema as reference

4. **Check Rate Limits:** Look for 429 responses in Network tab

5. **Bearer Token:** Verify token is valid and not expired

---

## ✅ Best Practices

1. **Always use Bearer token authentication**
2. **Implement exponential backoff for reconnections**
3. **Validate message formats before sending**
4. **Handle rate limiting gracefully**
5. **Use proper field names ("channel" not "channelId" for join_channel)**
6. **Include required fields like "session_id"**
7. **Implement message queueing for offline scenarios**
8. **Add heartbeat/ping for connection health**
9. **Clean up WebSocket connections on component unmount**
10. **Log all WebSocket events for debugging**

De WebSocket connectie is nu **production-ready** met correcte authenticatie en foutafhandeling! 🚀