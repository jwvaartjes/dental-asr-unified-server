/**
 * Complete Pairing Service Implementation
 * Ready-to-use service class for desktop-mobile pairing with Zustand support
 */

import {
  DeviceType,
  MessageType,
  WSMessage,
  PairingServiceConfig,
  PairingServiceInterface,
  GeneratePairCodeResponse,
  PairDeviceResponse,
  WebSocketTokenResponse,
  AudioSettings,
  AudioFormat,
  PairingError,
  PairingErrorCode,
  WebSocketError,
  PAIRING_CONSTANTS
} from './pairing-types';

export class PairingService implements PairingServiceInterface {
  private baseURL: string;
  private authToken?: string;
  private sessionId: string;
  private deviceType: DeviceType;

  private ws: WebSocket | null = null;
  private wsToken: string | null = null;
  private channelId: string | null = null;
  private isConnecting = false;
  private reconnectAttempts = 0;
  private pingInterval: NodeJS.Timeout | null = null;

  // Event handlers
  private onErrorHandler?: (error: Error) => void;
  private onConnectionChangeHandler?: (isConnected: boolean) => void;
  private onPairingChangeHandler?: (isPaired: boolean) => void;
  private onSettingsSyncHandler?: (settings: AudioSettings) => void;
  private messageHandlers: ((message: WSMessage) => void)[] = [];

  constructor(config: PairingServiceConfig) {
    this.baseURL = config.baseURL.replace(/\/$/, ''); // Remove trailing slash
    this.authToken = config.authToken;
    this.sessionId = config.sessionId;
    this.deviceType = config.deviceType;

    this.onErrorHandler = config.onError;
    this.onConnectionChangeHandler = config.onConnectionChange;
    this.onPairingChangeHandler = config.onPairingChange;
    this.onSettingsSyncHandler = config.onSettingsSync;
  }

  // ============================================================================
  // API Methods
  // ============================================================================

