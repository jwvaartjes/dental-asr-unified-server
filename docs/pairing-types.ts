/**
 * TypeScript interfaces for Device Pairing & WebSocket API
 * Complete type definitions for desktop-mobile pairing with Zustand support
 */

// ============================================================================
// Enums
// ============================================================================

export enum DeviceType {
  DESKTOP = 'desktop',
  MOBILE = 'mobile'
}

export enum MessageType {
  // Connection & Identification
  IDENTIFY = 'identify',
  MOBILE_INIT = 'mobile_init',
  CONNECTED = 'connected',
  IDENTIFIED = 'identified',

  // Channel Operations
  JOIN_CHANNEL = 'join_channel',
  CHANNEL_JOINED = 'channel_joined',
  CHANNEL_MESSAGE = 'channel_message',

  // Settings & State Sync (Perfect for Zustand!)
  SETTINGS_SYNC = 'settings_sync',

  // Audio Streaming
  AUDIO_CHUNK = 'audio_chunk',
  AUDIO_DATA = 'audio_data',
  AUDIO_STREAM = 'audio_stream',

  // Connection Events
  PAIRING_SUCCESS = 'pairing_success',
  CLIENT_JOINED = 'client_joined',
  DESKTOP_DISCONNECTED = 'desktop_disconnected',
  MOBILE_DISCONNECTED = 'mobile_disconnected',

  // Keep-Alive
  PING = 'ping',
  PONG = 'pong',

  // Error Handling
  ERROR = 'error'
}

export enum PairingErrorCode {
  INVALID_CODE = 'INVALID_CODE',
  CODE_NOT_FOUND = 'CODE_NOT_FOUND',
  CODE_EXPIRED = 'CODE_EXPIRED',
  INVALID_TOKEN = 'INVALID_TOKEN',
  INVALID_CHANNEL = 'INVALID_CHANNEL',
  CHANNEL_FULL = 'CHANNEL_FULL',
  RATE_LIMITED = 'RATE_LIMITED',
  PAYLOAD_TOO_LARGE = 'PAYLOAD_TOO_LARGE'
}

export enum AudioFormat {
  WAV = 'wav',
  MP3 = 'mp3',
  WEBM = 'webm',
  OPUS = 'opus'
}

// ============================================================================
// API Request/Response Types
// ============================================================================

export interface GeneratePairCodeRequest {
  desktop_session_id: string;
}

export interface GeneratePairCodeResponse {
  code: string;
  expires_at: string; // ISO datetime
  channel_id: string; // "pair-XXXXXX"
}

export interface PairDeviceRequest {
  code: string;
  mobile_session_id: string;
}

export interface PairDeviceResponse {
  success: boolean;
  channel_id: string; // "pair-XXXXXX"
  message: string;
  error?: PairingErrorCode;
}

export interface WebSocketTokenRequest {
  username?: string;
}

export interface WebSocketTokenResponse {
  token: string;
  expires_in: number; // seconds
}

// ============================================================================
// WebSocket Message Types
// ============================================================================

export interface BaseWSMessage {
  type: MessageType;
  timestamp?: string;
}

export interface IdentifyMessage extends BaseWSMessage {
  type: MessageType.IDENTIFY;
  device_type: DeviceType;
  session_id: string;
  user_agent?: string;
}

export interface MobileInitMessage extends BaseWSMessage {
  type: MessageType.MOBILE_INIT;
  device_type: DeviceType.MOBILE;
  pairing_code: string; // 6-digit code
  session_id: string;
}

export interface JoinChannelMessage extends BaseWSMessage {
  type: MessageType.JOIN_CHANNEL;
  channel: string; // "pair-XXXXXX"
  device_type: DeviceType;
  session_id: string;
}

export interface ChannelMessage extends BaseWSMessage {
  type: MessageType.CHANNEL_MESSAGE;
  channelId: string; // "pair-XXXXXX"
  payload: {
    action: string;
    stateType?: string;
    data: any;
  };
}

// Perfect for Zustand State Synchronization!
export interface SettingsSyncMessage extends BaseWSMessage {
  type: MessageType.SETTINGS_SYNC;
  channelId: string; // "pair-XXXXXX"
  settings: AudioSettings;
}

export interface AudioChunkMessage extends BaseWSMessage {
  type: MessageType.AUDIO_CHUNK | MessageType.AUDIO_DATA | MessageType.AUDIO_STREAM;
  chunk_id?: string;
  data: string; // Base64 encoded
  format?: AudioFormat;
  sample_rate?: number;
}

export interface PairingSuccessMessage extends BaseWSMessage {
  type: MessageType.PAIRING_SUCCESS;
  code?: string;
  message: string;
}

export interface ClientJoinedMessage extends BaseWSMessage {
  type: MessageType.CLIENT_JOINED;
  client_id: string;
  device_type: DeviceType;
}

