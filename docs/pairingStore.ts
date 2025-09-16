/**
 * Zustand Store for Device Pairing
 * Complete state management with real-time synchronization
 */

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import {
  PairingStore,
  PairingState,
  DeviceType,
  AudioSettings,
  AudioFormat,
  ConnectedDevice,
  WSMessage,
  ErrorMessage,
  PairingError,
  PairingErrorCode,
  MessageType,
  AUDIO_SETTINGS_DEFAULTS,
  PAIRING_CONSTANTS
} from './pairing-types';
import {
  PairingService,
  createSessionId,
  handlePairingError,
  mergeAudioSettings
} from './pairingService';

// ============================================================================
// Initial State
// ============================================================================

const createInitialState = (deviceType: DeviceType): PairingState => ({
  // Connection State
  isConnected: false,
  isPaired: false,
  isConnecting: false,
  connectionError: null,

  // Pairing Info
  pairingCode: null,
  channelId: null,
  deviceType,
  sessionId: createSessionId(deviceType),

  // Other Device Info
  connectedDevices: [],

  // Synced Settings (shared between devices)
  audioSettings: { ...AUDIO_SETTINGS_DEFAULTS },

  // WebSocket
  ws: null,
  wsToken: null,
  lastPingTime: null
});

// ============================================================================
// Store Implementation
// ============================================================================

