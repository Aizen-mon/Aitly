import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

import '../services/audio_recorder_service.dart';
import '../services/transcription_service.dart';

/// Voice input for the assistant.
/// - Web: browser speech recognition (no path_provider / no WAV files).
/// - Desktop & mobile: record WAV → backend Faster-Whisper.
class SimpleVoiceControl extends StatefulWidget {
  final ValueChanged<String> onFinalTranscript;
  final ValueChanged<bool>? onListeningChanged;
  final ValueChanged<String>? onError;

  const SimpleVoiceControl({
    required this.onFinalTranscript,
    this.onListeningChanged,
    this.onError,
    Key? key,
  }) : super(key: key);

  @override
  State<SimpleVoiceControl> createState() {
    if (kIsWeb) {
      return _WebSpeechVoiceControlState();
    }
    return _WhisperVoiceControlState();
  }
}

abstract class _VoiceControlStateBase extends State<SimpleVoiceControl> {
  bool isListening = false;
  bool isBusy = false;
  bool initializing = true;
  String statusText = 'Checking microphone...';
  String liveTranscript = '';
  String? errorText;

  void handleError(String message) {
    if (!mounted) return;
    setState(() {
      isListening = false;
      isBusy = false;
      statusText = message;
      errorText = message;
    });
    widget.onListeningChanged?.call(false);
    widget.onError?.call(message);
  }

  void handleSuccess(String transcript) {
    if (!mounted) return;
    setState(() {
      isListening = false;
      isBusy = false;
      statusText = 'Transcript ready';
      liveTranscript = transcript;
      errorText = null;
    });
    widget.onListeningChanged?.call(false);
    widget.onFinalTranscript(transcript);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isRecording = isListening;
    final isTranscribing = isBusy && !isListening;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: theme.colorScheme.outlineVariant),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: isRecording
                      ? Colors.red.shade100
                      : (isTranscribing ? Colors.orange.shade100 : Colors.blue.shade50),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  isRecording
                      ? Icons.mic
                      : (isTranscribing ? Icons.autorenew : Icons.mic_none),
                  color: isRecording
                      ? Colors.red.shade700
                      : (isTranscribing ? Colors.orange.shade700 : Colors.blue.shade700),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      isRecording
                          ? 'Listening now'
                          : (isTranscribing ? 'Transcribing' : 'Voice input'),
                      style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      statusText,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: errorText == null ? Colors.black54 : Colors.red.shade700,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              FilledButton.icon(
                onPressed: initializing || isBusy ? null : onTalkPressed,
                icon: Icon(isRecording ? Icons.stop : Icons.mic),
                label: Text(isRecording ? 'Stop' : 'Talk'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            kIsWeb
                ? 'Web uses browser speech recognition. Desktop/mobile use offline Whisper.'
                : 'Hold the mic to talk, or tap it to toggle recording.',
            style: theme.textTheme.bodySmall?.copyWith(color: Colors.black45),
          ),
          if (liveTranscript.isNotEmpty) ...[
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: theme.colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Text(liveTranscript, style: theme.textTheme.bodyMedium),
            ),
          ],
        ],
      ),
    );
  }

  void onTalkPressed();
}

/// Chrome / Flutter web — browser STT only (avoids path_provider).
class _WebSpeechVoiceControlState extends _VoiceControlStateBase {
  final stt.SpeechToText _speech = stt.SpeechToText();
  String _partial = '';

  @override
  void initState() {
    super.initState();
    _initSpeech();
  }

  Future<void> _initSpeech() async {
    final available = await _speech.initialize(
      onError: (error) => handleError('Mic error: ${error.errorMsg}'),
      onStatus: (status) {
        if ((status == 'done' || status == 'notListening') && isListening) {
          _finishListening();
        }
      },
    );
    if (!mounted) return;
    setState(() {
      initializing = false;
      statusText = available
          ? 'Tap Talk and speak (browser recognition)'
          : 'Microphone unavailable in this browser';
      errorText = available ? null : 'Microphone unavailable in this browser';
    });
  }

  @override
  void onTalkPressed() {
    if (isListening) {
      _speech.stop();
      _finishListening();
      return;
    }
    _startListening();
  }

  Future<void> _startListening() async {
    if (initializing || isBusy) return;

    final available = _speech.isAvailable;
    if (!available) {
      handleError('Speech recognition is not available in this browser');
      return;
    }

    setState(() {
      isListening = true;
      isBusy = false;
      liveTranscript = '';
      _partial = '';
      errorText = null;
      statusText = 'Listening...';
    });
    widget.onListeningChanged?.call(true);

    await _speech.listen(
      onResult: (result) {
        if (!mounted) return;
        setState(() {
          _partial = result.recognizedWords;
          liveTranscript = _partial;
        });
        if (result.finalResult) {
          _finishListening();
        }
      },
      listenFor: const Duration(seconds: 30),
      pauseFor: const Duration(seconds: 3),
      localeId: 'en_IN',
    );
  }

  void _finishListening() {
    final text = _partial.trim();
    if (text.isEmpty) {
      handleError('No speech detected. Try again.');
      return;
    }
    handleSuccess(text);
  }

  @override
  void dispose() {
    _speech.stop();
    super.dispose();
  }
}

/// Windows / macOS / Linux / Android / iOS — WAV + Faster-Whisper backend.
class _WhisperVoiceControlState extends _VoiceControlStateBase {
  late final AudioRecorderService _recorder;
  late final TranscriptionService _transcriptionService;

  @override
  void initState() {
    super.initState();
    _recorder = AudioRecorderService();
    _transcriptionService = TranscriptionService();
    _initRecorder();
  }

  Future<void> _initRecorder() async {
    final available = await _recorder.hasMicrophonePermission();
    if (!mounted) return;
    setState(() {
      initializing = false;
      statusText = available ? 'Hold or tap the mic to record' : 'Microphone permission is required';
      errorText = available ? null : 'Microphone permission is required';
    });
  }

  @override
  void onTalkPressed() {
    if (isListening) {
      _stopRecording();
    } else {
      _startRecording();
    }
  }

  Future<void> _startRecording() async {
    if (isListening || isBusy || initializing) return;

    final started = await _recorder.startRecording();
    if (!started) {
      handleError(_recorder.getLastError() ?? 'Could not start recording');
      return;
    }

    if (!mounted) return;
    setState(() {
      isListening = true;
      liveTranscript = '';
      errorText = null;
      statusText = 'Recording...';
    });
    widget.onListeningChanged?.call(true);
  }

  Future<void> _stopRecording() async {
    if (!isListening || isBusy) return;

    setState(() {
      isListening = false;
      isBusy = true;
      statusText = 'Transcribing...';
    });
    widget.onListeningChanged?.call(false);

    final recordingPath = await _recorder.stopRecording();
    final audioBytes = await _recorder.getRecordingBytes(recordingPath);
    if (audioBytes == null || audioBytes.isEmpty) {
      handleError(_recorder.getLastError() ?? 'Recording failed');
      return;
    }

    final result = await _transcriptionService.transcribeBytes(audioBytes);
    if (!mounted) return;

    if (result != null && result.success && result.text.trim().isNotEmpty) {
      handleSuccess(result.text.trim());
      return;
    }

    handleError(_transcriptionService.lastError ?? result?.error ?? 'Transcription failed');
  }

  @override
  void dispose() {
    _recorder.dispose();
    _transcriptionService.dispose();
    super.dispose();
  }
}
