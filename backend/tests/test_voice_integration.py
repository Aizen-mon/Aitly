"""
Test suite for Faster-Whisper integration
Run: python -m pytest backend/tests/test_voice_integration.py -v
"""

import pytest
import os
from datetime import datetime
from services.stt_service import get_stt_service, initialize_stt
from services.audio_processor import AudioProcessor
from services.transcription_queue import TranscriptionQueue, TranscriptionJob, TranscriptionStatus
from services.voice_command_handler import VoiceCommandHandler
from services.voice_workflow_steps import MultiStepVoiceWorkflow, VoiceWorkflowContext
from whisper_config import WhisperConfig, WhisperModel


class TestAudioProcessor:
    """Test audio processing utilities."""
    
    def test_validate_audio(self):
        """Test audio validation."""
        # Test too small audio
        is_valid, msg = AudioProcessor.validate_audio(b"x" * 50)
        assert not is_valid
        
    def test_audio_format_detection(self):
        """Test audio format detection from magic bytes."""
        # WAV magic bytes
        wav_header = b"RIFF\x00\x00\x00\x00WAVE"
        fmt = AudioProcessor.detect_audio_format(wav_header)
        assert fmt == "wav"
        
        # MP3 magic bytes
        mp3_header = b"\xff\xfb"
        fmt = AudioProcessor.detect_audio_format(mp3_header)
        assert fmt == "mp3"


class TestWhisperConfig:
    """Test Whisper configuration."""
    
    def test_cpu_only_config(self):
        """Test CPU-only configuration."""
        config = WhisperConfig.for_cpu_only()
        assert config.device == "cpu"
        assert config.model_name == WhisperModel.MEDIUM
        assert config.compute_type.value == "float32"
    
    def test_gpu_config(self):
        """Test GPU configuration."""
        config = WhisperConfig.for_gpu_rtx()
        assert config.device == "cuda"
        assert config.model_name == WhisperModel.LARGE
    
    def test_config_from_env(self):
        """Test loading config from environment."""
        os.environ["WHISPER_MODEL"] = "small"
        os.environ["WHISPER_DEVICE"] = "cpu"
        
        config = WhisperConfig.from_env()
        assert config.model_name == WhisperModel.SMALL
        assert config.device == "cpu"


class TestSTTService:
    """Test Speech-to-Text service."""
    
    @pytest.mark.slow
    def test_stt_initialization(self):
        """Test STT service initialization."""
        config = WhisperConfig.for_cpu_only()
        stt = initialize_stt(config)
        
        assert stt is not None
        model_info = stt.get_model_info()
        assert model_info["model"] == "medium"
        assert model_info["device"] == "cpu"
    
    @pytest.mark.slow
    def test_model_info(self):
        """Test getting model information."""
        stt = get_stt_service()
        info = stt.get_model_info()
        
        assert "model" in info
        assert "device" in info
        assert "compute_type" in info


class TestTranscriptionQueue:
    """Test asynchronous transcription queue."""
    
    @pytest.mark.asyncio
    async def test_queue_initialization(self):
        """Test queue initialization."""
        queue = TranscriptionQueue(max_workers=2)
        await queue.start()
        
        assert queue._queue is not None
        assert len(queue._workers) == 2
        
        await queue.stop()
    
    @pytest.mark.asyncio
    async def test_job_submission(self):
        """Test submitting a transcription job."""
        queue = TranscriptionQueue(max_workers=1)
        await queue.start()
        
        job_id = await queue.submit(
            b"test_audio_data",
            language="en",
            metadata={"test": True},
        )
        
        assert job_id in queue.jobs
        assert queue.jobs[job_id].status.value == "pending"
        
        await queue.stop()
    
    @pytest.mark.asyncio
    async def test_queue_cleanup(self):
        """Test cleanup of old jobs."""
        queue = TranscriptionQueue()
        
        # Add a completed job
        job = TranscriptionJob(
            job_id="test_id",
            audio_data=b"test",
            status=TranscriptionStatus.COMPLETED,
        )
        job.completed_at = datetime.now()
        queue.jobs["test_id"] = job
        
        # Cleanup jobs older than 0 minutes (should remove)
        removed = queue.cleanup_old_jobs(max_age_minutes=0)
        assert removed == 1
        assert "test_id" not in queue.jobs


class TestEntityExtraction:
    """Test voice entity extraction."""
    
    def test_extract_quantity_simple(self):
        """Test simple quantity extraction."""
        from services.entity_parser import EntityParser
        parser = EntityParser()
        
        # Test: "add 20 coke"
        qty = parser._extract_quantity("add 20 coke bottles")
        assert qty == 20
    
    def test_extract_quantity_indian_pattern(self):
        """Test Indian English quantity patterns."""
        from services.entity_parser import EntityParser
        parser = EntityParser()
        
        # Test: "5 only" (common in Indian English)
        qty = parser._extract_quantity("5 only maggi")
        assert qty == 5
    
    def test_extract_amount_indian_currency(self):
        """Test Indian currency amount extraction."""
        from services.entity_parser import EntityParser
        parser = EntityParser()
        
        # Test: "₹850"
        amount = parser._extract_amount("payment of ₹850 please")
        assert amount == 850.0
        
        # Test: "850 rupees"
        amount = parser._extract_amount("total 850 rupees only")
        assert amount == 850.0
    
    def test_extract_line_items(self):
        """Test line item extraction."""
        from services.entity_parser import EntityParser
        parser = EntityParser()
        
        # Test: "5 coke and 2 maggi"
        items = parser._extract_line_items(
            "add 5 coke and 2 maggi",
            product_names=["Coke", "Maggi"]
        )
        assert len(items) > 0
        assert any(item["name"].lower() == "coke" for item in items)


