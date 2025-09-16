#!/usr/bin/env python3
"""
Create a test WAV file with synthetic audio for testing transcription
"""
import wave
import numpy as np
import struct

def create_test_wav(filename, duration=2.0, sample_rate=16000):
    """Create a WAV file with synthetic speech-like audio"""

    # Generate synthetic "speech-like" audio
    frames = int(duration * sample_rate)
    t = np.linspace(0, duration, frames)

    # Create multiple frequency components to simulate speech
    frequencies = [300, 500, 800, 1200]  # Typical speech frequencies
    audio = np.zeros(frames)

    for i, freq in enumerate(frequencies):
        # Add frequency component with varying amplitude
        amplitude = 0.1 * (1 + 0.5 * np.sin(2 * np.pi * 0.5 * t))
        audio += amplitude * np.sin(2 * np.pi * freq * t)

    # Add some noise to make it more realistic
    noise = 0.02 * np.random.normal(0, 1, frames)
    audio += noise

    # Normalize to prevent clipping
    audio = audio / np.max(np.abs(audio)) * 0.8

    # Convert to 16-bit integers
    audio_int = (audio * 32767).astype(np.int16)

    # Write WAV file
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int.tobytes())

    print(f"Created test audio: {filename}")
    print(f"Duration: {duration}s, Sample rate: {sample_rate}Hz")
    print(f"File size: {len(audio_int.tobytes())} bytes")

if __name__ == "__main__":
    create_test_wav("/tmp/test_speech.wav", duration=3.0)