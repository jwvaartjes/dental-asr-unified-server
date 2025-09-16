# Dental ASR - Lovable Integration Guide

Complete API documentation for integrating with the Dental ASR Unified Server from Lovable frontend applications.

## 🌐 Server Configuration

**Base URL**: `http://localhost:8089` (development)
**Production URL**: TBD
**CORS**: Automatically configured for all `*.lovable.app` and `*.lovable.dev` domains

## 🔐 Authentication Endpoints

### Overview
The server uses **httpOnly cookies** for secure authentication. No JWT tokens are returned in response bodies.

### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response**:
```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User Name",
    "role": "user",
    "permissions": {
      "canManageUsers": false,
      "canDeleteUsers": false,
      "canModifyAdminRoles": false,
      "isSuperAdmin": false
    }
  },
  "auth_method": "cookie",
  "expires_in": 28800
}
```

**Cookie Set**: `session_token` (HttpOnly, 8 hours, SameSite=lax)

### Magic Link Login
```http
POST /api/auth/login-magic
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Response**: Same as regular login

### Check Authentication Status
```http
GET /api/auth/status
```

**Response**:
```json
{
  "authenticated": true,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User Name",
    "role": "user"
  }
}
```

### Logout
```http
POST /api/auth/logout
```

**Response**:
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

### Verify Token
```http
GET /api/auth/verify
```

**Response**:
```json
{
  "valid": true,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User Name"
  }
}
```

## 📱 Device Pairing Flow

### Step 1: Desktop Generates Pairing Code

```http
POST /api/generate-pair-code
Content-Type: application/json

{
  "desktop_session_id": "unique-desktop-session-id"
}
```

**Response**:
```json
{
  "code": "123456",
  "expires_at": "2025-09-15T20:00:00.000Z",
  "channel_id": "pair-123456"
}
```

**Important Notes**:
- Code expires after **5 minutes**
- `channel_id` format: `pair-{code}`
- `desktop_session_id` should be unique per browser session

### Step 2: Mobile Validates Pairing Code

```http
POST /api/pair-device
Content-Type: application/json

{
  "code": "123456",
  "mobile_session_id": "unique-mobile-session-id"
}
```

**Success Response**:
```json
{
  "success": true,
  "channel_id": "pair-123456",
  "message": "Device paired successfully"
}
```

**Error Response**:
```json
{
  "success": false,
  "error": "INVALID_CODE",
  "message": "Pairing code does not exist or has expired"
}
```

### Step 3: WebSocket Connection & Channel Communication

After successful pairing, both devices connect to WebSocket and join the channel.

## 🔌 WebSocket Protocol

### Connection
```javascript
const ws = new WebSocket('ws://localhost:8089/ws');
```

### Initial Messages

**1. Desktop Identifies**:
```javascript
ws.send(JSON.stringify({
  type: "identify",
  device_type: "desktop"
}));
```

**2. Desktop Joins Channel**:
```javascript
ws.send(JSON.stringify({
  type: "join_channel",
  channel: "pair-123456", // from pairing response
  device_type: "desktop"
}));
```

**3. Mobile Joins Channel**:
```javascript
ws.send(JSON.stringify({
  type: "mobile_init",
  device_type: "mobile",
  pairing_code: "123456"
}));
```

### Server Responses

**Connection Established**:
```json
{
  "type": "connected",
  "client_id": "client_12345"
}
```

**Channel Joined**:
```json
{
  "type": "channel_joined",
  "channel": "pair-123456"
}
```

**Device Joined Channel**:
```json
{
  "type": "client_joined",
  "client_id": "client_67890",
  "device_type": "mobile"
}
```

**Pairing Success** (sent to both devices):
```json
{
  "type": "pairing_success",
  "message": "Mobile and desktop paired successfully"
}
```

## 🎤 Audio Streaming Protocol

### Audio Data Message
```javascript
ws.send(JSON.stringify({
  type: "audio_chunk",
  channelId: "pair-123456",
  data: "base64-encoded-audio-data",
  sequence: 1,
  timestamp: Date.now()
}));
```

**Alternative formats**:
- `type: "audio_data"`
- `type: "audio_stream"`

### Settings Sync
```javascript
ws.send(JSON.stringify({
  type: "settings_sync",
  channelId: "pair-123456",
  settings: {
    language: "nl",
    quality: "high"
  }
}));
```

### Generic Channel Messages
```javascript
ws.send(JSON.stringify({
  type: "channel_message",
  channelId: "pair-123456",
  payload: {
    // Any custom data
  }
}));
```

## ⚡ Complete Pairing Implementation

### Desktop Implementation

```javascript
class DesktopPairingManager {
  constructor() {
    this.ws = null;
    this.channelId = null;
    this.sessionId = `desktop-${Date.now()}-${Math.random()}`;
  }

  async generatePairingCode() {
    const response = await fetch('/api/generate-pair-code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include', // Important for cookies
      body: JSON.stringify({
        desktop_session_id: this.sessionId
      })
    });

    const data = await response.json();
    this.channelId = data.channel_id;

