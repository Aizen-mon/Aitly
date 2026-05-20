"""Speech-to-Text service using Faster-Whisper."""

from __future__ import annotations

import logging
import os
from typing import Dict, Optional

from faster_whisper import WhisperModel

from whisper_config import WhisperConfig, get_whisper_config, set_whisper_config

logger = logging.getLogger(__name__)


class STTService:
    """
    Speech-to-Text service using Faster-Whisper for local, offline transcription.
    Supports multiple languages with optimization for Indian English.
    """
    
    _instance: Optional[STTService] = None
    _model: Optional[WhisperModel] = None
    
    def __init__(self, config: Optional[WhisperConfig] = None):
        """Initialize STT service with Faster-Whisper."""
        self.config = config or get_whisper_config()
        self._model_cache = {}
        self._load_model()
    
    @classmethod
    def get_instance(cls, config: Optional[WhisperConfig] = None) -> STTService:
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance
    
    @classmethod
    def set_instance(cls, instance: STTService) -> None:
        """Override the singleton instance."""
        cls._instance = instance
    
    def _load_model(self) -> None:
        """Load Faster-Whisper model."""
        try:
            model_key = f"{self.config.model_name}_{self.config.device}_{self.config.compute_type}"
            
            if model_key not in self._model_cache:
                logger.info(
                    f"Loading Whisper model: {self.config.model_name} on {self.config.device} "
                    f"(compute_type={self.config.compute_type})"
                )
                
                # Download model if not cached locally
                model_dir = os.path.expanduser("~/.cache/huggingface/hub/")
                
                model = WhisperModel(
                    model_size_or_path=self.config.model_name.value,
                    device=self.config.device,
                    compute_type=self.config.compute_type.value,
                    download_root=model_dir,
                    local_files_only=False,  # Allow download on first run
                    num_workers=self.config.num_workers,
                    cpu_threads=self.config.cpu_threads,
                )
                
                self._model_cache[model_key] = model
                logger.info(f"Whisper model loaded successfully")
            
            STTService._model = self._model_cache[model_key]
        
        except ImportError as e:
            logger.error(
                f"faster-whisper not installed. Install with: pip install faster-whisper"
            )
            raise ImportError("faster-whisper is required for STT") from e
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise RuntimeError(f"Model loading failed: {str(e)}")
    
    def transcribe(
        self,
        audio: bytes | str,
        language: Optional[str] = None,
        task: str = "transcribe",
    ) -> Dict[str, object]:
        """
        Transcribe audio to text.
        
        Args:
            audio: Audio bytes or file path
            language: Language code (e.g., 'en', 'hi', auto-detect if None)
            task: 'transcribe' for STT or 'translate' for translation to English
            
        Returns:
            Dict with transcription, confidence, and metadata
        """
        if not STTService._model:
            raise RuntimeError("Whisper model not loaded")
        
        try:
            lang = language or self.config.language
            
            # Transcribe
            segments, info = STTService._model.transcribe(
                audio,
                language=lang if lang != "auto" else None,
                task=task,
                temperature=self.config.temperature,
                beam_size=self.config.beam_size,
                best_of=self.config.best_of,
                patience=self.config.patience,
                condition_on_previous_text=True,
                compression_ratio_threshold=2.4,
                no_speech_threshold=0.6,
            )
            
            # Collect segments
            text_parts = []
            confidence_scores = []
            segment_list = []
            
            for segment in segments:
                text_parts.append(segment.text)
                confidence_scores.append(segment.confidence)
                
                segment_list.append({
                    "id": segment.id,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "confidence": segment.confidence,
                })
            
            full_text = " ".join(text_parts).strip()
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            return {
                "text": full_text,
                "transcript": full_text,  # Alias for compatibility
                "language": info.language,
                "language_probability": info.language_probability,
                "confidence": round(avg_confidence, 3),
                "segments": segment_list,
                "duration_seconds": info.duration,
                "success": True,
            }
        
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {
                "text": "",
                "transcript": "",
                "error": str(e),
                "success": False,
                "confidence": 0.0,
            }
    
    def transcribe_multilingual(
        self,
        audio: bytes | str,
        task: str = "transcribe",
    ) -> Dict[str, object]:
        """
        Transcribe audio with automatic language detection.
        
        Args:
            audio: Audio bytes or file path
            task: 'transcribe' for STT or 'translate' for translation
            
        Returns:
            Dict with transcription, detected language, and metadata
        """
        return self.transcribe(audio, language=None, task=task)
    
    def transcribe_chunk(
        self,
        audio: bytes | str,
        language: Optional[str] = None,
        start_offset_seconds: float = 0,
    ) -> Dict[str, object]:
        """
        Transcribe a chunk of audio (useful for streaming).
        
        Args:
            audio: Audio bytes or file path
            language: Language code
            start_offset_seconds: Start time offset for segment timing
            
        Returns:
            Transcription with adjusted timestamps
        """
        result = self.transcribe(audio, language=language)
        
        # Adjust segment times if offset provided
        if start_offset_seconds > 0 and "segments" in result:
            for segment in result["segments"]:
                segment["start"] += start_offset_seconds
                segment["end"] += start_offset_seconds
        
        return result
    
    def get_model_info(self) -> Dict[str, str]:
        """Get information about the loaded model."""
        return {
            "model": self.config.model_name.value,
            "device": self.config.device,
            "compute_type": self.config.compute_type.value,
            "language": self.config.language,
        }
    
    def reconfigure(self, config: WhisperConfig) -> None:
        """Reconfigure with a new config."""
        self.config = config
        self._load_model()
    
    def set_language(self, language: str) -> None:
        """Set the default language for transcription."""
        self.config.language = language


# Global singleton instance
_stt_service: Optional[STTService] = None


def get_stt_service(config: Optional[WhisperConfig] = None) -> STTService:
    """Get or create the STT service singleton."""
    global _stt_service
    if _stt_service is None:
        _stt_service = STTService(config)
    return _stt_service


def initialize_stt(config: Optional[WhisperConfig] = None) -> STTService:
    """Initialize and return the STT service."""
    global _stt_service
    _stt_service = STTService(config)
    return _stt_service
