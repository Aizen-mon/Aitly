"""Configuration for Faster-Whisper speech-to-text engine."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Literal


class WhisperModel(str, Enum):
    """Available Whisper model sizes."""
    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large-v3"


class ComputeType(str, Enum):
    """Compute type options for inference."""
    FLOAT32 = "float32"
    FLOAT16 = "float16"
    INT8 = "int8"


@dataclass
class WhisperConfig:
    """Configuration for Faster-Whisper initialization and inference."""
    
    # Model configuration
    model_name: WhisperModel = WhisperModel.MEDIUM
    device: Literal["cpu", "cuda"] = "cpu"
    compute_type: ComputeType = ComputeType.FLOAT32
    
    # Inference settings
    language: str = "en"  # Default to English; auto-detect supported
    temperature: float = 0.0  # Deterministic output
    beam_size: int = 5  # Higher for accuracy, lower for speed
    best_of: int = 5  # Number of passes for beam search
    patience: float = 1.0  # Patience for early stopping
    
    # Input/output settings
    sample_rate: int = 16000  # Standard for Whisper
    chunk_length: int = 30  # Seconds per chunk for long audio
    
    # Performance settings
    num_workers: int = 1  # Number of async workers
    cpu_threads: int = 4  # For CPU inference
    
    # Optimization
    fp16: bool = False  # Use half precision
    memory_efficient: bool = False  # Trade speed for memory
    
    # Indian English specific
    optimize_for_indian_english: bool = True
    
    @classmethod
    def for_cpu_only(cls) -> WhisperConfig:
        """Optimized config for CPU-only systems."""
        return cls(
            model_name=WhisperModel.MEDIUM,
            device="cpu",
            compute_type=ComputeType.FLOAT32,
            beam_size=3,
            best_of=3,
            patience=0.5,
            num_workers=1,
            cpu_threads=4,
        )
    
    @classmethod
    def for_mid_range_pc(cls) -> WhisperConfig:
        """Optimized config for mid-range PCs (4-8 cores)."""
        return cls(
            model_name=WhisperModel.MEDIUM,
            device="cpu",
            compute_type=ComputeType.FLOAT16,
            beam_size=5,
            best_of=5,
            num_workers=2,
            cpu_threads=6,
            fp16=True,
        )
    
    @classmethod
    def for_gpu_rtx(cls) -> WhisperConfig:
        """Optimized config for RTX GPUs (A4000/A5000 or consumer RTX cards)."""
        return cls(
            model_name=WhisperModel.LARGE,
            device="cuda",
            compute_type=ComputeType.FLOAT16,
            beam_size=5,
            best_of=5,
            num_workers=4,
            fp16=True,
        )
    
    @classmethod
    def from_env(cls) -> WhisperConfig:
        """Load config from environment variables with sensible defaults."""
        model_str = os.getenv("WHISPER_MODEL", "medium").lower()
        device = os.getenv("WHISPER_DEVICE", "cpu").lower()
        
        try:
            model = WhisperModel(model_str)
        except ValueError:
            model = WhisperModel.MEDIUM
        
        config = cls()
        config.model_name = model
        config.device = device
        
        # Check if CUDA is available
        if device == "cuda":
            try:
                import torch
                if not torch.cuda.is_available():
                    config.device = "cpu"
            except ImportError:
                config.device = "cpu"
        
        return config


# Default configuration - can be overridden
DEFAULT_CONFIG = WhisperConfig.from_env()


def get_whisper_config() -> WhisperConfig:
    """Get the current Whisper configuration."""
    return DEFAULT_CONFIG


def set_whisper_config(config: WhisperConfig) -> None:
    """Override the Whisper configuration."""
    global DEFAULT_CONFIG
    DEFAULT_CONFIG = config