export const createPairingStore = (config: {
  deviceType: DeviceType;
  baseURL: string;
  authToken?: string;
  onError?: (error: Error) => void;
}) => {
  const pairingService = new PairingService({
    baseURL: config.baseURL,
    authToken: config.authToken,
    sessionId: createSessionId(config.deviceType),
    deviceType: config.deviceType,
    onError: config.onError
  });

  return create<PairingStore>()(
    subscribeWithSelector((set, get) => ({
      // ============================================================================
      // Initial State
      // ============================================================================
      ...createInitialState(config.deviceType),

      // ============================================================================
      // Connection Actions
      // ============================================================================

      generatePairingCode: async (): Promise<string> => {
        try {
          set({ isConnecting: true, connectionError: null });

          const response = await pairingService.generatePairingCode();
          const { code, channel_id } = response;

          set({
            pairingCode: code,
            channelId: channel_id,
            isConnecting: false
          });

          // Connect to WebSocket after generating code
          await get().connectWebSocket();

          return code;
        } catch (error) {
          const pairingError = handlePairingError(error);
          set({
            isConnecting: false,
            connectionError: pairingError.message
          });
          throw pairingError;
        }
      },

      pairWithCode: async (code: string): Promise<boolean> => {
        try {
          set({ isConnecting: true, connectionError: null });

          const response = await pairingService.pairWithCode(code);

          if (response.success) {
            set({
              channelId: response.channel_id,
              isConnecting: false
            });

            // Connect to WebSocket after pairing
            await get().connectWebSocket();
            return true;
          }

          return false;
        } catch (error) {
          const pairingError = handlePairingError(error);
          set({
            isConnecting: false,
            connectionError: pairingError.message
          });
          throw pairingError;
        }
      },

      connectWebSocket: async (): Promise<void> => {
        if (get().isConnected) return;

        try {
          set({ isConnecting: true, connectionError: null });

          // Set up event handlers
          pairingService.onConnectionChange((isConnected) => {
            set({ isConnected, isConnecting: false });

            if (isConnected) {
              // Join channel if we have one
              const { channelId } = get();
              if (channelId) {
                pairingService.joinChannel(channelId);
              }
            }
          });

          pairingService.onPairingChange((isPaired) => {
            set({ isPaired });
          });

          pairingService.onSettingsSync((settings) => {
            set({ audioSettings: settings });
          });

          pairingService.onMessage(get().handleWebSocketMessage);

          // Connect
          await pairingService.connect();

        } catch (error) {
          const pairingError = handlePairingError(error);
          set({
            isConnecting: false,
            connectionError: pairingError.message
          });
          throw pairingError;
        }
      },

      disconnect: (): void => {
        pairingService.disconnect();
        set({
          isConnected: false,
          isPaired: false,
          isConnecting: false,
          connectionError: null,
          pairingCode: null,
          channelId: null,
          connectedDevices: []
        });
      },

      // ============================================================================
      // Settings Sync Actions
      // ============================================================================

      updateAudioSettings: (settings: Partial<AudioSettings>): void => {
        const currentSettings = get().audioSettings;
        const updatedSettings = mergeAudioSettings(currentSettings, settings);

        set({ audioSettings: updatedSettings });

        // Sync to other devices
        get().syncSettingsToChannel(updatedSettings);
      },

      syncSettingsToChannel: (settings?: AudioSettings): void => {
        const settingsToSync = settings || get().audioSettings;
        const { channelId } = get();

        if (!channelId) return;

        try {
          pairingService.syncSettings(settingsToSync);
        } catch (error) {
          const pairingError = handlePairingError(error);
          set({ connectionError: pairingError.message });
        }
      },

      // ============================================================================
      // Audio Actions
      // ============================================================================

      sendAudioChunk: (audioData: string, format: AudioFormat = AudioFormat.WEBM): void => {
        try {
          pairingService.sendAudioChunk(audioData, format);
        } catch (error) {
          const pairingError = handlePairingError(error);
          set({ connectionError: pairingError.message });
        }
      },

      // ============================================================================
      // Channel Actions
      // ============================================================================

      sendChannelMessage: (action: string, stateType: string, data: any): void => {
        try {
          pairingService.sendCustomMessage(action, stateType, data);
        } catch (error) {
          const pairingError = handlePairingError(error);
          set({ connectionError: pairingError.message });
        }
      },

      joinChannel: (channelId: string): void => {
        set({ channelId });

        if (get().isConnected) {
          pairingService.joinChannel(channelId);
        }
      },

      // ============================================================================
      // Internal Actions
      // ============================================================================

      setConnectionState: (isConnected: boolean, error?: string | null): void => {
        set({
          isConnected,
          connectionError: error || null,
          isConnecting: false
        });
      },

      setPairingState: (isPaired: boolean): void => {
        set({ isPaired });
      },

      handleWebSocketMessage: (message: WSMessage): void => {
        const state = get();

        switch (message.type) {
          case MessageType.PAIRING_SUCCESS:
            set({ isPaired: true });
            break;

          case MessageType.SETTINGS_SYNC:
            if ('settings' in message) {
              set({ audioSettings: message.settings as AudioSettings });
            }
            break;

          case MessageType.CHANNEL_MESSAGE:
            if ('payload' in message && message.payload) {
              const { action, stateType, data } = message.payload;

              // Handle different types of state updates
              if (action === 'STATE_UPDATE') {
                switch (stateType) {
                  case 'audioSettings':
                    const currentSettings = state.audioSettings;
                    const updatedSettings = mergeAudioSettings(currentSettings, data);
                    set({ audioSettings: updatedSettings });
                    break;

                  // Add more state types as needed
                  default:
                    console.log('Unknown state type:', stateType);
                }
              }
            }
            break;

          case MessageType.CLIENT_JOINED:
            if ('client_id' in message && 'device_type' in message) {
              const newDevice: ConnectedDevice = {
                clientId: message.client_id,
                deviceType: message.device_type as DeviceType,
                connectedAt: new Date()
              };

              set({
                connectedDevices: [...state.connectedDevices, newDevice]
              });
            }
            break;

          case MessageType.DESKTOP_DISCONNECTED:
          case MessageType.MOBILE_DISCONNECTED:
            // Remove disconnected device from list
            if ('client_id' in message) {
              set({
                connectedDevices: state.connectedDevices.filter(
                  device => device.clientId !== message.client_id
                ),
                isPaired: state.connectedDevices.length > 1
              });
            }
            break;

          case MessageType.AUDIO_CHUNK:
          case MessageType.AUDIO_DATA:
          case MessageType.AUDIO_STREAM:
            // Handle incoming audio (forward to audio processor)
            // This would typically be handled by a separate audio store/service
            break;

          case MessageType.PING:
            // Server sent ping, respond with pong (handled by service)
            break;

          case MessageType.PONG:
            set({ lastPingTime: Date.now() });
            break;

          case MessageType.ERROR:
            get().handleError(message as ErrorMessage);
            break;

          default:
            console.log('Unhandled message type:', message.type);
        }
      },

      sendPing: (): void => {
        try {
          pairingService.sendPing();
        } catch (error) {
          const pairingError = handlePairingError(error);
          set({ connectionError: pairingError.message });
        }
      },

      // ============================================================================
      // Error Handling
      // ============================================================================

      handleError: (error: ErrorMessage): void => {
        const errorMessage = error.message || 'Unknown error';
        set({ connectionError: errorMessage });

        // Handle specific error types
        switch (error.code) {
          case PairingErrorCode.INVALID_TOKEN:
            // Token expired, need to reconnect
            get().disconnect();
            break;

          case PairingErrorCode.INVALID_CHANNEL:
            // Channel expired, reset pairing
            set({
              channelId: null,
              pairingCode: null,
              isPaired: false
            });
            break;

          case PairingErrorCode.CODE_EXPIRED:
            // Code expired, generate new one
            set({ pairingCode: null });
            break;

          default:
            console.error('Pairing error:', error);
        }
      },

      clearError: (): void => {
        set({ connectionError: null });
      }
    }))
  );
};

// ============================================================================
// Hook for easier usage
// ============================================================================

export const usePairingStore = createPairingStore;

// ============================================================================
// Selectors for optimized re-renders
// ============================================================================