class TestVoiceCommandHandler:
    """Test voice command handlers."""
    
    def test_inventory_command_structure(self):
        """Test command handler structure."""
        handler = VoiceCommandHandler()
        
        # Test that handlers are callable
        assert callable(handler.handle_inventory_command)
        assert callable(handler.handle_invoice_command)
        assert callable(handler.handle_payment_command)
        assert callable(handler.handle_dashboard_command)
    
    def test_clarification_request(self):
        """Test clarification handling."""
        handler = VoiceCommandHandler()
        
        result = handler.handle_inventory_command(
            "add_inventory",
            {},  # No entities
        )
        
        assert result["status"] == "clarify"
        assert "requires" in result


class TestMultiStepWorkflow:
    """Test multi-step voice workflows."""
    
    def test_workflow_initialization(self):
        """Test workflow context initialization."""
        context = VoiceWorkflowContext("session1", "create_invoice")
        
        assert context.session_id == "session1"
        assert context.workflow_type == "create_invoice"
        assert context.current_step == 0
        assert not context.completed
    
    def test_workflow_step_management(self):
        """Test managing workflow steps."""
        context = VoiceWorkflowContext("session1", "create_invoice")
        
        context.add_step(0, "Who is the customer?", ["customer_name"])
        context.add_step(1, "What items?", ["items"])
        
        assert 0 in context.steps
        assert 1 in context.steps
        
        # Set step active
        context.set_step_active(0)
        assert context.current_step == 0
        assert context.steps[0]["status"] == "active"
    
    def test_workflow_step_completion(self):
        """Test completing a workflow step."""
        context = VoiceWorkflowContext("session1", "create_invoice")
        context.add_step(0, "Customer?", ["customer_name"])
        context.set_step_active(0)
        
        # Complete step
        context.set_step_completed(
            0,
            "ABC Traders",
            {"customer_name": "ABC Traders"}
        )
        
        assert context.steps[0]["status"] == "completed"
        assert context.steps[0]["response"] == "ABC Traders"
        assert context.data["customer_name"] == "ABC Traders"
        assert len(context.history) == 1
    
    def test_workflow_templates(self):
        """Test workflow template structure."""
        engine = MultiStepVoiceWorkflow()
        workflows = engine.get_all_workflows()
        
        assert "create_invoice" in workflows
        assert "record_payment" in workflows
        assert "add_inventory" in workflows
        
        for workflow_name, info in workflows.items():
            assert "name" in info
            assert "steps" in info
            assert info["steps"] > 0


class TestVoiceIntegration:
    """Integration tests for complete voice workflow."""
    
    def test_workflow_structure(self):
        """Test complete workflow structure."""
        from services.voice_workflow import VoiceWorkflowEngine
        
        # Initialize with stubs
        engine = VoiceWorkflowEngine(
            stt_service=None,  # Would be real STT service
            nlp_service=None,  # Would be real NLP service
            workflow_engine=None,
        )
        
        assert engine.stt is not None  # Gets default
    
    def test_intent_detection_flow(self):
        """Test intent detection in workflow."""
        from intent_service import IntentService
        
        intent_service = IntentService()
        
        # Test inventory intent
        result = intent_service.detect("add 20 coke bottles")
        assert result["intent"] == "add_inventory"
        assert result["confidence"] > 0.5
        
        # Test sales intent
        result = intent_service.detect("today sales")
        assert result["intent"] == "today_sales"
        
        # Test payment intent
        result = intent_service.detect("record payment from abc traders")
        assert result["intent"] == "record_payment"


# Performance benchmarks
class TestPerformance:
    """Performance and optimization tests."""
    
    @pytest.mark.benchmark
    def test_entity_extraction_speed(self, benchmark):
        """Benchmark entity extraction speed."""
        from services.entity_parser import EntityParser
        parser = EntityParser()
        
        text = "add 20 coke bottles for customer ABC Traders for ₹850"
        result = benchmark(
            parser.extract,
            text,
            product_names=["Coke", "Maggi"],
            customer_names=["ABC Traders"],
        )
        
        assert result["quantity"] == 20


# Example test data
SAMPLE_VOICE_COMMANDS = [
    ("add 20 coke bottles", "add_inventory"),
    ("update maggi quantity to 50", "update_inventory"),
    ("show low stock items", "low_stock"),
    ("create invoice", "create_invoice"),
    ("record payment from abc traders", "record_payment"),
    ("today's sales", "today_sales"),
    ("top products", "top_products"),
    ("inventory summary", "inventory_summary"),
]


@pytest.mark.parametrize("command,expected_intent", SAMPLE_VOICE_COMMANDS)
def test_intent_detection_commands(command, expected_intent):
    """Test intent detection for sample commands."""
    from intent_service import IntentService
    
    service = IntentService()
    result = service.detect(command)
    assert result["intent"] == expected_intent


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
