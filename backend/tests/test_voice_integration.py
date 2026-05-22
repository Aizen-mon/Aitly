"""Integration tests for the current voice stack and workflow engine."""

from __future__ import annotations

from types import SimpleNamespace

from app import create_app
from services.audio_processor import AudioProcessor
from services.entity_parser import EntityParser
from services.voice_service import VoiceService
from whisper_config import WhisperConfig, WhisperModel


class DummyNLP:
    def parse(self, transcript, product_names=None, customer_names=None):
        return {
            "intent": "create_invoice" if "invoice" in transcript.lower() else "general",
            "confidence": 0.9,
            "entities": {"items": []},
        }


class DummyWorkflow:
    def __init__(self):
        self.calls = []
        self.builder = SimpleNamespace()

    def process(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "intent": kwargs["parsed"]["intent"],
            "message": "processed",
            "speech": "processed",
            "details": kwargs["parsed"].get("entities", {}),
        }


def test_audio_processor_validation():
    is_valid, _ = AudioProcessor.validate_audio(b"x" * 50)
    assert not is_valid

    wav_header = b"RIFF\x00\x00\x00\x00WAVE"
    assert AudioProcessor.detect_audio_format(wav_header) == "wav"


def test_whisper_config_from_env(monkeypatch):
    monkeypatch.setenv("WHISPER_MODEL", "small")
    monkeypatch.setenv("WHISPER_DEVICE", "cpu")
    config = WhisperConfig.from_env()
    assert config.model_name == WhisperModel.SMALL
    assert config.device == "cpu"


def test_voice_service_routes_to_workflow():
    workflow = DummyWorkflow()
    voice = VoiceService(repos=None, nlp_service=DummyNLP(), workflow_engine=workflow)

    result = voice.process(
        session_id="session-1",
        transcript="create invoice for ABC Traders",
        product_names=["Coke", "Maggi"],
        customer_names=["ABC Traders"],
    )

    assert workflow.calls
    assert result["intent"] == "create_invoice"
    assert result["session_id"] == "session-1"
    assert result["transcript"] == "create invoice for ABC Traders"


def test_entity_parser_extracts_demo_products():
    parser = EntityParser()
    entities = parser.extract("add 5 Coke and 2 Maggi", product_names=["Coke", "Maggi"])
    assert entities


def test_create_app_smoke(monkeypatch):
    monkeypatch.setenv("FLASK_DEBUG", "false")
    app = create_app()
    routes = {str(rule) for rule in app.url_map.iter_rules()}
    assert "/api/parse" in routes
    assert "/api/voice/transcribe" in routes