    // Start WebSocket connection
    this.connectWebSocket();

    return data.code;
  }

  connectWebSocket() {
    this.ws = new WebSocket('ws://localhost:8089/ws');

    this.ws.onopen = () => {
      // Identify as desktop
      this.ws.send(JSON.stringify({
        type: "identify",
        device_type: "desktop"
      }));

      // Join pairing channel
      this.ws.send(JSON.stringify({
        type: "join_channel",
        channel: this.channelId,
        device_type: "desktop"
      }));
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };
  }

  handleMessage(message) {
    switch (message.type) {
      case 'pairing_success':
        console.log('✅ Mobile device paired successfully!');
        this.onPairingSuccess();
        break;

      case 'audio_chunk':
      case 'audio_data':
      case 'audio_stream':
        console.log('🎤 Received audio from mobile');
        this.handleAudioData(message);
        break;

      case 'mobile_disconnected':
        console.log('📱 Mobile device disconnected');
        this.onMobileDisconnected();
        break;
    }
  }

  onPairingSuccess() {
    // Update UI to show paired status
  }

  handleAudioData(message) {
    // Process audio data from mobile
    const audioData = message.data;
    // Send to transcription service
  }
}
```

### Mobile Implementation

```javascript
class MobilePairingManager {
  constructor() {
    this.ws = null;
    this.channelId = null;
    this.sessionId = `mobile-${Date.now()}-${Math.random()}`;
  }

  async pairWithCode(code) {
    // Validate pairing code
    const response = await fetch('/api/pair-device', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        code: code,
        mobile_session_id: this.sessionId
      })
    });

    const data = await response.json();

    if (data.success) {
      this.channelId = data.channel_id;
      this.connectWebSocket(code);
      return true;
    } else {
      throw new Error(data.message);
    }
  }

  connectWebSocket(pairingCode) {
    this.ws = new WebSocket('ws://localhost:8089/ws');

    this.ws.onopen = () => {
      // Mobile initialization with pairing code
      this.ws.send(JSON.stringify({
        type: "mobile_init",
        device_type: "mobile",
        pairing_code: pairingCode
      }));
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };
  }

  sendAudioChunk(audioData) {
    if (this.ws && this.channelId) {
      this.ws.send(JSON.stringify({
        type: "audio_chunk",
        channelId: this.channelId,
        data: audioData, // base64 encoded
        timestamp: Date.now()
      }));
    }
  }

  handleMessage(message) {
    switch (message.type) {
      case 'pairing_success':
        console.log('✅ Successfully paired with desktop!');
        this.onPairingSuccess();
        break;

      case 'desktop_disconnected':
        console.log('💻 Desktop disconnected');
        this.onDesktopDisconnected();
        break;
    }
  }
}
```

## 🚨 Critical Implementation Notes

### 1. Channel ID Synchronization
- **Desktop**: Gets `channel_id` from `/api/generate-pair-code` response
- **Mobile**: Gets `channel_id` from `/api/pair-device` response
- **Format**: Always `pair-{6-digit-code}`
- **Must Match**: Both devices must use exact same `channel_id` for WebSocket messages

### 2. Cookie Configuration
```javascript
// For fetch requests, always include:
fetch('/api/auth/login', {
  method: 'POST',
  credentials: 'include', // Required for httpOnly cookies
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(data)
});
```

### 3. WebSocket Message Routing
- Messages with `channelId` field are routed to all devices in that channel
- Audio messages are automatically forwarded between paired devices
- Unknown message types are forwarded to channel (extensible)

### 4. Connection Lifecycle
1. **Desktop**: Generate code → Connect WS → Join channel → Wait for mobile
2. **Mobile**: Validate code → Connect WS → Join channel → Pairing success
3. **Both**: Listen for disconnect events and handle gracefully

### 5. Error Handling
```javascript
// Rate limiting
{
  "type": "error",
  "message": "Rate limit exceeded. Retry after 2.1 seconds"
}

// Invalid pairing code
{
  "success": false,
  "error": "INVALID_CODE",
  "message": "Pairing code does not exist or has expired"
}
```

## 🔧 Testing & Debugging

### Test Endpoints
- **Desktop Test**: `http://localhost:8089/test-desktop.html`
- **Mobile Test**: `http://localhost:8089/test-mobile-local.html`
- **Complete API Test**: `http://localhost:8089/api-test`

### Common Issues
1. **CORS**: Ensure using correct Lovable domain
2. **Cookies**: Must use `credentials: 'include'`
3. **Channel ID**: Must match exactly between devices
4. **Timing**: Pairing code expires in 5 minutes
5. **WebSocket**: Connect after successful pairing validation

## 📊 Rate Limits
- **HTTP**: 30 requests per minute per IP
- **WebSocket**: 10 messages per second per connection
- **Pairing**: 5 attempts per 60 seconds per IP

---

✅ **Ready for Production**: All endpoints tested and working with httpOnly cookies
🔒 **Security**: CORS configured for Lovable domains
📱 **Mobile Ready**: Complete pairing flow with audio streaming support