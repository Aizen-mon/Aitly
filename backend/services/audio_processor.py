"""Audio processing utilities for speech-to-text."""

from __future__ import annotations

import io
import logging
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from pydub import AudioSegment

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Handle audio format conversion and preprocessing."""
    
    SUPPORTED_FORMATS = {"wav", "mp3", "m4a", "ogg", "flac", "aac"}
    TARGET_SAMPLE_RATE = 16000
    
    @staticmethod
    def convert_to_wav(
        audio_data: bytes,
        input_format: str = "auto",
        sample_rate: int = 16000,
        mono: bool = True,
    ) -> bytes:
        """
        Convert audio to WAV format with specified sample rate.
        
        Args:
            audio_data: Raw audio bytes
            input_format: Input format (auto-detect, wav, mp3, m4a, etc)
            sample_rate: Target sample rate (default 16000 for Whisper)
            mono: Convert to mono if True
            
        Returns:
            WAV-encoded audio bytes
        """
        try:
            # Auto-detect format from header if requested
            if input_format == "auto":
                input_format = AudioProcessor._detect_format(audio_data)
            
            # Load audio
            if input_format.lower() in ("wav", "wave"):
                audio = AudioSegment.from_wav(io.BytesIO(audio_data))
            elif input_format.lower() in ("mp3", "mpeg"):
                audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
            elif input_format.lower() in ("m4a", "aac"):
                audio = AudioSegment.from_file(io.BytesIO(audio_data), format="mp4")
            elif input_format.lower() == "ogg":
                audio = AudioSegment.from_ogg(io.BytesIO(audio_data))
            elif input_format.lower() == "flac":
                audio = AudioSegment.from_file(io.BytesIO(audio_data), format="flac")
            else:
                # Try generic format detection
                audio = AudioSegment.from_file(io.BytesIO(audio_data), format=input_format.lower())
            
            # Resample if needed
            if audio.frame_rate != sample_rate:
                audio = audio.set_frame_rate(sample_rate)
            
            # Convert to mono if requested
            if mono and audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Convert to 16-bit PCM
            audio = audio.set_sample_width(2)
            
            # Export as WAV
            with io.BytesIO() as wav_buffer:
                audio.export(wav_buffer, format="wav")
                return wav_buffer.getvalue()
        
        except Exception as e:
            logger.error(f"Failed to convert audio: {e}")
            raise ValueError(f"Audio conversion failed: {str(e)}")
    
    @staticmethod
    def convert_to_numpy(
        audio_data: bytes,
        sample_rate: int = 16000,
    ) -> np.ndarray:
        """
        Convert audio bytes to NumPy array for Faster-Whisper.
        
        Args:
            audio_data: Raw audio bytes (WAV format preferred)
            sample_rate: Expected sample rate
            
        Returns:
            NumPy array of audio samples (float32, normalized to [-1, 1])
        """
        try:
            # Convert to WAV first if needed
            wav_data = AudioProcessor.convert_to_wav(audio_data, sample_rate=sample_rate)
            
            # Load with pydub
            audio = AudioSegment.from_wav(io.BytesIO(wav_data))
            
            # Convert to NumPy array
            samples = np.array(audio.get_array_of_samples())
            
            # Normalize to float32 in range [-1, 1]
            samples = samples.astype(np.float32) / 32768.0
            
            return samples
        
        except Exception as e:
            logger.error(f"Failed to convert audio to numpy: {e}")
            raise ValueError(f"Audio conversion to numpy failed: {str(e)}")
    
    @staticmethod
    def detect_audio_format(audio_data: bytes) -> str:
        """Detect audio format from file header (magic bytes)."""
        if len(audio_data) < 4:
            return "unknown"
        
        # WAV: RIFF....WAVE
        if audio_data[:4] == b"RIFF" and audio_data[8:12] == b"WAVE":
            return "wav"
        
        # MP3: FFxx or ID3
        if audio_data[:2] == b"\xff\xfb" or audio_data[:2] == b"\xff\xfa" or audio_data[:3] == b"ID3":
            return "mp3"
        
        # M4A/AAC: ftyp
        if audio_data[4:8] == b"ftyp":
            return "m4a"
        
        # OGG: OggS
        if audio_data[:4] == b"OggS":
            return "ogg"
        
        # FLAC: fLaC
        if audio_data[:4] == b"fLaC":
            return "flac"
        
        return "unknown"
    
    @staticmethod
    def _detect_format(audio_data: bytes) -> str:
        """Internal method for format detection."""
        fmt = AudioProcessor.detect_audio_format(audio_data)
        return fmt if fmt != "unknown" else "wav"
    
    @staticmethod
    def chunk_audio(
        audio_data: bytes,
        chunk_length_seconds: int = 30,
        overlap_seconds: int = 2,
    ) -> list[Tuple[bytes, int]]:
        """
        Split long audio into chunks for processing.
        
        Args:
            audio_data: Audio bytes
            chunk_length_seconds: Length of each chunk
            overlap_seconds: Overlap between chunks
            
        Returns:
            List of (chunk_bytes, start_time_ms) tuples
        """
        try:
            audio = AudioSegment.from_wav(io.BytesIO(audio_data))
            
            chunk_ms = chunk_length_seconds * 1000
            overlap_ms = overlap_seconds * 1000
            step_ms = chunk_ms - overlap_ms
            
            chunks = []
            start_ms = 0
            
            while start_ms < len(audio):
                end_ms = min(start_ms + chunk_ms, len(audio))
                chunk = audio[start_ms:end_ms]
                
                with io.BytesIO() as chunk_buffer:
                    chunk.export(chunk_buffer, format="wav")
                    chunks.append((chunk_buffer.getvalue(), start_ms))
                
                start_ms += step_ms
            
            return chunks
        
        except Exception as e:
            logger.error(f"Failed to chunk audio: {e}")
            return [(audio_data, 0)]
    
    @staticmethod
    def validate_audio(
        audio_data: bytes,
        min_duration_seconds: float = 0.5,
        max_duration_seconds: float = 3600,
    ) -> Tuple[bool, str]:
        """
        Validate audio data.
        
        Args:
            audio_data: Audio bytes to validate
            min_duration_seconds: Minimum duration
            max_duration_seconds: Maximum duration
            
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            if not audio_data or len(audio_data) < 100:
                return False, "Audio data too small"
            
            audio = AudioSegment.from_wav(io.BytesIO(audio_data))
            duration_seconds = len(audio) / 1000.0
            
            if duration_seconds < min_duration_seconds:
                return False, f"Audio too short (< {min_duration_seconds}s)"
            
            if duration_seconds > max_duration_seconds:
                return False, f"Audio too long (> {max_duration_seconds}s)"
            
            if audio.frame_rate not in (16000, 22050, 44100, 48000):
                return True, f"Non-standard sample rate: {audio.frame_rate} Hz"
            
            return True, "Valid"
        
        except Exception as e:
            return False, f"Invalid audio: {str(e)}"