export const pairingSelectors = {
  // Connection selectors
  isConnected: (state: PairingStore) => state.isConnected,
  isPaired: (state: PairingStore) => state.isPaired,
  isConnecting: (state: PairingStore) => state.isConnecting,
  connectionError: (state: PairingStore) => state.connectionError,

  // Pairing info selectors
  pairingCode: (state: PairingStore) => state.pairingCode,
  channelId: (state: PairingStore) => state.channelId,
  deviceType: (state: PairingStore) => state.deviceType,

  // Settings selectors
  audioSettings: (state: PairingStore) => state.audioSettings,
  audioGain: (state: PairingStore) => state.audioSettings.audioGain,
  vadEnabled: (state: PairingStore) => state.audioSettings.vadEnabled,

  // Device selectors
  connectedDevices: (state: PairingStore) => state.connectedDevices,
  connectedDeviceCount: (state: PairingStore) => state.connectedDevices.length,

  // Actions (for component usage)
  actions: (state: PairingStore) => ({
    generatePairingCode: state.generatePairingCode,
    pairWithCode: state.pairWithCode,
    disconnect: state.disconnect,
    updateAudioSettings: state.updateAudioSettings,
    sendAudioChunk: state.sendAudioChunk,
    sendChannelMessage: state.sendChannelMessage,
    clearError: state.clearError
  })
};

// ============================================================================
// Middleware for persistence (optional)
// ============================================================================

export interface PairingPersistConfig {
  // Persist audio settings
  audioSettings?: boolean;
  // Persist device type
  deviceType?: boolean;
  // Persist session ID
  sessionId?: boolean;
}

export const createPersistentPairingStore = (config: {
  deviceType: DeviceType;
  baseURL: string;
  authToken?: string;
  onError?: (error: Error) => void;
  persistConfig?: PairingPersistConfig;
}) => {
  const { persistConfig = {} } = config;

  // Load persisted state
  const getPersistedState = (): Partial<PairingState> => {
    if (typeof window === 'undefined') return {};

    const persisted: Partial<PairingState> = {};

    if (persistConfig.audioSettings) {
      const saved = localStorage.getItem('pairing-audio-settings');
      if (saved) {
        try {
          persisted.audioSettings = JSON.parse(saved);
        } catch (error) {
          console.warn('Failed to parse persisted audio settings');
        }
      }
    }

    if (persistConfig.sessionId) {
      const saved = localStorage.getItem('pairing-session-id');
      if (saved) {
        persisted.sessionId = saved;
      }
    }

    return persisted;
  };

  const store = createPairingStore(config);

  // Subscribe to changes for persistence
  if (typeof window !== 'undefined') {
    store.subscribe(
      (state) => state.audioSettings,
      (audioSettings) => {
        if (persistConfig.audioSettings) {
          localStorage.setItem('pairing-audio-settings', JSON.stringify(audioSettings));
        }
      }
    );

    store.subscribe(
      (state) => state.sessionId,
      (sessionId) => {
        if (persistConfig.sessionId) {
          localStorage.setItem('pairing-session-id', sessionId);
        }
      }
    );
  }

  // Initialize with persisted state
  const persistedState = getPersistedState();
  if (Object.keys(persistedState).length > 0) {
    store.setState(persistedState, true);
  }

  return store;
};

// ============================================================================
// Usage Examples
// ============================================================================

/*
// Example 1: Basic store creation
const pairingStore = createPairingStore({
  deviceType: DeviceType.DESKTOP,
  baseURL: 'http://localhost:8089',
  authToken: 'your-jwt-token',
  onError: (error) => console.error('Pairing error:', error)
});

// Example 2: Using in React component
function PairingComponent() {
  const {
    isConnected,
    isPaired,
    pairingCode,
    audioSettings,
    generatePairingCode,
    updateAudioSettings
  } = pairingStore(pairingSelectors.actions);

  const handleGenerateCode = async () => {
    try {
      const code = await generatePairingCode();
      console.log('Generated code:', code);
    } catch (error) {
      console.error('Failed to generate code:', error);
    }
  };

  const handleAudioGainChange = (gain: number) => {
    updateAudioSettings({ audioGain: gain });
  };

  return (
    <div>
      <h2>Device Pairing</h2>
      <p>Status: {isConnected ? 'Connected' : 'Disconnected'}</p>
      <p>Paired: {isPaired ? 'Yes' : 'No'}</p>
      {pairingCode && <p>Code: {pairingCode}</p>}

      <button onClick={handleGenerateCode}>
        Generate Pairing Code
      </button>

      <div>
        <label>Audio Gain: {audioSettings.audioGain}</label>
        <input
          type="range"
          min="0"
          max="100"
          value={audioSettings.audioGain}
          onChange={(e) => handleAudioGainChange(Number(e.target.value))}
        />
      </div>
    </div>
  );
}

// Example 3: Persistent store
const persistentStore = createPersistentPairingStore({
  deviceType: DeviceType.MOBILE,
  baseURL: 'http://localhost:8089',
  persistConfig: {
    audioSettings: true,
    sessionId: true
  }
});
*/