export interface DisconnectMessage extends BaseWSMessage {
  type: MessageType.DESKTOP_DISCONNECTED | MessageType.MOBILE_DISCONNECTED;
  reason?: string;
  force_disconnect?: boolean;
}

export interface PingMessage extends BaseWSMessage {
  type: MessageType.PING;
  sequence?: number;
}

export interface PongMessage extends BaseWSMessage {
  type: MessageType.PONG;
  sequence?: number;
}

export interface ErrorMessage extends BaseWSMessage {
  type: MessageType.ERROR;
  code?: PairingErrorCode;
  message: string;
  details?: any;
}

// Union type for all WebSocket messages
export type WSMessage =
  | IdentifyMessage
  | MobileInitMessage
  | JoinChannelMessage
  | ChannelMessage
  | SettingsSyncMessage
  | AudioChunkMessage
  | PairingSuccessMessage
  | ClientJoinedMessage
  | DisconnectMessage
  | PingMessage
  | PongMessage
  | ErrorMessage;

// ============================================================================
// Settings & State Types (Perfect for Zustand!)
// ============================================================================

export interface AudioSettings {
  audioGain: number; // 0-100
  autoGainEnabled: boolean;
  vadEnabled: boolean;
  chunkDuration: number; // seconds
  overlapPercent: number; // 0-100
  paragraphBreakDuration?: number; // seconds
  language?: string; // e.g., "nl"
  model?: string; // e.g., "whisper-1"
}

export interface PairingState {
  // Connection State
  isConnected: boolean;
  isPaired: boolean;
  isConnecting: boolean;
  connectionError: string | null;

  // Pairing Info
  pairingCode: string | null;
  channelId: string | null;
  deviceType: DeviceType;
  sessionId: string;

  // Other Device Info
  connectedDevices: ConnectedDevice[];

  // Synced Settings (shared between devices)
  audioSettings: AudioSettings;

  // WebSocket
  ws: WebSocket | null;
  wsToken: string | null;
  lastPingTime: number | null;
}

export interface ConnectedDevice {
  clientId: string;
  deviceType: DeviceType;
  connectedAt: Date;
}

// ============================================================================
// Zustand Store Interface
// ============================================================================

export interface PairingStore extends PairingState {
  // Connection Actions
  generatePairingCode: () => Promise<string>;
  pairWithCode: (code: string) => Promise<boolean>;
  connectWebSocket: () => Promise<void>;
  disconnect: () => void;

  // Settings Sync Actions
  updateAudioSettings: (settings: Partial<AudioSettings>) => void;
  syncSettingsToChannel: (settings?: AudioSettings) => void;

  // Audio Actions
  sendAudioChunk: (audioData: string, format?: AudioFormat) => void;

  // Channel Actions
  sendChannelMessage: (action: string, stateType: string, data: any) => void;
  joinChannel: (channelId: string) => void;

  // Internal Actions
  setConnectionState: (isConnected: boolean, error?: string | null) => void;
  setPairingState: (isPaired: boolean) => void;
  handleWebSocketMessage: (message: WSMessage) => void;
  sendPing: () => void;

  // Error Handling
  handleError: (error: ErrorMessage) => void;
  clearError: () => void;
}

// ============================================================================
// Hook Types
// ============================================================================

export interface UsePairingReturn {
  // State
  isConnected: boolean;
  isPaired: boolean;
  isConnecting: boolean;
  pairingCode: string | null;
  channelId: string | null;
  connectionError: string | null;
  connectedDevices: ConnectedDevice[];

  // Actions
  generateCode: () => Promise<string>;
  pairWithCode: (code: string) => Promise<boolean>;
  disconnect: () => void;
  syncAudioSettings: (settings: Partial<AudioSettings>) => void;
  sendAudioChunk: (audioData: string, format?: AudioFormat) => void;
  sendCustomMessage: (action: string, stateType: string, data: any) => void;
}

export interface UseAudioStreamingReturn {
  // Audio State
  isRecording: boolean;
  audioLevel: number;
  audioFormat: AudioFormat;

  // Settings
  audioSettings: AudioSettings;
  updateAudioSettings: (settings: Partial<AudioSettings>) => void;

  // Actions
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  sendAudioChunk: (chunk: Blob) => Promise<void>;
}

// ============================================================================
// Service Class Interfaces
// ============================================================================

export interface PairingServiceConfig {
  baseURL: string;
  authToken?: string;
  sessionId: string;
  deviceType: DeviceType;
  onError?: (error: Error) => void;
  onConnectionChange?: (isConnected: boolean) => void;
  onPairingChange?: (isPaired: boolean) => void;
  onSettingsSync?: (settings: AudioSettings) => void;
}

