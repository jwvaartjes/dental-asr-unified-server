"""
Audio processing utilities for real-time transcription.
Provides PCM16LE audio analysis functions for voice activity detection and endpointing.
"""

import base64
import math
import struct
import io
import wave
from typing import Optional, Iterator, Tuple


# Audio format constants
BYTES_PER_SAMPLE = 2
SAMPLE_RATE = 16000
BYTES_PER_SECOND = SAMPLE_RATE * BYTES_PER_SAMPLE


def pcm16le_rms(pcm: bytes) -> float:
    """
    Calculate RMS (Root Mean Square) energy of PCM16LE audio data.

    Args:
        pcm: Raw PCM16LE audio bytes (little-endian signed 16-bit)

    Returns:
        float: RMS energy normalized to 0..1 range (1.0 = full scale)
    """
    if not pcm or len(pcm) < 2:
        return 0.0

    # Interpret as little-endian signed 16-bit samples
    # Use memoryview for efficient processing without copies
    try:
        mv = memoryview(pcm).cast('h')  # 'h' = signed short (16-bit)

        # Calculate sum of squares
        acc = 0
        for sample in mv:
            acc += sample * sample

        # Calculate mean square
        mean_sq = acc / len(mv)

        # Return RMS normalized by full scale (32768 = 2^15)
        return math.sqrt(mean_sq) / 32768.0

    except (ValueError, struct.error):
        return 0.0


def pcm16le_zcr(pcm: bytes) -> float:
    """
    Calculate Zero-Crossing Rate of PCM16LE audio data.
    ZCR is useful for distinguishing between voice and noise.

    Args:
        pcm: Raw PCM16LE audio bytes

    Returns:
        float: Zero-crossing rate (0..1) where 1.0 means every sample crosses zero
    """
    if not pcm or len(pcm) < 4:  # Need at least 2 samples
        return 0.0

    try:
        mv = memoryview(pcm).cast('h')

        if len(mv) < 2:
            return 0.0

        crossings = 0
        prev_sample = mv[0]

        for sample in mv[1:]:
            # Count zero crossings (sign changes)
            if (prev_sample < 0 and sample >= 0) or (prev_sample > 0 and sample <= 0):
                crossings += 1
            prev_sample = sample

        # Return crossing rate per sample
        return crossings / (len(mv) - 1)

    except (ValueError, struct.error):
        return 0.0


def pcm16le_to_base64(pcm: bytes) -> str:
    """
    Convert PCM16LE audio bytes to base64 string for OpenAI API.

    Args:
        pcm: Raw PCM16LE audio bytes

    Returns:
        str: Base64 encoded audio data
    """
    return base64.b64encode(pcm).decode("ascii")


def rms_to_dbfs(rms: float) -> float:
    """
    Convert RMS value to dBFS (decibels relative to full scale).

    Args:
        rms: RMS value (0..1)

    Returns:
        float: dBFS value (negative, -inf to 0)
    """
    if rms <= 0:
        return float('-inf')
    return 20 * math.log10(rms)


def dbfs_to_rms(dbfs: float) -> float:
    """
    Convert dBFS to RMS value.

    Args:
        dbfs: dBFS value (negative)

    Returns:
        float: RMS value (0..1)
    """
    if dbfs == float('-inf'):
        return 0.0
    return 10 ** (dbfs / 20)


def calculate_duration_ms(pcm_bytes: int) -> float:
    """
    Calculate duration in milliseconds for PCM16LE audio data.

    Args:
        pcm_bytes: Number of PCM bytes

    Returns:
        float: Duration in milliseconds
    """
    return (pcm_bytes / BYTES_PER_SECOND) * 1000.0


def is_voice_activity(rms: float, zcr: float,
                     rms_threshold: float = 0.015,
                     zcr_max: float = 0.15) -> bool:
    """
    Determine if audio contains voice activity based on RMS and ZCR.

    Args:
        rms: RMS energy level
        zcr: Zero-crossing rate
        rms_threshold: Minimum RMS for voice detection
        zcr_max: Maximum ZCR for voice (higher = more noise-like)

    Returns:
        bool: True if voice activity detected
    """
    return rms >= rms_threshold and zcr <= zcr_max


def is_silence(rms: float, zcr: float,
               rms_threshold: float = 0.010,
               zcr_max: float = 0.15) -> bool:
    """
    Determine if audio is silence based on RMS and ZCR.

    Args:
        rms: RMS energy level
        zcr: Zero-crossing rate
        rms_threshold: Maximum RMS for silence
        zcr_max: Maximum ZCR for silence

    Returns:
        bool: True if silence detected
    """
    return rms <= rms_threshold and zcr <= zcr_max


