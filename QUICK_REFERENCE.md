# Historical - see ARCHITECTURE.md

# Quick Reference - AI Tally Voice Integration

## 🚀 Get Started in 3 Steps

### 1. Backend (5 min)
```bash
cd backend
pip install -r requirements.txt
python app.py  # Runs on http://localhost:5000
```

### 2. Flutter (3 min)
```bash
cd frontend/flutter
flutter pub get
flutter run
```

### 3. Test (2 min)
- Open app → Voice Assistant screen
- Click microphone → Speak: "add 20 coke bottles"
- Verify transcript and response

## 📋 What Was Implemented

### Backend Services
| File | Purpose |
|------|---------|
| `whisper_config.py` | Whisper model configuration |
| `services/stt_service.py` | Faster-Whisper speech-to-text |
| `services/audio_processor.py` | Audio format conversion |
| `services/transcription_queue.py` | Async transcription queue |
| `services/voice_workflow.py` | Complete audio→response pipeline |
| `services/voice_command_handler.py` | Business command handlers |
| `services/voice_workflow_steps.py` | Multi-step conversation flows |

### Flask API Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/voice/transcribe` | POST | Audio → Text (Faster-Whisper) |
| `/api/voice/process` | POST | Text → Action → Response |
| `/api/voice/models` | GET | Model information |

### Flutter Services
| File | Purpose |
|------|---------|
| `services/audio_recorder_service.dart` | Local audio recording |
| `services/transcription_service.dart` | Backend integration |
| `services/tts_service.dart` | Text-to-speech (flutter_tts) |

### Flutter UI
| File | Purpose |
|------|---------|
| `screens/voice_assistant.dart` | Complete voice UI screen |

## 🗣️ Voice Commands

### Inventory
```
"add 20 coke bottles" → Add 20 Coke
"update maggi to 50" → Set Maggi quantity to 50
"search parle-g" → Find Parle-G stock
"low stock" → Show low items
```

### Invoices
```
"create invoice"
→ "Who's the customer?" 
→ "ABC Traders"
→ "What items?"
→ "5 coke and 2 maggi"
→ "Total ₹850. Confirm?"
```

### Payments
```
"record payment from ABC" → Record payment
"show pending dues" → Show owed amounts
"overdue customers" → Show late payers
```

### Dashboard
```
"today sales" → Show today's revenue
"top products" → Best selling items
"inventory summary" → Total value
"sales summary" → Sales analytics
```

## 🔧 Configuration

### CPU System
```bash
export WHISPER_MODEL=medium
export WHISPER_DEVICE=cpu
python app.py
```

### GPU System
```bash
export WHISPER_MODEL=large-v3
export WHISPER_DEVICE=cuda
python app.py
```

### Low Memory
```python
# In app.py
from whisper_config import WhisperConfig
config = WhisperConfig.for_cpu_only()
```

## 📊 Performance Guide

| Hardware | Model | Speed | Accuracy |
|----------|-------|-------|----------|
| Basic laptop | small | ⚡⚡⚡ | ⭐⭐⭐⭐ |
| Mid PC | medium | ⚡⚡ | ⭐⭐⭐⭐⭐ |
| RTX GPU | large-v3 | ⚡ | ⭐⭐⭐⭐⭐ |

## 📱 Flutter Setup

### Dependencies Added
```yaml
record: ^5.1.0                    # Audio recording
path_provider: ^2.1.0             # File storage
permission_handler: ^11.4.4       # Permissions
```

### Permissions Required
- `RECORD_AUDIO` - Microphone access
- Already in `AndroidManifest.xml`

## 🧪 Testing

```bash
# Run test suite
cd backend
pytest tests/test_voice_integration.py -v

# Test transcription
curl -X POST http://localhost:5000/api/voice/transcribe \
  -F "audio=@recording.wav"

# Test processing
curl -X POST http://localhost:5000/api/voice/process \
  -H "Content-Type: application/json" \
  -d '{"transcript": "add 20 coke"}'
```

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| "faster_whisper not found" | `pip install faster-whisper` |
| "FFmpeg not found" | Install FFmpeg, add to PATH |
| "CUDA not available" | `pip install torch --index-url https://download.pytorch.org/whl/cu118` |
| "Audio too short" | Use audio ≥ 1 second |
| "Flutter symlink error" | `flutter clean && flutter pub get` |

## 📚 Documentation

| File | Contents |
|------|----------|
| `VOICE_INTEGRATION_GUIDE.md` | Complete setup guide |
| `IMPLEMENTATION_SUMMARY.md` | Architecture & checklist |
| `tests/test_voice_integration.py` | Test suite |

## 🔑 Key Features

✅ **Offline** - No cloud APIs, pure local processing
✅ **Fast** - Async transcription queue
✅ **Accurate** - Faster-Whisper (92-99% accuracy)
✅ **Conversational** - Multi-step workflows
✅ **Indian Optimized** - Rupees, local products, Indian English
✅ **Production Ready** - Error handling, logging, tests
✅ **Flexible** - CPU/GPU configurations

## 🎯 Next Steps

1. Run backend: `python app.py`
2. Run Flutter: `flutter run`
3. Test voice commands
4. Monitor logs for optimization
5. Customize entity parser for your products
6. Extend workflows for your use cases

## 💡 Tips

- Speak clearly and at normal pace
- Use standard product names
- Say "rupees" or "₹" for amounts
- Multi-step workflows pause for your response
- All processing happens offline
- Models download on first use (~1GB)

## 📞 Support

- Check `VOICE_INTEGRATION_GUIDE.md` for detailed setup
- Review `IMPLEMENTATION_SUMMARY.md` for architecture
- Run tests to verify installation
- Check Flask console for processing logs

---

**Status**: ✅ Production Ready
**Last Updated**: May 2026
**Version**: 1.0 (Faster-Whisper Integration)
