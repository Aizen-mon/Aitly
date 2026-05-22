import 'package:flutter/material.dart';
import '../services/audio_recorder_service.dart';
import '../services/transcription_service.dart';

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
  State<SimpleVoiceControl> createState() => _SimpleVoiceControlState();
}

class _SimpleVoiceControlState extends State<SimpleVoiceControl> {
  late final AudioRecorderService _recorder;
  late final TranscriptionService _transcriptionService;
  bool _isRecording = false;
  bool _isTranscribing = false;
  bool _initializing = true;
  String _statusText = 'Checking microphone...';
  String _liveTranscript = '';
  String? _errorText;

  @override
  void initState() {
    super.initState();
    _recorder = AudioRecorderService();
    _transcriptionService = TranscriptionService();
    _initializeRecorder();
  }

  Future<void> _initializeRecorder() async {
    final available = await _recorder.hasMicrophonePermission();
    if (!mounted) return;
    setState(() {
      _initializing = false;
      _statusText = available ? 'Hold or tap the mic to record' : 'Microphone permission is required';
      _errorText = available ? null : 'Microphone permission is required';
    });
  }

  Future<void> _startRecording() async {
    if (_isRecording || _isTranscribing || _initializing) {
      return;
    }

    final started = await _recorder.startRecording();
    if (!started) {
      _handleError(_recorder.getLastError() ?? 'Could not start recording');
      return;
    }

    if (!mounted) return;
    setState(() {
      _isRecording = true;
      _liveTranscript = '';
      _errorText = null;
      _statusText = 'Recording...';
    });
    widget.onListeningChanged?.call(true);
  }

  Future<void> _stopRecording() async {
    if (!_isRecording || _isTranscribing) {
      return;
    }

    final recordingPath = await _recorder.stopRecording();
    if (!mounted) return;

    setState(() {
      _isRecording = false;
      _isTranscribing = true;
      _statusText = 'Transcribing...';
    });
    widget.onListeningChanged?.call(false);

    final audioBytes = await _recorder.getRecordingBytes(recordingPath);
    if (audioBytes == null || audioBytes.isEmpty) {
      _handleError(_recorder.getLastError() ?? 'Recording failed');
      return;
    }

    final result = await _transcriptionService.transcribeBytes(audioBytes);
    if (!mounted) return;

    if (result != null && result.success && result.text.trim().isNotEmpty) {
      final transcript = result.text.trim();
      setState(() {
        _isTranscribing = false;
        _statusText = 'Transcript ready';
        _liveTranscript = transcript;
        _errorText = null;
      });
      widget.onFinalTranscript(transcript);
      return;
    }

    _handleError(_transcriptionService.lastError ?? result?.error ?? 'Transcription failed');
  }

  void _handleError(String message) {
    if (!mounted) {
      return;
    }

    setState(() {
      _isRecording = false;
      _isTranscribing = false;
      _statusText = message;
      _errorText = message;
    });
    widget.onListeningChanged?.call(false);
    widget.onError?.call(message);
  }

  @override
  void dispose() {
    _recorder.dispose();
    _transcriptionService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

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
                  color: _isRecording ? Colors.red.shade100 : (_isTranscribing ? Colors.orange.shade100 : Colors.blue.shade50),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  _isRecording ? Icons.mic : (_isTranscribing ? Icons.autorenew : Icons.mic_none),
                  color: _isRecording ? Colors.red.shade700 : (_isTranscribing ? Colors.orange.shade700 : Colors.blue.shade700),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _isRecording ? 'Recording now' : (_isTranscribing ? 'Transcribing' : 'Voice input'),
                      style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      _statusText,
                      style: theme.textTheme.bodySmall?.copyWith(color: _errorText == null ? Colors.black54 : Colors.red.shade700),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              FilledButton.icon(
                onPressed: _initializing
                    ? null
                    : (_isRecording ? _stopRecording : _startRecording),
                icon: Icon(_isRecording ? Icons.stop : Icons.mic),
                label: Text(_isRecording ? 'Stop' : 'Talk'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Hold the mic to talk, or tap it to toggle recording.',
            style: theme.textTheme.bodySmall?.copyWith(color: Colors.black45),
          ),
          if (_liveTranscript.isNotEmpty) ...[
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: theme.colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Text(
                _liveTranscript,
                style: theme.textTheme.bodyMedium,
              ),
            ),
          ],
        ],
      ),
    );
  }
}