class AudioAnalyzer:
    """Helper class for analyzing audio frames with configurable thresholds."""

    def __init__(self,
                 voice_rms_threshold: float = 0.015,
                 silence_rms_threshold: float = 0.010,
                 zcr_max: float = 0.15):
        """
        Initialize audio analyzer with thresholds.

        Args:
            voice_rms_threshold: Minimum RMS for voice detection (~-36 dBFS)
            silence_rms_threshold: Maximum RMS for silence (~-40 dBFS)
            zcr_max: Maximum ZCR for voice/silence discrimination
        """
        self.voice_rms_threshold = voice_rms_threshold
        self.silence_rms_threshold = silence_rms_threshold
        self.zcr_max = zcr_max

    def analyze_frame(self, pcm: bytes) -> dict:
        """
        Analyze a single audio frame.

        Args:
            pcm: PCM16LE audio bytes

        Returns:
            dict: Analysis results with keys: rms, zcr, dbfs, is_voice, is_silence
        """
        rms = pcm16le_rms(pcm)
        zcr = pcm16le_zcr(pcm)
        dbfs = rms_to_dbfs(rms)

        return {
            'rms': rms,
            'zcr': zcr,
            'dbfs': dbfs,
            'is_voice': is_voice_activity(rms, zcr, self.voice_rms_threshold, self.zcr_max),
            'is_silence': is_silence(rms, zcr, self.silence_rms_threshold, self.zcr_max),
            'duration_ms': calculate_duration_ms(len(pcm))
        }


def iter_wav_pcm16_mono16k_chunks(wav_bytes: bytes, chunk_ms: int = 20) -> Iterator[bytes]:
    """
    Read WAV file and yield PCM16-LE bytes in chunks of specified duration.

    This function is key for the hybrid approach: frontend sends WAV after VAD,
    server chunks it into small PCM pieces for OpenAI Realtime API.

    Args:
        wav_bytes: Complete WAV file as bytes
        chunk_ms: Chunk duration in milliseconds (default: 20ms)

    Yields:
        bytes: PCM16-LE audio chunks

    Raises:
        ValueError: If WAV format is not mono 16kHz 16-bit
    """
    bio = io.BytesIO(wav_bytes)
    try:
        with wave.open(bio, "rb") as wf:
            nch = wf.getnchannels()
            sr = wf.getframerate()
            sw = wf.getsampwidth()

            if sr != 16000 or sw != 2 or nch != 1:
                raise ValueError(f"Expected mono 16kHz 16-bit WAV, got ch={nch} sr={sr} sw={sw}")

            samples_per_chunk = int(sr * (chunk_ms / 1000.0))
            frames_per_chunk = samples_per_chunk  # 1 sample per frame in mono

            while True:
                data = wf.readframes(frames_per_chunk)
                if not data:
                    break
                yield data

    except wave.Error as e:
        raise ValueError(f"Invalid WAV file: {e}")


def validate_wav_format(wav_bytes: bytes) -> Tuple[bool, str, dict]:
    """
    Validate WAV file format and return details.

    Args:
        wav_bytes: WAV file as bytes

    Returns:
        Tuple[bool, str, dict]: (is_valid, error_message, format_info)
    """
    try:
        bio = io.BytesIO(wav_bytes)
        with wave.open(bio, "rb") as wf:
            format_info = {
                'channels': wf.getnchannels(),
                'sample_rate': wf.getframerate(),
                'sample_width': wf.getsampwidth(),
                'frames': wf.getnframes(),
                'duration_ms': (wf.getnframes() / wf.getframerate()) * 1000 if wf.getframerate() > 0 else 0
            }

            # Check if format matches requirements
            if (format_info['channels'] == 1 and
                format_info['sample_rate'] == 16000 and
                format_info['sample_width'] == 2):
                return True, "Valid format", format_info
            else:
                error = f"Invalid format: {format_info['channels']}ch, {format_info['sample_rate']}Hz, {format_info['sample_width']*8}bit"
                return False, error, format_info

    except wave.Error as e:
        return False, f"WAV parsing error: {e}", {}
    except Exception as e:
        return False, f"Unexpected error: {e}", {}


def wav_to_pcm_chunks(wav_bytes: bytes, chunk_ms: int = 20) -> Iterator[bytes]:
    """
    Convert WAV file to PCM16LE chunks.
    Alias for iter_wav_pcm16_mono16k_chunks for clearer naming.

    Args:
        wav_bytes: Complete WAV file as bytes
        chunk_ms: Chunk duration in milliseconds

    Yields:
        bytes: PCM16-LE audio chunks
    """
    yield from iter_wav_pcm16_mono16k_chunks(wav_bytes, chunk_ms)