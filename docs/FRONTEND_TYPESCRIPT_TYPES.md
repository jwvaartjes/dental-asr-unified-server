# Frontend TypeScript Types for Pairing System

## Overview

This document provides TypeScript type definitions needed for the frontend pairing system integration.

## 🔧 Core Types

Create these types in your frontend project (e.g., `src/types/pairing.ts`):

```typescript
// Authentication Types
export interface AuthToken {
  token: string;
  expires_in: number;
  inherited_from?: string;
  pairing_code?: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
  inheritedFrom: string | null;
  isInherited: boolean;
  loading: boolean;
  error: string | null;
}

// Pairing Types
export interface PairingCode {
  code: string;
  expires_at: string;
  channel_id: string;
}

export interface PairingValidation {
  success: boolean;
  channel_id?: string;
  message: string;
  error?: string;
}

export interface PairingState {
  code: string | null;
  channelId: string | null;
  isGenerating: boolean;
  isValidating: boolean;
  expiresAt: string | null;
  error: string | null;
}

// WebSocket Types
export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export interface WebSocketState {
  isConnected: boolean;
  error: string | null;
  messages: WebSocketMessage[];
}

// Device Types
export type DeviceType = 'desktop' | 'mobile';

export interface DeviceInfo {
  device_type: DeviceType;
  session_id: string;
  channel?: string;
}

// API Request/Response Types
export interface LoginRequest {
  email: string;
  password?: string;
}

export interface MagicLoginRequest {
  email: string;
}

export interface TokenRequest {
  username: string;
}

export interface MobileTokenRequest {
  pair_code: string;
  username: string;
}

export interface PairCodeRequest {
  desktop_session_id: string;
}

export interface PairDeviceRequest {
  code: string;
  mobile_session_id: string;
}

// WebSocket Message Types
export interface IdentifyMessage {
  type: 'identify';
  device_type: DeviceType;
  session_id: string;
}

export interface JoinChannelMessage {
  type: 'join_channel';
  channel: string;
  session_id: string;
}

export interface ChannelMessage {
  type: 'channel_message';
  channel: string;
  message: any;
  timestamp: string;
}

export interface ClientJoinedMessage {
  type: 'client_joined';
  client_id: string;
  device_type: DeviceType;
}

export interface PairingSuccessMessage {
  type: 'pairing_success';
  message: string;
}

export interface DisconnectedMessage {
  type: 'desktop_disconnected' | 'mobile_disconnected';
  session_id: string;
  channel: string;
  reason: string;
  force_disconnect: boolean;
}

// Combined WebSocket Message Union
export type WebSocketMessageType =
  | IdentifyMessage
  | JoinChannelMessage
  | ChannelMessage
  | ClientJoinedMessage
  | PairingSuccessMessage
  | DisconnectedMessage;

// Hook Return Types
export interface UsePairingReturn {
  // State
  code: string | null;
  channelId: string | null;
  isGenerating: boolean;
  expiresAt: string | null;
  error: string | null;

  // Actions
  generateCode: () => Promise<PairingCode>;
  validateCode: (code: string, mobileSessionId: string) => Promise<PairingValidation>;
  clearError: () => void;
}

export interface UseAuthReturn extends AuthState {
  // Actions
  login: (credentials: LoginRequest) => Promise<AuthToken>;
  loginMagic: (email: string) => Promise<AuthToken>;
  getDesktopToken: (username: string) => Promise<AuthToken>;
  getMobileToken: (pairCode: string, fallbackUsername: string) => Promise<AuthToken>;
  logout: () => void;
  restoreAuth: () => void;
}

export interface UseWebSocketReturn extends WebSocketState {
  // Actions
  connect: () => void;
  disconnect: () => void;
  sendMessage: (message: WebSocketMessageType) => void;

  // Handlers
  onMessage: (handler: (message: WebSocketMessage) => void) => void;
  onConnect: (handler: () => void) => void;
  onDisconnect: (handler: (reason?: string) => void) => void;
}

// Environment Configuration
export interface AppConfig {
  apiUrl: string;
  wsUrl: string;
  isDevelopment: boolean;
}

// Error Types
export interface ApiError {
  message: string;
  status: number;
  details?: string;
}

export interface ValidationError extends ApiError {
  field?: string;
}

// Store/Context Types (for Zustand or Context API)
export interface AppStore {
  // Auth
  auth: AuthState;

  // Pairing
  pairing: PairingState;

  // WebSocket
  websocket: WebSocketState;

  // Actions
  actions: {
    auth: {
      login: (credentials: LoginRequest) => Promise<void>;
      logout: () => void;
      restoreAuth: () => void;
    };
    pairing: {
      generateCode: () => Promise<void>;
      validateCode: (code: string) => Promise<void>;
    };
    websocket: {
      connect: () => void;
      disconnect: () => void;
      sendMessage: (message: WebSocketMessageType) => void;
    };
  };
}
```

## 🎯 Usage Examples

### Authentication Hook

```typescript
// hooks/useAuth.ts
import { UseAuthReturn, AuthToken, LoginRequest } from '../types/pairing';

export const useAuth = (): UseAuthReturn => {
  // Implementation using the types above
};
```

### Pairing Hook

```typescript
// hooks/usePairing.ts
import { UsePairingReturn, PairingCode } from '../types/pairing';

export const usePairing = (): UsePairingReturn => {
  // Implementation using the types above
};
```

### WebSocket Hook

```typescript
// hooks/useWebSocket.ts
import { UseWebSocketReturn, WebSocketMessageType } from '../types/pairing';

export const useWebSocket = (token: string | null): UseWebSocketReturn => {
  // Implementation using the types above
};
```

## 🚫 Common Mistakes to Avoid

### ❌ Don't Look for Backend Types
```typescript
// DON'T DO THIS - PairingStore is a Python backend class
import { PairingStore } from './websocket-types';
```

### ✅ Use Frontend-Specific Types
```typescript
// DO THIS - Use frontend state management types
import { PairingState, UsePairingReturn } from './types/pairing';
```

### ❌ Don't Import Backend Interfaces
```typescript
// DON'T DO THIS - Backend interfaces don't exist in frontend
interface PairingStore extends PairingState { }
```

### ✅ Define Your Own State Types
```typescript
// DO THIS - Define frontend-specific state interfaces
interface PairingState {
  code: string | null;
  channelId: string | null;
  isGenerating: boolean;
  error: string | null;
}
```

## 🔄 API Integration

When calling the backend APIs, use these request/response types:

```typescript
// API calls with proper typing
const generatePairCode = async (): Promise<PairingCode> => {
  const response = await fetch(`${apiUrl}/api/generate-pair-code`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      desktop_session_id: sessionId
    } as PairCodeRequest)
  });

  if (!response.ok) {
    throw new Error(`Failed to generate pairing code: ${response.status}`);
  }

  return response.json() as Promise<PairingCode>;
};
```

## 🎯 Key Points

1. **`PairingStore` is a backend Python class** - don't look for it in frontend types
2. **Use `PairingState`** for frontend state management
3. **WebSocket messages** have specific type unions for type safety
4. **API requests/responses** have dedicated interfaces
5. **Hook return types** provide consistent interfaces across components

This type system ensures type safety throughout your frontend pairing implementation while avoiding confusion with backend class names.