  async generatePairingCode(): Promise<GeneratePairCodeResponse> {
    const response = await fetch(`${this.baseURL}/api/generate-pair-code`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.authToken && { 'Authorization': `Bearer ${this.authToken}` })
      },
      body: JSON.stringify({
        desktop_session_id: this.sessionId
      })
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Network error' }));
      throw new PairingError(
        PairingErrorCode.INVALID_CODE,
        error.message || `HTTP ${response.status}`
      );
    }

    const data = await response.json();
    this.channelId = data.channel_id;
    return data;
  }

  async pairWithCode(code: string): Promise<PairDeviceResponse> {
    if (!/^\d{6}$/.test(code)) {
      throw new PairingError(
        PairingErrorCode.INVALID_CODE,
        'Pairing code must be 6 digits'
      );
    }

    const response = await fetch(`${this.baseURL}/api/pair-device`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.authToken && { 'Authorization': `Bearer ${this.authToken}` })
      },
      body: JSON.stringify({
        code,
        mobile_session_id: this.sessionId
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new PairingError(
        data.error || PairingErrorCode.INVALID_CODE,
        data.message || `HTTP ${response.status}`
      );
    }

    if (data.success) {
      this.channelId = data.channel_id;
    }

    return data;
  }

  async getWebSocketToken(): Promise<WebSocketTokenResponse> {
    const endpoint = this.deviceType === DeviceType.DESKTOP
      ? '/api/auth/ws-token'
      : '/api/auth/ws-token-mobile';

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.authToken && { 'Authorization': `Bearer ${this.authToken}` })
      },
      body: JSON.stringify({
        username: this.sessionId
      })
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Failed to get WebSocket token' }));
      throw new WebSocketError(error.message || `HTTP ${response.status}`);
    }

    const data = await response.json();
    this.wsToken = data.token;
    return data;
  }

  // ============================================================================
  // WebSocket Methods
  // ============================================================================

  async connect(): Promise<void> {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    if (this.isConnecting) {
      return; // Connection in progress
    }

    this.isConnecting = true;

    try {
      // Get WebSocket token if we don't have one
      if (!this.wsToken) {
        await this.getWebSocketToken();
      }

      // Create WebSocket connection
      const wsUrl = `${this.baseURL.replace('http', 'ws')}/ws?token=${this.wsToken}`;
      this.ws = new WebSocket(wsUrl);

      // Set up event handlers
      this.ws.onopen = this.handleWebSocketOpen.bind(this);
      this.ws.onmessage = this.handleWebSocketMessage.bind(this);
      this.ws.onclose = this.handleWebSocketClose.bind(this);
      this.ws.onerror = this.handleWebSocketError.bind(this);

      // Wait for connection to open
      await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new WebSocketError('Connection timeout'));
        }, PAIRING_CONSTANTS.WEBSOCKET_TIMEOUT);

        this.ws!.addEventListener('open', () => {
          clearTimeout(timeout);
          resolve(void 0);
        });

        this.ws!.addEventListener('error', () => {
          clearTimeout(timeout);
          reject(new WebSocketError('Failed to connect'));
        });
      });

    } catch (error) {
      this.isConnecting = false;
      throw error;
    }
  }

  disconnect(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.isConnecting = false;
    this.reconnectAttempts = 0;
    this.onConnectionChangeHandler?.(false);
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  // ============================================================================
  // Message Methods
  // ============================================================================

  sendMessage(message: WSMessage): void {
    if (!this.isConnected()) {
      throw new WebSocketError('WebSocket not connected');
    }

    try {
      this.ws!.send(JSON.stringify(message));
    } catch (error) {
      this.handleError(new WebSocketError('Failed to send message'));
    }
  }

  joinChannel(channelId: string): void {
    this.channelId = channelId;
    this.sendMessage({
      type: MessageType.JOIN_CHANNEL,
      channel: channelId,
      device_type: this.deviceType,
      session_id: this.sessionId
    });
  }

  syncSettings(settings: AudioSettings): void {
    if (!this.channelId) {
      throw new PairingError(PairingErrorCode.INVALID_CHANNEL, 'No channel joined');
    }

    this.sendMessage({
      type: MessageType.SETTINGS_SYNC,
      channelId: this.channelId,
      settings
    });
  }

  sendAudioChunk(audioData: string, format: AudioFormat = AudioFormat.WEBM): void {
    if (!this.channelId) {
      throw new PairingError(PairingErrorCode.INVALID_CHANNEL, 'No channel joined');
    }

    this.sendMessage({
      type: MessageType.AUDIO_CHUNK,
      chunk_id: `chunk-${Date.now()}`,
      data: audioData,
      format,
      sample_rate: 16000
    });
  }

  sendCustomMessage(action: string, stateType: string, data: any): void {
    if (!this.channelId) {
      throw new PairingError(PairingErrorCode.INVALID_CHANNEL, 'No channel joined');
    }

    this.sendMessage({
      type: MessageType.CHANNEL_MESSAGE,
      channelId: this.channelId,
      payload: {
        action,
        stateType,
        data
      }
    });
  }

  sendPing(): void {
    const sequence = Date.now();
    this.sendMessage({
      type: MessageType.PING,
      sequence
    });
  }

  // ============================================================================
  // Event Handlers
  // ============================================================================

  onMessage(handler: (message: WSMessage) => void): void {
    this.messageHandlers.push(handler);
  }

  onError(handler: (error: Error) => void): void {
    this.onErrorHandler = handler;
  }

  onConnectionChange(handler: (isConnected: boolean) => void): void {
    this.onConnectionChangeHandler = handler;
  }

  // ============================================================================
  // Private WebSocket Event Handlers
  // ============================================================================

  private handleWebSocketOpen(): void {
    this.isConnecting = false;
    this.reconnectAttempts = 0;

    // Send identification message
    this.sendMessage({
      type: MessageType.IDENTIFY,
      device_type: this.deviceType,
      session_id: this.sessionId,
      user_agent: navigator?.userAgent
    });

    // Join channel if we have one
    if (this.channelId) {
      this.joinChannel(this.channelId);
    }

    // Start ping interval
    this.pingInterval = setInterval(() => {
      if (this.isConnected()) {
        this.sendPing();
      }
    }, PAIRING_CONSTANTS.PING_INTERVAL);

    this.onConnectionChangeHandler?.(true);
  }

  private handleWebSocketMessage(event: MessageEvent): void {
    try {
      const message: WSMessage = JSON.parse(event.data);

      // Handle specific message types
      switch (message.type) {
        case MessageType.PAIRING_SUCCESS:
          this.onPairingChangeHandler?.(true);
          break;

        case MessageType.SETTINGS_SYNC:
          if ('settings' in message) {
            this.onSettingsSyncHandler?.(message.settings as AudioSettings);
          }
          break;

        case MessageType.CHANNEL_JOINED:
          // Channel joined successfully
          break;

        case MessageType.CLIENT_JOINED:
          // Another device joined the channel
          break;

        case MessageType.DESKTOP_DISCONNECTED:
        case MessageType.MOBILE_DISCONNECTED:
          this.onPairingChangeHandler?.(false);
          break;

        case MessageType.ERROR:
          if ('code' in message && 'message' in message) {
            this.handleError(new PairingError(
              message.code as PairingErrorCode,
              message.message,
              message.details
            ));
          }
          break;

        case MessageType.PONG:
          // Pong received, connection is alive
          break;
      }

      // Notify all message handlers
      this.messageHandlers.forEach(handler => {
        try {
          handler(message);
        } catch (error) {
          console.error('Error in message handler:', error);
        }
      });

    } catch (error) {
      this.handleError(new WebSocketError('Failed to parse message'));
    }
  }

  private handleWebSocketClose(event: CloseEvent): void {
    this.ws = null;
    this.isConnecting = false;

    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }

    this.onConnectionChangeHandler?.(false);

    // Attempt to reconnect if not a clean close
    if (!event.wasClean && this.reconnectAttempts < PAIRING_CONSTANTS.MAX_RECONNECT_ATTEMPTS) {
      this.reconnectAttempts++;
      setTimeout(() => {
        this.connect().catch(error => {
          this.handleError(new WebSocketError(`Reconnection failed: ${error.message}`));
        });
      }, PAIRING_CONSTANTS.RECONNECT_DELAY);
    }
  }

  private handleWebSocketError(event: Event): void {
    this.handleError(new WebSocketError('WebSocket connection error'));
  }

  private handleError(error: Error): void {
    console.error('PairingService error:', error);
    this.onErrorHandler?.(error);
  }
}

