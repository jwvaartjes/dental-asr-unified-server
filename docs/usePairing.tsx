/**
 * React Hook for Device Pairing
 * Easy-to-use hook for implementing device pairing in React components
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  DeviceType,
  AudioSettings,
  AudioFormat,
  ConnectedDevice,
  WSMessage,
  UsePairingReturn,
  UseAudioStreamingReturn,
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
  validatePairingCode,
  convertBlobToBase64
} from './pairingService';

// ============================================================================
// Main Pairing Hook
// ============================================================================

export function usePairing(config: {
  deviceType: DeviceType;
  baseURL: string;
  authToken?: string;
  autoConnect?: boolean;
  onPairingSuccess?: () => void;
  onError?: (error: Error) => void;
}): UsePairingReturn {
  // Connection state
  const [isConnected, setIsConnected] = useState(false);
  const [isPaired, setIsPaired] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  // Pairing state
  const [pairingCode, setPairingCode] = useState<string | null>(null);
  const [channelId, setChannelId] = useState<string | null>(null);
  const [connectedDevices, setConnectedDevices] = useState<ConnectedDevice[]>([]);

  // Service reference
  const serviceRef = useRef<PairingService | null>(null);
  const sessionIdRef = useRef(createSessionId(config.deviceType));

  // Initialize service
  useEffect(() => {
    const service = new PairingService({
      baseURL: config.baseURL,
      authToken: config.authToken,
      sessionId: sessionIdRef.current,
      deviceType: config.deviceType,
      onError: config.onError,
      onConnectionChange: (connected) => {
        setIsConnected(connected);
        setIsConnecting(false);
        if (!connected) {
          setIsPaired(false);
          setConnectedDevices([]);
        }
      },
      onPairingChange: (paired) => {
        setIsPaired(paired);
        if (paired) {
          config.onPairingSuccess?.();
        }
      },
      onSettingsSync: (settings) => {
        // Settings sync handled by separate hook or store
      }
    });

    // Set up message handler
    service.onMessage(handleMessage);

    serviceRef.current = service;

    // Auto-connect if enabled
    if (config.autoConnect) {
      connectWebSocket();
    }

    return () => {
      service.disconnect();
    };
  }, [config.baseURL, config.authToken, config.deviceType]);

  // ============================================================================
  // Message Handler
  // ============================================================================

  const handleMessage = useCallback((message: WSMessage) => {
    switch (message.type) {
      case MessageType.CLIENT_JOINED:
        if ('client_id' in message && 'device_type' in message) {
          const newDevice: ConnectedDevice = {
            clientId: message.client_id,
            deviceType: message.device_type as DeviceType,
            connectedAt: new Date()
          };
          setConnectedDevices(prev => [...prev, newDevice]);
        }
        break;

      case MessageType.DESKTOP_DISCONNECTED:
      case MessageType.MOBILE_DISCONNECTED:
        if ('client_id' in message) {
          setConnectedDevices(prev =>
            prev.filter(device => device.clientId !== message.client_id)
          );
        }
        break;

      case MessageType.ERROR:
        if ('message' in message) {
          setConnectionError(message.message);
        }
        break;
    }
  }, []);

  // ============================================================================
  // Actions
  // ============================================================================

  const connectWebSocket = useCallback(async () => {
    if (!serviceRef.current || isConnected) return;

    try {
      setIsConnecting(true);
      setConnectionError(null);
      await serviceRef.current.connect();
    } catch (error) {
      const pairingError = handlePairingError(error);
      setConnectionError(pairingError.message);
      setIsConnecting(false);
    }
  }, [isConnected]);

  const generateCode = useCallback(async (): Promise<string> => {
    if (!serviceRef.current) {
      throw new PairingError(PairingErrorCode.INVALID_CODE, 'Service not initialized');
    }

    try {
      setIsConnecting(true);
      setConnectionError(null);

      const response = await serviceRef.current.generatePairingCode();
      const { code, channel_id } = response;

      setPairingCode(code);
      setChannelId(channel_id);

      // Connect WebSocket if not already connected
      if (!isConnected) {
        await connectWebSocket();
      } else {
        // Join channel if already connected
        serviceRef.current.joinChannel(channel_id);
      }

      return code;
    } catch (error) {
      const pairingError = handlePairingError(error);
      setConnectionError(pairingError.message);
      throw pairingError;
    } finally {
      setIsConnecting(false);
    }
  }, [isConnected, connectWebSocket]);

  const pairWithCode = useCallback(async (code: string): Promise<boolean> => {
    if (!serviceRef.current) {
      throw new PairingError(PairingErrorCode.INVALID_CODE, 'Service not initialized');
    }

    if (!validatePairingCode(code)) {
      throw new PairingError(
        PairingErrorCode.INVALID_CODE,
        'Pairing code must be 6 digits'
      );
    }

    try {
      setIsConnecting(true);
      setConnectionError(null);

      const response = await serviceRef.current.pairWithCode(code);

      if (response.success) {
        setChannelId(response.channel_id);

        // Connect WebSocket if not already connected
        if (!isConnected) {
          await connectWebSocket();
        } else {
          // Join channel if already connected
          serviceRef.current.joinChannel(response.channel_id);
        }

        return true;
      }

      return false;
    } catch (error) {
      const pairingError = handlePairingError(error);
      setConnectionError(pairingError.message);
      throw pairingError;
    } finally {
      setIsConnecting(false);
    }
  }, [isConnected, connectWebSocket]);

  const disconnect = useCallback(() => {
    serviceRef.current?.disconnect();
    setPairingCode(null);
    setChannelId(null);
    setConnectionError(null);
    setConnectedDevices([]);
  }, []);

  const syncAudioSettings = useCallback((settings: Partial<AudioSettings>) => {
    if (!serviceRef.current || !isPaired) return;

    try {
      const mergedSettings = { ...AUDIO_SETTINGS_DEFAULTS, ...settings };
      serviceRef.current.syncSettings(mergedSettings);
    } catch (error) {
      const pairingError = handlePairingError(error);
      setConnectionError(pairingError.message);
    }
  }, [isPaired]);

  const sendAudioChunk = useCallback((audioData: string, format: AudioFormat = AudioFormat.WEBM) => {
    if (!serviceRef.current || !isPaired) return;

    try {
      serviceRef.current.sendAudioChunk(audioData, format);
    } catch (error) {
      const pairingError = handlePairingError(error);
      setConnectionError(pairingError.message);
    }
  }, [isPaired]);

  const sendCustomMessage = useCallback((action: string, stateType: string, data: any) => {
    if (!serviceRef.current || !isPaired) return;

    try {
      serviceRef.current.sendCustomMessage(action, stateType, data);
    } catch (error) {
      const pairingError = handlePairingError(error);
      setConnectionError(pairingError.message);
    }
  }, [isPaired]);

  return {
    // State
    isConnected,
    isPaired,
    isConnecting,
    pairingCode,
    channelId,
    connectionError,
    connectedDevices,

    // Actions
    generateCode,
    pairWithCode,
    disconnect,
    syncAudioSettings,
    sendAudioChunk,
    sendCustomMessage
  };
}

// ============================================================================
// Audio Streaming Hook
// ============================================================================

export function useAudioStreaming(pairingHook: UsePairingReturn): UseAudioStreamingReturn {
  // Audio state
  const [isRecording, setIsRecording] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [audioFormat] = useState<AudioFormat>(AudioFormat.WEBM);
  const [audioSettings, setAudioSettings] = useState<AudioSettings>(AUDIO_SETTINGS_DEFAULTS);

  // Audio references
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  // ============================================================================
  // Audio Level Monitoring
  // ============================================================================

  const updateAudioLevel = useCallback(() => {
    if (!analyserRef.current) return;

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);

    // Calculate RMS (Root Mean Square) for audio level
    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) {
      sum += dataArray[i] * dataArray[i];
    }
    const rms = Math.sqrt(sum / dataArray.length);
    const level = Math.min(100, (rms / 128) * 100); // Normalize to 0-100

    setAudioLevel(level);

    if (isRecording) {
      animationFrameRef.current = requestAnimationFrame(updateAudioLevel);
    }
  }, [isRecording]);

  // ============================================================================
  // Recording Controls
  // ============================================================================

  const startRecording = useCallback(async (): Promise<void> => {
    try {
      // Get user media
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        }
      });

      streamRef.current = stream;

      // Set up audio analysis
      const audioContext = new AudioContext({ sampleRate: 16000 });
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();

      analyser.fftSize = 256;
      source.connect(analyser);

      audioContextRef.current = audioContext;
      analyserRef.current = analyser;

      // Set up media recorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      mediaRecorderRef.current = mediaRecorder;

      // Handle recorded chunks
      const audioChunks: Blob[] = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm;codecs=opus' });

        try {
          const base64Data = await convertBlobToBase64(audioBlob);
          pairingHook.sendAudioChunk(base64Data, AudioFormat.WEBM);
        } catch (error) {
          console.error('Failed to send audio chunk:', error);
        }

        audioChunks.length = 0; // Clear chunks
      };

      // Start recording
      mediaRecorder.start();
      setIsRecording(true);

      // Start audio level monitoring
      updateAudioLevel();

    } catch (error) {
      console.error('Failed to start recording:', error);
      throw error;
    }
  }, [pairingHook, updateAudioLevel]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
    }

    // Clean up audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    // Stop stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    // Cancel animation frame
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }

    setIsRecording(false);
    setAudioLevel(0);
  }, [isRecording]);

  const sendAudioChunk = useCallback(async (chunk: Blob): Promise<void> => {
    try {
      const base64Data = await convertBlobToBase64(chunk);
      pairingHook.sendAudioChunk(base64Data, audioFormat);
    } catch (error) {
      console.error('Failed to send audio chunk:', error);
      throw error;
    }
  }, [pairingHook, audioFormat]);

  // ============================================================================
  // Settings Management
  // ============================================================================

  const updateAudioSettings = useCallback((settings: Partial<AudioSettings>) => {
    const newSettings = { ...audioSettings, ...settings };
    setAudioSettings(newSettings);

    // Sync to paired device
    pairingHook.syncAudioSettings(newSettings);
  }, [audioSettings, pairingHook]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopRecording();
    };
  }, [stopRecording]);

  return {
    // Audio State
    isRecording,
    audioLevel,
    audioFormat,

    // Settings
    audioSettings,
    updateAudioSettings,

    // Actions
    startRecording,
    stopRecording,
    sendAudioChunk
  };
}

// ============================================================================
// Utility Hooks
// ============================================================================

export function usePairingCode(
  initialCode?: string
): [string, (code: string) => void, boolean] {
  const [code, setCode] = useState(initialCode || '');
  const isValid = validatePairingCode(code);

  const handleCodeChange = useCallback((newCode: string) => {
    // Only allow digits and limit to 6 characters
    const cleanCode = newCode.replace(/\D/g, '').slice(0, 6);
    setCode(cleanCode);
  }, []);

  return [code, handleCodeChange, isValid];
}

export function useConnectionStatus(pairingHook: UsePairingReturn) {
  const [connectionHistory, setConnectionHistory] = useState<{
    timestamp: Date;
    status: 'connected' | 'disconnected' | 'paired' | 'unpaired';
  }[]>([]);

  useEffect(() => {
    const addHistoryEntry = (status: 'connected' | 'disconnected' | 'paired' | 'unpaired') => {
      setConnectionHistory(prev => [
        ...prev.slice(-9), // Keep last 10 entries
        { timestamp: new Date(), status }
      ]);
    };

    if (pairingHook.isConnected) {
      addHistoryEntry('connected');
    } else {
      addHistoryEntry('disconnected');
    }
  }, [pairingHook.isConnected]);

  useEffect(() => {
    const addHistoryEntry = (status: 'connected' | 'disconnected' | 'paired' | 'unpaired') => {
      setConnectionHistory(prev => [
        ...prev.slice(-9), // Keep last 10 entries
        { timestamp: new Date(), status }
      ]);
    };

    if (pairingHook.isPaired) {
      addHistoryEntry('paired');
    } else {
      addHistoryEntry('unpaired');
    }
  }, [pairingHook.isPaired]);

  return {
    connectionHistory,
    isStable: pairingHook.isConnected && !pairingHook.isConnecting,
    hasError: !!pairingHook.connectionError
  };
}

// ============================================================================
// Example Usage Components
// ============================================================================

/*
// Example 1: Desktop Component
function DesktopPairingComponent() {
  const pairing = usePairing({
    deviceType: DeviceType.DESKTOP,
    baseURL: 'http://localhost:8089',
    authToken: 'your-jwt-token',
    autoConnect: true,
    onPairingSuccess: () => console.log('Paired successfully!'),
    onError: (error) => console.error('Pairing error:', error)
  });

  const audio = useAudioStreaming(pairing);
  const connectionStatus = useConnectionStatus(pairing);

  const handleGenerateCode = async () => {
    try {
      const code = await pairing.generateCode();
      console.log('Generated pairing code:', code);
    } catch (error) {
      console.error('Failed to generate code:', error);
    }
  };

  return (
    <div>
      <h2>Desktop Pairing</h2>
      <p>Status: {pairing.isConnected ? 'Connected' : 'Disconnected'}</p>
      <p>Paired: {pairing.isPaired ? 'Yes' : 'No'}</p>

      {pairing.pairingCode && (
        <div>
          <h3>Pairing Code: {pairing.pairingCode}</h3>
          <p>Enter this code on your mobile device</p>
        </div>
      )}

      <button onClick={handleGenerateCode} disabled={pairing.isConnecting}>
        {pairing.isConnecting ? 'Generating...' : 'Generate Code'}
      </button>

      <button onClick={() => audio.startRecording()} disabled={audio.isRecording}>
        Start Recording
      </button>

      <button onClick={() => audio.stopRecording()} disabled={!audio.isRecording}>
        Stop Recording
      </button>

      {audio.isRecording && (
        <div>
          <p>Recording... Audio Level: {audio.audioLevel.toFixed(1)}%</p>
        </div>
      )}
    </div>
  );
}

// Example 2: Mobile Component
function MobilePairingComponent() {
  const pairing = usePairing({
    deviceType: DeviceType.MOBILE,
    baseURL: 'http://localhost:8089',
    authToken: 'your-jwt-token',
    autoConnect: false,
    onPairingSuccess: () => console.log('Paired with desktop!'),
    onError: (error) => console.error('Pairing error:', error)
  });

  const [code, setCode, isCodeValid] = usePairingCode();

  const handlePair = async () => {
    if (!isCodeValid) return;

    try {
      const success = await pairing.pairWithCode(code);
      if (success) {
        console.log('Successfully paired!');
      }
    } catch (error) {
      console.error('Failed to pair:', error);
    }
  };

  return (
    <div>
      <h2>Mobile Pairing</h2>
      <p>Status: {pairing.isConnected ? 'Connected' : 'Disconnected'}</p>
      <p>Paired: {pairing.isPaired ? 'Yes' : 'No'}</p>

      <div>
        <label>Enter Pairing Code:</label>
        <input
          type="text"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="123456"
          maxLength={6}
        />
      </div>

      <button onClick={handlePair} disabled={!isCodeValid || pairing.isConnecting}>
        {pairing.isConnecting ? 'Pairing...' : 'Pair'}
      </button>

      {pairing.connectionError && (
        <p style={{ color: 'red' }}>Error: {pairing.connectionError}</p>
      )}
    </div>
  );
}
*/