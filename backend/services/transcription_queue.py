"""Asynchronous transcription queue for background speech-to-text processing."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TranscriptionStatus(str, Enum):
    """Status of a transcription job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TranscriptionJob:
    """Represents a transcription job."""
    job_id: str
    audio_data: bytes
    language: Optional[str] = None
    status: TranscriptionStatus = TranscriptionStatus.PENDING
    transcript: str = ""
    confidence: float = 0.0
    error: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, object] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, object]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "transcript": self.transcript,
            "confidence": self.confidence,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }


class TranscriptionQueue:
    """
    Asynchronous queue for processing speech-to-text jobs.
    Allows non-blocking transcription in the background.
    """
    
    def __init__(self, stt_service=None, max_workers: int = 2):
        """
        Initialize the transcription queue.
        
        Args:
            stt_service: STT service instance
            max_workers: Number of concurrent transcription workers
        """
        self.stt_service = stt_service
        self.max_workers = max_workers
        self.jobs: Dict[str, TranscriptionJob] = {}
        self.callbacks: Dict[str, list[Callable]] = {}
        self._queue: asyncio.Queue = None
        self._workers = []
        self._running = False
    
    async def start(self) -> None:
        """Start the queue and workers."""
        if self._running:
            return
        
        self._running = True
        self._queue = asyncio.Queue()
        
        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)
        
        logger.info(f"Transcription queue started with {self.max_workers} workers")
    
    async def stop(self) -> None:
        """Stop the queue and cancel all workers."""
        self._running = False
        
        if self._queue:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        
        for worker in self._workers:
            if not worker.done():
                worker.cancel()
                try:
                    await worker
                except asyncio.CancelledError:
                    pass
        
        self._workers.clear()
        logger.info("Transcription queue stopped")
    
    async def submit(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
        metadata: Optional[Dict[str, object]] = None,
        callback: Optional[Callable] = None,
    ) -> str:
        """
        Submit audio for transcription.
        
        Args:
            audio_data: Audio bytes
            language: Language code
            metadata: Additional metadata
            callback: Optional callback function on completion
            
        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        job = TranscriptionJob(
            job_id=job_id,
            audio_data=audio_data,
            language=language,
            metadata=metadata or {},
        )
        
        self.jobs[job_id] = job
        
        if callback:
            if job_id not in self.callbacks:
                self.callbacks[job_id] = []
            self.callbacks[job_id].append(callback)
        
        if self._queue:
            await self._queue.put(job_id)
        
        logger.info(f"Submitted transcription job: {job_id}")
        return job_id
    
    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine for processing jobs."""
        logger.info(f"Transcription worker {worker_id} started")
        
        while self._running:
            try:
                # Get next job
                job_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                
                if job_id not in self.jobs:
                    continue
                
                job = self.jobs[job_id]
                job.status = TranscriptionStatus.PROCESSING
                
                # Transcribe
                if self.stt_service:
                    try:
                        result = self.stt_service.transcribe(
                            job.audio_data,
                            language=job.language,
                        )
                        
                        job.transcript = result.get("text", "")
                        job.confidence = result.get("confidence", 0.0)
                        job.status = TranscriptionStatus.COMPLETED
                        job.completed_at = datetime.now()
                        
                        logger.info(f"Job {job_id} completed: {job.transcript[:50]}...")
                    
                    except Exception as e:
                        job.error = str(e)
                        job.status = TranscriptionStatus.FAILED
                        job.completed_at = datetime.now()
                        logger.error(f"Job {job_id} failed: {e}")
                else:
                    job.error = "STT service not initialized"
                    job.status = TranscriptionStatus.FAILED
                    job.completed_at = datetime.now()
                    logger.error(f"Job {job_id}: STT service not initialized")
                
                # Call callbacks
                if job_id in self.callbacks:
                    for callback in self.callbacks[job_id]:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(job)
                            else:
                                callback(job)
                        except Exception as e:
                            logger.error(f"Callback error for job {job_id}: {e}")
                    
                    del self.callbacks[job_id]
            
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
    
    def get_job(self, job_id: str) -> Optional[TranscriptionJob]:
        """Get job by ID."""
        return self.jobs.get(job_id)
    
    def get_job_status(self, job_id: str) -> Optional[str]:
        """Get job status."""
        job = self.jobs.get(job_id)
        return job.status.value if job else None
    
    def is_complete(self, job_id: str) -> bool:
        """Check if job is complete."""
        job = self.jobs.get(job_id)
        return job and job.status in (TranscriptionStatus.COMPLETED, TranscriptionStatus.FAILED)
    
    def get_result(self, job_id: str) -> Optional[Dict[str, object]]:
        """Get job result if complete."""
        job = self.jobs.get(job_id)
        if not job or not self.is_complete(job_id):
            return None
        
        return {
            "text": job.transcript,
            "confidence": job.confidence,
            "status": job.status.value,
            "error": job.error,
        }
    
    def cleanup_old_jobs(self, max_age_minutes: int = 60) -> int:
        """Remove old completed jobs to free memory."""
        import time
        now = datetime.now()
        current_time = time.time()
        removed = 0
        
        job_ids_to_remove = []
        for job_id, job in self.jobs.items():
            if job.completed_at:
                age_minutes = (now - job.completed_at).total_seconds() / 60
                if age_minutes > max_age_minutes:
                    job_ids_to_remove.append(job_id)
        
        for job_id in job_ids_to_remove:
            del self.jobs[job_id]
            removed += 1
        
        if removed > 0:
            logger.info(f"Cleaned up {removed} old transcription jobs")
        
        return removed


# Global queue instance
_queue: Optional[TranscriptionQueue] = None


def get_transcription_queue(stt_service=None) -> TranscriptionQueue:
    """Get or create the global transcription queue."""
    global _queue
    if _queue is None:
        _queue = TranscriptionQueue(stt_service)
    return _queue


async def submit_transcription(
    audio_data: bytes,
    language: Optional[str] = None,
    metadata: Optional[Dict[str, object]] = None,
) -> str:
    """Submit audio for async transcription."""
    queue = get_transcription_queue()
    return await queue.submit(audio_data, language, metadata)