// ============================================================================
// Utility Functions
// ============================================================================

export function createSessionId(deviceType: DeviceType): string {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2);
  return `${deviceType}-${timestamp}-${random}`;
}

export function validatePairingCode(code: string): boolean {
  return /^\d{6}$/.test(code);
}

export function formatChannelId(code: string): string {
  return `${PAIRING_CONSTANTS.CHANNEL_PREFIX}${code}`;
}

export function extractCodeFromChannel(channelId: string): string {
  return channelId.replace(PAIRING_CONSTANTS.CHANNEL_PREFIX, '');
}

export function isChannelExpired(expiresAt: string): boolean {
  return new Date() > new Date(expiresAt);
}

// ============================================================================
// Error Handling Utilities
// ============================================================================

export function handlePairingError(error: any): PairingError {
  if (error instanceof PairingError) {
    return error;
  }

  if (error.name === 'WebSocketError') {
    return new PairingError(
      PairingErrorCode.INVALID_TOKEN,
      'WebSocket connection failed'
    );
  }

  // Network errors
  if (error.name === 'TypeError' && error.message.includes('fetch')) {
    return new PairingError(
      PairingErrorCode.RATE_LIMITED,
      'Network error - please check your connection'
    );
  }

  // Generic error
  return new PairingError(
    PairingErrorCode.INVALID_CODE,
    error.message || 'Unknown error occurred'
  );
}

export function getErrorMessage(error: PairingError): string {
  return error.message || 'An unexpected error occurred';
}

export function shouldRetryError(error: PairingError): boolean {
  const retryableCodes = [
    PairingErrorCode.RATE_LIMITED,
    PairingErrorCode.INVALID_TOKEN
  ];

  return retryableCodes.includes(error.code);
}

// ============================================================================
// Audio Utilities
// ============================================================================

export async function convertBlobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      // Remove data URL prefix (e.g., "data:audio/wav;base64,")
      const base64 = result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

export function validateAudioSettings(settings: Partial<AudioSettings>): boolean {
  if (settings.audioGain !== undefined) {
    if (settings.audioGain < 0 || settings.audioGain > 100) return false;
  }

  if (settings.chunkDuration !== undefined) {
    if (settings.chunkDuration < 0.5 || settings.chunkDuration > 30) return false;
  }

  if (settings.overlapPercent !== undefined) {
    if (settings.overlapPercent < 0 || settings.overlapPercent > 100) return false;
  }

  return true;
}

export function mergeAudioSettings(
  current: AudioSettings,
  updates: Partial<AudioSettings>
): AudioSettings {
  const merged = { ...current, ...updates };

  if (!validateAudioSettings(merged)) {
    throw new Error('Invalid audio settings provided');
  }

  return merged;
}