export interface PairingServiceInterface {
  // API Methods
  generatePairingCode(): Promise<GeneratePairCodeResponse>;
  pairWithCode(code: string): Promise<PairDeviceResponse>;
  getWebSocketToken(): Promise<WebSocketTokenResponse>;

  // WebSocket Methods
  connect(): Promise<void>;
  disconnect(): void;
  isConnected(): boolean;

  // Message Methods
  sendMessage(message: WSMessage): void;
  joinChannel(channelId: string): void;
  syncSettings(settings: AudioSettings): void;
  sendAudioChunk(audioData: string, format?: AudioFormat): void;
  sendCustomMessage(action: string, stateType: string, data: any): void;

  // Event Handlers
  onMessage(handler: (message: WSMessage) => void): void;
  onError(handler: (error: Error) => void): void;
  onConnectionChange(handler: (isConnected: boolean) => void): void;
}

// ============================================================================
// Utility Types
// ============================================================================

export interface PairingValidationResult {
  isValid: boolean;
  error?: PairingErrorCode;
  message?: string;
}

export interface AudioChunk {
  id: string;
  data: string; // Base64
  format: AudioFormat;
  timestamp: number;
  sampleRate?: number;
  duration?: number;
}

export interface ChannelInfo {
  channelId: string;
  code: string;
  createdAt: Date;
  expiresAt: Date;
  devices: ConnectedDevice[];
}

// ============================================================================
// Error Types
// ============================================================================

export class PairingError extends Error {
  constructor(
    public code: PairingErrorCode,
    message: string,
    public details?: any
  ) {
    super(message);
    this.name = 'PairingError';
  }
}

export class WebSocketError extends Error {
  constructor(
    message: string,
    public code?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'WebSocketError';
  }
}

// ============================================================================
// Type Guards
// ============================================================================

export function isPairingSuccessMessage(message: WSMessage): message is PairingSuccessMessage {
  return message.type === MessageType.PAIRING_SUCCESS;
}

export function isSettingsSyncMessage(message: WSMessage): message is SettingsSyncMessage {
  return message.type === MessageType.SETTINGS_SYNC;
}

export function isChannelMessage(message: WSMessage): message is ChannelMessage {
  return message.type === MessageType.CHANNEL_MESSAGE;
}

export function isAudioChunkMessage(message: WSMessage): message is AudioChunkMessage {
  return [MessageType.AUDIO_CHUNK, MessageType.AUDIO_DATA, MessageType.AUDIO_STREAM].includes(message.type as MessageType);
}

export function isErrorMessage(message: WSMessage): message is ErrorMessage {
  return message.type === MessageType.ERROR;
}

export function isClientJoinedMessage(message: WSMessage): message is ClientJoinedMessage {
  return message.type === MessageType.CLIENT_JOINED;
}

export function isDisconnectMessage(message: WSMessage): message is DisconnectMessage {
  return [MessageType.DESKTOP_DISCONNECTED, MessageType.MOBILE_DISCONNECTED].includes(message.type as MessageType);
}

// ============================================================================
// Constants
// ============================================================================

export const PAIRING_CONSTANTS = {
  CODE_LENGTH: 6,
  CODE_EXPIRY_MINUTES: 5,
  CHANNEL_PREFIX: 'pair-',
  WEBSOCKET_TIMEOUT: 30000, // 30 seconds
  PING_INTERVAL: 30000, // 30 seconds
  RECONNECT_DELAY: 5000, // 5 seconds
  MAX_RECONNECT_ATTEMPTS: 5,
  MAX_MESSAGE_SIZE: 10 * 1024, // 10KB
  MAX_AUDIO_CHUNK_SIZE: 1024 * 1024, // 1MB
} as const;

export const AUDIO_SETTINGS_DEFAULTS: AudioSettings = {
  audioGain: 50,
  autoGainEnabled: true,
  vadEnabled: false,
  chunkDuration: 3.0,
  overlapPercent: 15,
  paragraphBreakDuration: 2.0,
  language: 'nl',
  model: 'whisper-1'
} as const;

export const ERROR_MESSAGES = {
  [PairingErrorCode.INVALID_CODE]: 'Invalid pairing code format',
  [PairingErrorCode.CODE_NOT_FOUND]: 'Pairing code does not exist',
  [PairingErrorCode.CODE_EXPIRED]: 'Pairing code has expired',
  [PairingErrorCode.INVALID_TOKEN]: 'WebSocket token is invalid or expired',
  [PairingErrorCode.INVALID_CHANNEL]: 'Channel does not exist or has expired',
  [PairingErrorCode.CHANNEL_FULL]: 'Maximum number of devices already connected',
  [PairingErrorCode.RATE_LIMITED]: 'Too many requests. Please slow down',
  [PairingErrorCode.PAYLOAD_TOO_LARGE]: 'Message size exceeds maximum limit'
} as const;