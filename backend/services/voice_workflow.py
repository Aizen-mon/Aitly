"""Orchestrate complete voice workflow from audio to response."""

from __future__ import annotations

import json
import logging
from typing import Dict, Optional
from datetime import datetime

from services.stt_service import get_stt_service
from services.audio_processor import AudioProcessor

logger = logging.getLogger(__name__)


class VoiceWorkflowEngine:
    """
    Complete voice assistant workflow:
    Audio → Transcription → Intent Detection → Action Execution → Response
    """
    
    def __init__(
        self,
        stt_service=None,
        nlp_service=None,
        workflow_engine=None,
        response_builder=None,
    ):
        """
        Initialize voice workflow.
        
        Args:
            stt_service: Speech-to-text service
            nlp_service: NLP/Intent detection service
            workflow_engine: Business action executor
            response_builder: Response formatter
        """
        self.stt = stt_service or get_stt_service()
        self.nlp = nlp_service
        self.workflow = workflow_engine
        self.response_builder = response_builder
    
    def process_audio(
        self,
        audio_data: bytes,
        session_id: str,
        language: Optional[str] = None,
        product_names: Optional[list[str]] = None,
        customer_names: Optional[list[str]] = None,
    ) -> Dict[str, object]:
        """
        Complete voice workflow processing.
        
        Args:
            audio_data: Raw audio bytes
            session_id: User session ID
            language: Language code (e.g., 'en', 'hi')
            product_names: Known product names for entity extraction
            customer_names: Known customer names for entity extraction
            
        Returns:
            Complete workflow result with transcript and action response
        """
        result = {
            "status": "processing",
            "session_id": session_id,
            "workflow_steps": {},
            "timestamp": datetime.now().isoformat(),
        }
        
        try:
            # STEP 1: Validate and process audio
            logger.info(f"[{session_id}] Starting voice workflow")
            
            is_valid, validation_msg = AudioProcessor.validate_audio(audio_data)
            if not is_valid:
                result["status"] = "error"
                result["error"] = f"Invalid audio: {validation_msg}"
                result["workflow_steps"]["validation"] = {"success": False, "error": validation_msg}
                return result
            
            result["workflow_steps"]["validation"] = {"success": True}
            
            # STEP 2: Convert to WAV format
            try:
                wav_audio = AudioProcessor.convert_to_wav(audio_data, input_format="auto")
                result["workflow_steps"]["audio_conversion"] = {
                    "success": True,
                    "format": "wav",
                    "size_bytes": len(wav_audio),
                }
            except Exception as e:
                result["status"] = "error"
                result["error"] = f"Audio conversion failed: {str(e)}"
                result["workflow_steps"]["audio_conversion"] = {
                    "success": False,
                    "error": str(e),
                }
                return result
            
            # STEP 3: Transcribe audio to text
            try:
                transcription_result = self.stt.transcribe(
                    wav_audio,
                    language=language,
                )
                
                transcript = transcription_result.get("text", "").strip()
                
                if not transcript:
                    result["status"] = "error"
                    result["error"] = "No speech detected in audio"
                    result["workflow_steps"]["transcription"] = {
                        "success": False,
                        "error": "No speech detected",
                    }
                    return result
                
                result["workflow_steps"]["transcription"] = {
                    "success": True,
                    "text": transcript,
                    "confidence": transcription_result.get("confidence", 0),
                    "language": transcription_result.get("language"),
                    "duration": transcription_result.get("duration_seconds", 0),
                }
                
                logger.info(f"[{session_id}] Transcribed: {transcript[:80]}")
            
            except Exception as e:
                result["status"] = "error"
                result["error"] = f"Transcription failed: {str(e)}"
                result["workflow_steps"]["transcription"] = {
                    "success": False,
                    "error": str(e),
                }
                return result
            
            # STEP 4: Detect intent and extract entities
            try:
                if self.nlp:
                    intent_result = self.nlp.parse(
                        transcript,
                        product_names=product_names,
                        customer_names=customer_names,
                    )
                    
                    intent = intent_result.get("intent", "general")
                    confidence = intent_result.get("confidence", 0)
                    entities = intent_result.get("entities", {})
                    
                    result["workflow_steps"]["intent_detection"] = {
                        "success": True,
                        "intent": intent,
                        "confidence": confidence,
                        "entities": entities,
                    }
                    
                    logger.info(f"[{session_id}] Intent: {intent} (confidence: {confidence:.2f})")
                else:
                    intent = "general"
                    confidence = 0.0
                    entities = {}
                    result["workflow_steps"]["intent_detection"] = {
                        "success": False,
                        "error": "NLP service not available",
                    }
            
            except Exception as e:
                intent = "general"
                confidence = 0.0
                entities = {}
                result["workflow_steps"]["intent_detection"] = {
                    "success": False,
                    "error": str(e),
                }
                logger.error(f"[{session_id}] Intent detection failed: {e}")
            
            # STEP 5: Execute business action via workflow
            try:
                if self.workflow:
                    action_result = self.workflow.process(
                        session_id=session_id,
                        text=transcript,
                        parsed={
                            "intent": intent,
                            "confidence": confidence,
                            "entities": entities,
                            "transcript": transcript,
                        },
                        product_names=product_names or [],
                        customer_names=customer_names or [],
                    )
                    
                    result["workflow_steps"]["action_execution"] = {
                        "success": True,
                        "intent": action_result.get("intent"),
                        "action_type": action_result.get("action_type"),
                    }
                    
                    # Merge action result into final response
                    result.update(action_result)
                    result["status"] = "success"
                else:
                    result["workflow_steps"]["action_execution"] = {
                        "success": False,
                        "error": "Workflow engine not available",
                    }
            
            except Exception as e:
                result["workflow_steps"]["action_execution"] = {
                    "success": False,
                    "error": str(e),
                }
                logger.error(f"[{session_id}] Action execution failed: {e}")
                result["status"] = "error"
                result["error"] = str(e)
                return result
            
            # STEP 6: Format response
            result["transcript"] = transcript
            result["intent"] = intent
            result["confidence"] = confidence
            result["entities"] = entities
            result["workflow_status"] = "completed"
            
            logger.info(f"[{session_id}] Voice workflow completed successfully")
            
            return result
        
        except Exception as e:
            logger.error(f"[{session_id}] Unexpected error in voice workflow: {e}")
            result["status"] = "error"
            result["error"] = str(e)
            return result
    
    def process_audio_with_context(
        self,
        audio_data: bytes,
        session_id: str,
        previous_context: Optional[Dict[str, object]] = None,
        **kwargs,
    ) -> Dict[str, object]:
        """
        Process audio with conversation context for multi-turn flows.
        
        Args:
            audio_data: Raw audio bytes
            session_id: Session ID
            previous_context: Context from previous turn
            **kwargs: Additional arguments
            
        Returns:
            Workflow result with context-aware processing
        """
        result = self.process_audio(
            audio_data,
            session_id,
            product_names=kwargs.get("product_names"),
            customer_names=kwargs.get("customer_names"),
            language=kwargs.get("language"),
        )
        
        # Add context information
        if previous_context:
            result["previous_context"] = previous_context
            result["is_continuation"] = True
        
        return result
    
    def get_workflow_status(self, session_id: str) -> Dict[str, object]:
        """Get the status of an ongoing workflow."""
        return {
            "session_id": session_id,
            "status": "available",
            "available_intents": [
                "today_sales", "low_stock", "pending_dues", "create_invoice",
                "record_payment", "add_inventory", "search_inventory"
            ],
        }
