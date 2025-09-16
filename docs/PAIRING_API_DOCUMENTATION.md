# 🔗 Device Pairing & WebSocket API Documentation

**Complete guide for implementing desktop-mobile device pairing with real-time communication**

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Authentication Flow](#authentication-flow)
- [Pairing Process](#pairing-process)
- [WebSocket API](#websocket-api)
- [Channel Management](#channel-management)
- [Message Types](#message-types)
- [State Management (Zustand)](#state-management-zustand)
- [Error Handling](#error-handling)
- [Security](#security)
- [Implementation Examples](#implementation-examples)

---

## 🎯 Overview

The pairing system enables secure real-time communication between desktop and mobile devices. It uses:

- **6-digit pairing codes** for device authentication
- **WebSocket channels** for real-time communication
- **JWT tokens** for WebSocket connection authentication
- **Channel-based messaging** to prevent cross-device interference
- **State synchronization** between devices (perfect for Zustand)

### Key Features

- ✅ **Secure Pairing**: 6-digit codes with expiration (5 minutes)
- ✅ **Real-time Communication**: WebSocket-based messaging
- ✅ **Channel Isolation**: Each pair gets its own communication channel
- ✅ **State Sync**: Zustand state can be synchronized between devices
- ✅ **Audio Streaming**: Support for real-time audio chunks
- ✅ **Auto-cleanup**: Automatic disconnection handling
- ✅ **Rate Limiting**: Built-in protection against abuse

---

## 🏗️ Architecture

```
[Desktop App] ←→ [Pairing Server] ←→ [Mobile App]
      ↓                ↓                ↓
  JWT Token    WebSocket Channel    JWT Token
      ↓                ↓                ↓
  Session ID    pair-XXXXXX       Session ID
```

### Flow Overview:
1. **Desktop** generates pairing code via API
2. **Mobile** enters code to join the same WebSocket channel
3. Both devices communicate via channel-specific messages
4. **Zustand state** can be synchronized between devices
5. Automatic cleanup on disconnect

---

## 🔐 Authentication Flow

### Step 1: Get WebSocket Token

Both desktop and mobile need WebSocket tokens before connecting.

#### Desktop WebSocket Token
```http
POST /api/auth/ws-token
Content-Type: application/json
Authorization: Bearer <your-jwt-token>

{
  "username": "optional"
}
```

#### Mobile WebSocket Token
```http
POST /api/auth/ws-token-mobile
Content-Type: application/json
Authorization: Bearer <your-jwt-token>

{
  "username": "optional"
}
```

**Response:**
```json
{
  "token": "ws-jwt-token-here",
  "expires_in": 3600
}
```

### Step 2: Use Token in WebSocket Connection

```javascript
const ws = new WebSocket(`ws://localhost:8089/ws?token=${wsToken}`);
```

---

## 📱 Pairing Process

### Step 1: Desktop Generates Code

```http
POST /api/generate-pair-code
Content-Type: application/json

{
  "desktop_session_id": "desktop-session-unique-id"
}
```

**Response:**
```json
{
  "code": "123456",
  "expires_at": "2025-09-14T22:45:00Z",
  "channel_id": "pair-123456"
}
```

### Step 2: Mobile Pairs with Code

```http
POST /api/pair-device
Content-Type: application/json

{
  "code": "123456",
  "mobile_session_id": "mobile-session-unique-id"
}
```

**Response:**
```json
{
  "success": true,
  "channel_id": "pair-123456",
  "message": "Device paired successfully"
}
```

### Step 3: Both Devices Join WebSocket Channel

Both desktop and mobile connect to WebSocket and join the same channel.

---

## 🔌 WebSocket API

### Connection URL
```
ws://localhost:8089/ws?token=<ws-jwt-token>
```

### Connection Flow

1. **Connect to WebSocket**
2. **Identify Device** (desktop/mobile)
3. **Join Channel** using pairing code
4. **Start Communication** via channel messages

---

## 📢 Channel Management

### Channel Naming Convention
- Format: `pair-XXXXXX` (where XXXXXX is the 6-digit code)
- Example: `pair-123456`

### Channel Lifecycle
1. **Created**: When desktop generates code
2. **Active**: When both desktop and mobile join
3. **Cleanup**: Auto-deleted after 5 minutes or on disconnect

### Channel Isolation
- Each pairing gets its own channel
- Messages only sent to devices in the same channel
- No cross-channel communication possible

---

## 💬 Message Types

### 1. Device Identification

#### Desktop Identify
```json
{
  "type": "identify",
  "device_type": "desktop",
  "session_id": "desktop-session-123",
  "user_agent": "MyDesktopApp/1.0"
}
```

#### Mobile Identify
```json
{
  "type": "identify",
  "device_type": "mobile",
  "session_id": "mobile-session-456",
  "user_agent": "MyMobileApp/1.0"
}
```

### 2. Channel Operations

#### Join Channel
```json
{
  "type": "join_channel",
  "channel": "pair-123456",
  "device_type": "desktop|mobile",
  "session_id": "your-session-id"
}
```

#### Channel Message (for Zustand sync)
```json
{
  "type": "channel_message",
  "channelId": "pair-123456",
  "payload": {
    "action": "STATE_UPDATE",
    "stateType": "audioSettings",
    "data": {
      "audioGain": 75,
      "autoGainEnabled": true,
      "vadEnabled": false
    }
  }
}
```

### 3. Audio Streaming

#### Audio Chunk
```json
{
  "type": "audio_chunk",
  "chunk_id": "chunk-001",
  "data": "base64-encoded-audio-data",
  "format": "webm",
  "sample_rate": 16000
}
```

### 4. Settings Synchronization

#### Settings Sync (Perfect for Zustand)
```json
{
  "type": "settings_sync",
  "channelId": "pair-123456",
  "settings": {
    "audioGain": 75,
    "autoGainEnabled": true,
    "chunkDuration": 3.0,
    "overlapPercent": 15,
    "paragraphBreakDuration": 2.0,
    "language": "nl",
    "model": "whisper-1",
    "vadEnabled": false
  }
}
```

### 5. Connection Events

#### Pairing Success
```json
{
  "type": "pairing_success",
  "code": "123456",
  "message": "Devices paired successfully"
}
```

#### Client Joined
```json
{
  "type": "client_joined",
  "client_id": "mobile-session-456",
  "device_type": "mobile"
}
```

#### Device Disconnected
```json
{
  "type": "desktop_disconnected",
  "reason": "Connection closed",
  "force_disconnect": false
}
```

### 6. Keep-Alive

#### Ping/Pong
```json
{
  "type": "ping",
  "sequence": 1
}
```

```json
{
  "type": "pong",
  "sequence": 1
}
```

### 7. Error Messages

```json
{
  "type": "error",
  "code": "INVALID_CHANNEL",
  "message": "Channel does not exist or has expired",
  "details": {
    "channel": "pair-123456"
  }
}
```

---

## 🗄️ State Management (Zustand)

### Perfect Integration with Zustand

The WebSocket channel system works perfectly with Zustand for state synchronization:

#### Zustand Store Example

```typescript
import { create } from 'zustand';

interface PairingState {
  // Connection state
  isConnected: boolean;
  isPaired: boolean;
  channelId: string | null;
  deviceType: 'desktop' | 'mobile';

  // Audio settings (synced between devices)
  audioSettings: {
    audioGain: number;
    autoGainEnabled: boolean;
    vadEnabled: boolean;
    chunkDuration: number;
    overlapPercent: number;
  };

  // Actions
  connectWebSocket: () => void;
  joinChannel: (channelId: string) => void;
  updateAudioSettings: (settings: Partial<AudioSettings>) => void;
  syncStateToChannel: () => void;
}

const usePairingStore = create<PairingState>((set, get) => ({
  // Initial state
  isConnected: false,
  isPaired: false,
  channelId: null,
  deviceType: 'desktop',
  audioSettings: {
    audioGain: 50,
    autoGainEnabled: true,
    vadEnabled: false,
    chunkDuration: 3.0,
    overlapPercent: 15,
  },

  // Actions
  connectWebSocket: () => {
    // WebSocket connection logic
  },

  joinChannel: (channelId: string) => {
    set({ channelId, isPaired: true });
  },

  updateAudioSettings: (newSettings) => {
    const currentSettings = get().audioSettings;
    const updatedSettings = { ...currentSettings, ...newSettings };

    set({ audioSettings: updatedSettings });

    // Sync to other device
    get().syncStateToChannel();
  },

  syncStateToChannel: () => {
    const { channelId, audioSettings } = get();
    if (!channelId) return;

    // Send settings sync message
    webSocket.send(JSON.stringify({
      type: 'settings_sync',
      channelId,
      settings: audioSettings
    }));
  }
}));
```

#### Receiving State Updates

```typescript
// WebSocket message handler
const handleWebSocketMessage = (event: MessageEvent) => {
  const message = JSON.parse(event.data);

  switch (message.type) {
    case 'settings_sync':
      // Update Zustand store with synced settings
      usePairingStore.getState().updateAudioSettings(message.settings);
      break;

    case 'channel_message':
      // Handle custom state updates
      if (message.payload.action === 'STATE_UPDATE') {
        const { stateType, data } = message.payload;

        if (stateType === 'audioSettings') {
          usePairingStore.getState().updateAudioSettings(data);
        }
      }
      break;

    case 'pairing_success':
      usePairingStore.getState().joinChannel(message.channelId);
      break;
  }
};
```

### State Synchronization Patterns

#### 1. Immediate Sync (Real-time)
Perfect for audio controls, UI state:
```typescript
const setAudioGain = (gain: number) => {
  // Update local state
  usePairingStore.getState().updateAudioSettings({ audioGain: gain });
  // State is automatically synced to other device
};
```

#### 2. Batch Sync
For multiple settings:
```typescript
const applyPreset = (preset: AudioPreset) => {
  // Update multiple settings at once
  usePairingStore.getState().updateAudioSettings({
    audioGain: preset.gain,
    vadEnabled: preset.vad,
    chunkDuration: preset.chunkSize
  });
  // Single sync message sent
};
```

#### 3. Selective Sync
Only sync specific state portions:
```typescript
const syncOnlyAudioSettings = () => {
  const { channelId, audioSettings } = usePairingStore.getState();

  webSocket.send(JSON.stringify({
    type: 'channel_message',
    channelId,
    payload: {
      action: 'AUDIO_SETTINGS_UPDATE',
      data: audioSettings
    }
  }));
};
```

---

## ❌ Error Handling

### Common Error Codes

| Code | Description | Action |
|------|-------------|---------|
| `INVALID_TOKEN` | WebSocket token expired | Refresh token |
| `INVALID_CHANNEL` | Channel doesn't exist | Regenerate pairing code |
| `CHANNEL_FULL` | Too many devices in channel | Try new pairing |
| `RATE_LIMITED` | Too many messages | Slow down requests |
| `PAYLOAD_TOO_LARGE` | Message exceeds size limit | Reduce payload size |

### Error Response Format

```json
{
  "type": "error",
  "code": "CHANNEL_FULL",
  "message": "Maximum number of devices already connected to channel",
  "details": {
    "channel": "pair-123456",
    "max_devices": 2,
    "current_devices": 2
  }
}
```

### Error Handling in Code

```typescript
const handleError = (error: ErrorMessage) => {
  switch (error.code) {
    case 'INVALID_TOKEN':
      // Refresh WebSocket token
      await refreshWebSocketToken();
      reconnectWebSocket();
      break;

    case 'INVALID_CHANNEL':
      // Channel expired, need new pairing
      usePairingStore.getState().resetPairing();
      showPairingDialog();
      break;

    case 'RATE_LIMITED':
      // Implement backoff strategy
      await delay(5000);
      break;

    default:
      console.error('WebSocket error:', error.message);
      showErrorNotification(error.message);
  }
};
```

---

## 🛡️ Security

### Security Features

1. **JWT Authentication**: All WebSocket connections require valid JWT tokens
2. **Channel Isolation**: Devices can only communicate within their paired channel
3. **Rate Limiting**: Built-in protection against message flooding
4. **Input Validation**: All messages validated against Pydantic schemas
5. **Size Limits**: Maximum message sizes enforced
6. **Origin Validation**: CORS protection for web clients
7. **Auto Expiration**: Pairing codes expire after 5 minutes

### Security Best Practices

1. **Always validate incoming messages**
2. **Implement reconnection with backoff**
3. **Handle token expiration gracefully**
4. **Sanitize user input before sending**
5. **Use HTTPS/WSS in production**
6. **Implement client-side timeouts**

---

## 💡 Implementation Examples

### Complete Desktop Implementation

```typescript
class PairingService {
  private ws: WebSocket | null = null;
  private channelId: string | null = null;

  // Generate pairing code
  async generatePairingCode(): Promise<string> {
    const response = await fetch('/api/generate-pair-code', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.authToken}`
      },
      body: JSON.stringify({
        desktop_session_id: this.sessionId
      })
    });

    const data = await response.json();
    this.channelId = data.channel_id;
    return data.code;
  }

  // Connect to WebSocket
  async connectWebSocket() {
    const wsToken = await this.getWebSocketToken();
    this.ws = new WebSocket(`ws://localhost:8089/ws?token=${wsToken}`);

    this.ws.onopen = () => {
      // Identify as desktop
      this.send({
        type: 'identify',
        device_type: 'desktop',
        session_id: this.sessionId
      });

      // Join channel
      if (this.channelId) {
        this.send({
          type: 'join_channel',
          channel: this.channelId,
          device_type: 'desktop',
          session_id: this.sessionId
        });
      }
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };
  }

  // Handle incoming messages
  private handleMessage(message: any) {
    switch (message.type) {
      case 'pairing_success':
        this.onPairingSuccess();
        break;

      case 'settings_sync':
        // Update Zustand store
        usePairingStore.getState().updateSettings(message.settings);
        break;

      case 'channel_message':
        // Handle custom messages
        this.handleChannelMessage(message.payload);
        break;

      case 'mobile_disconnected':
        this.onMobileDisconnected();
        break;
    }
  }

  // Sync Zustand state to mobile
  syncState(stateType: string, data: any) {
    if (!this.channelId) return;

    this.send({
      type: 'channel_message',
      channelId: this.channelId,
      payload: {
        action: 'STATE_UPDATE',
        stateType,
        data
      }
    });
  }

  private send(message: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }
}
```

### Complete Mobile Implementation

```typescript
class MobilePairingService {
  private ws: WebSocket | null = null;
  private channelId: string | null = null;

  // Pair with desktop using code
  async pairWithDesktop(code: string): Promise<boolean> {
    try {
      const response = await fetch('/api/pair-device', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.authToken}`
        },
        body: JSON.stringify({
          code,
          mobile_session_id: this.sessionId
        })
      });

      const data = await response.json();

      if (data.success) {
        this.channelId = data.channel_id;
        await this.connectWebSocket();
        return true;
      }

      return false;
    } catch (error) {
      console.error('Pairing failed:', error);
      return false;
    }
  }

  // Connect to WebSocket after successful pairing
  private async connectWebSocket() {
    const wsToken = await this.getWebSocketToken();
    this.ws = new WebSocket(`ws://localhost:8089/ws?token=${wsToken}`);

    this.ws.onopen = () => {
      // Identify as mobile
      this.send({
        type: 'identify',
        device_type: 'mobile',
        session_id: this.sessionId
      });

      // Join the paired channel
      if (this.channelId) {
        this.send({
          type: 'join_channel',
          channel: this.channelId,
          device_type: 'mobile',
          session_id: this.sessionId
        });
      }
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };
  }

  // Send audio data to desktop
  sendAudioChunk(audioData: string, format: string = 'webm') {
    if (!this.channelId) return;

    this.send({
      type: 'audio_chunk',
      chunk_id: `chunk-${Date.now()}`,
      data: audioData,
      format,
      sample_rate: 16000
    });
  }

  // Sync settings changes to desktop
  syncSettings(settings: AudioSettings) {
    if (!this.channelId) return;

    this.send({
      type: 'settings_sync',
      channelId: this.channelId,
      settings
    });
  }
}
```

### React Hook for Pairing

```typescript
const usePairing = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [isPaired, setIsPaired] = useState(false);
  const [pairingCode, setPairingCode] = useState<string | null>(null);

  const pairingService = useMemo(() => new PairingService(), []);

  const generateCode = async () => {
    try {
      const code = await pairingService.generatePairingCode();
      setPairingCode(code);
      await pairingService.connectWebSocket();
      setIsConnected(true);
    } catch (error) {
      console.error('Failed to generate pairing code:', error);
    }
  };

  const pairWithCode = async (code: string) => {
    try {
      const success = await pairingService.pairWithDesktop(code);
      if (success) {
        setIsPaired(true);
        setIsConnected(true);
      }
      return success;
    } catch (error) {
      console.error('Pairing failed:', error);
      return false;
    }
  };

  const syncZustandState = (stateType: string, data: any) => {
    pairingService.syncState(stateType, data);
  };

  return {
    isConnected,
    isPaired,
    pairingCode,
    generateCode,
    pairWithCode,
    syncZustandState
  };
};
```

---

## 🚀 Quick Start Checklist

### For Desktop App:
- [ ] Implement authentication to get JWT token
- [ ] Get WebSocket token via `/api/auth/ws-token`
- [ ] Generate pairing code via `/api/generate-pair-code`
- [ ] Connect to WebSocket with token
- [ ] Send `identify` and `join_channel` messages
- [ ] Handle incoming `settings_sync` and `channel_message` events
- [ ] Implement Zustand state synchronization

### For Mobile App:
- [ ] Implement authentication to get JWT token
- [ ] Get WebSocket token via `/api/auth/ws-token-mobile`
- [ ] Pair with desktop via `/api/pair-device`
- [ ] Connect to WebSocket with token
- [ ] Send `identify` and `join_channel` messages
- [ ] Send audio chunks via `audio_chunk` messages
- [ ] Sync settings via `settings_sync` messages
- [ ] Handle state updates from desktop

### For State Management:
- [ ] Set up Zustand store with pairing state
- [ ] Implement state synchronization methods
- [ ] Handle incoming state updates from WebSocket
- [ ] Add error handling and reconnection logic
- [ ] Test bidirectional state sync between devices

---

**Perfect for Zustand! 🎯** This WebSocket channel system provides exactly what you need for real-time state synchronization between your desktop and mobile applications. The channel isolation ensures your devices stay perfectly in sync without interference from other paired devices.