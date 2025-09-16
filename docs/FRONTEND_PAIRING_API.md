# 📱 Frontend Pairing API Guide

**Simple, working API documentation for React frontend integration**

## 🚀 Base URL
```
http://localhost:8089
```

## 📡 Required Headers
```javascript
{
  "Content-Type": "application/json",
  "Origin": "http://localhost:5173"  // Your frontend URL
}
```

---

## 🖥️ Desktop: Generate Pairing Code

**Endpoint:** `POST /api/generate-pair-code`

**Request:**
```javascript
const response = await fetch('http://localhost:8089/api/generate-pair-code', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Origin': 'http://localhost:5173'
  },
  body: JSON.stringify({
    desktop_session_id: "your-unique-desktop-id"
  })
});

const data = await response.json();
```

**Response (200 OK):**
```json
{
  "code": "670913",
  "expires_at": "2025-09-15T07:15:42.824896Z",
  "channel_id": "pair-670913"
}
```

**React Usage:**
```javascript
const { code, expires_at, channel_id } = data;
// Display code to user
// Use channel_id for WebSocket connection
```

---

## 📱 Mobile: Pair with Code

**Endpoint:** `POST /api/pair-device`

**Request:**
```javascript
const response = await fetch('http://localhost:8089/api/pair-device', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Origin': 'http://localhost:5173'
  },
  body: JSON.stringify({
    code: "670913",
    mobile_session_id: "your-unique-mobile-id"
  })
});

const data = await response.json();
```

**Response (200 OK - Success):**
```json
{
  "success": true,
  "channel_id": "pair-670913",
  "message": "Device paired successfully"
}
```

**Response (200 OK - Error):**
```json
{
  "success": false,
  "error": "INVALID_CODE",
  "message": "Pairing code does not exist or has expired"
}
```

**React Usage:**
```javascript
if (data.success) {
  const { channel_id } = data;
  // Use channel_id for WebSocket connection
} else {
  console.error(data.message);
}
```

---

## 🔌 WebSocket Connection

**URL:** `ws://localhost:8089/ws`

**⚠️ CRITICAL: WebSocket Authentication Required!**
```javascript
// 1. First get a WebSocket token
const tokenResponse = await fetch('http://localhost:8089/api/auth/ws-token', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Origin': window.location.origin
  },
  body: JSON.stringify({ username: 'your-user' })
});
const { token } = await tokenResponse.json();

// 2. Connect with Bearer token in subprotocol
const ws = new WebSocket('ws://localhost:8089/ws', [`Bearer.${token}`]);
```

**📤 Join Channel Message (EXACT format required):**
```javascript
// ⚠️ MUST use "channel" NOT "channelId"
// ⚠️ MUST include "session_id"
ws.send(JSON.stringify({
  type: "join_channel",
  channel: "pair-670913",        // ✅ CORRECT: "channel"
  device_type: "desktop",        // ✅ "desktop" or "mobile"
  session_id: "your-session-id"  // ✅ REQUIRED: unique session ID
}));
```

**❌ WRONG Format (will cause validation error):**
```javascript
// DON'T DO THIS:
{
  type: "join_channel",
  channelId: "pair-670913",  // ❌ WRONG: should be "channel"
  device_type: "desktop"     // ❌ MISSING: session_id
}
```

---

## 📝 Complete React Example

```typescript
interface PairingResponse {
  code: string;
  expires_at: string;
  channel_id: string;
}

interface PairDeviceResponse {
  success: boolean;
  channel_id?: string;
  message: string;
  error?: string;
}

// Desktop: Generate code
const generatePairingCode = async (desktopSessionId: string): Promise<PairingResponse> => {
  const response = await fetch('http://localhost:8089/api/generate-pair-code', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Origin': window.location.origin
    },
    body: JSON.stringify({
      desktop_session_id: desktopSessionId
    })
  });

  if (!response.ok) {
    throw new Error(`Failed to generate pairing code: ${response.status}`);
  }

  return response.json();
};

// Mobile: Pair with code
const pairWithCode = async (code: string, mobileSessionId: string): Promise<PairDeviceResponse> => {
  const response = await fetch('http://localhost:8089/api/pair-device', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Origin': window.location.origin
    },
    body: JSON.stringify({
      code,
      mobile_session_id: mobileSessionId
    })
  });

  if (!response.ok) {
    throw new Error(`Failed to pair device: ${response.status}`);
  }

  return response.json();
};

// Usage in React component
function PairingComponent() {
  const [pairingCode, setPairingCode] = useState<string>('');
  const [channelId, setChannelId] = useState<string>('');

  const handleGenerateCode = async () => {
    try {
      const result = await generatePairingCode('desktop-session-123');
      setPairingCode(result.code);
      setChannelId(result.channel_id);
      console.log('Code expires at:', new Date(result.expires_at));
    } catch (error) {
      console.error('Failed to generate code:', error);
    }
  };

  const handlePairDevice = async (inputCode: string) => {
    try {
      const result = await pairWithCode(inputCode, 'mobile-session-456');
      if (result.success) {
        setChannelId(result.channel_id!);
        console.log('Paired successfully!');
      } else {
        console.error('Pairing failed:', result.message);
      }
    } catch (error) {
      console.error('Failed to pair:', error);
    }
  };

  return (
    <div>
      <button onClick={handleGenerateCode}>
        Generate Pairing Code
      </button>
      {pairingCode && (
        <p>Pairing Code: {pairingCode}</p>
      )}
      {channelId && (
        <p>Channel: {channelId}</p>
      )}
    </div>
  );
}
```

---

## ✅ Key Points for Frontend

1. **Response format is exactly as shown** - no parsing needed
2. **Always check response.ok** before calling response.json()
3. **Use the channel_id** from either endpoint for WebSocket connection
4. **Codes expire in 5 minutes** - handle expiration gracefully
5. **Origin header is required** for CORS
6. **Session IDs should be unique** per device/session
7. **⚠️ WebSocket MUST use Bearer token authentication**
8. **⚠️ Use "channel" NOT "channelId" in WebSocket messages**
9. **⚠️ Always include "session_id" in join_channel messages**
10. **⚠️ Respect rate limits - add delays between retries!**

---

## 🐛 Error Handling

**Common error responses:**
- `403 Forbidden` - Invalid origin
- `422 Unprocessable Entity` - Invalid request format
- `429 Too Many Requests` - Rate limited
- `500 Internal Server Error` - Server error

**Always wrap API calls in try-catch blocks!**
