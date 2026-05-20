import 'package:flutter/material.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

class SimpleVoiceControl extends StatefulWidget {
  final ValueChanged<String> onFinalTranscript;
  final ValueChanged<bool>? onListeningChanged;

  const SimpleVoiceControl({
    required this.onFinalTranscript,
    this.onListeningChanged,
    Key? key,
  }) : super(key: key);

  @override
  State<SimpleVoiceControl> createState() => _SimpleVoiceControlState();
}

class _SimpleVoiceControlState extends State<SimpleVoiceControl> {
  final stt.SpeechToText _speech = stt.SpeechToText();

  bool _available = false;
  bool _isListening = false;
  bool _initializing = true;
  String _statusText = 'Checking microphone...';
  String _liveTranscript = '';

  @override
  void initState() {
    super.initState();
    _initializeSpeech();
  }

  Future<void> _initializeSpeech() async {
    final available = await _speech.initialize(
      onStatus: (status) {
        if ((status == 'done' || status == 'notListening') && _isListening) {
          _finishListening();
        }
      },
      onError: (errorNotification) {
        if (!mounted) return;
        setState(() {
          _statusText = 'Mic error: ${errorNotification.errorMsg}';
          _isListening = false;
          _liveTranscript = '';
          _initializing = false;
        });
        widget.onListeningChanged?.call(false);
      },
    );

    if (!mounted) return;
    setState(() {
      _available = available;
      _initializing = false;
      _statusText = available
          ? 'Tap Start Listening to use your microphone'
          : 'Microphone is unavailable in this browser';
    });
  }

  Future<void> _startListening() async {
    if (!_available || _isListening || _initializing) {
      return;
    }

    setState(() {
      _isListening = true;
      _liveTranscript = '';
      _statusText = 'Listening...';
    });
    widget.onListeningChanged?.call(true);

    await _speech.listen(
      onResult: (result) {
        if (!mounted) return;
        setState(() {
          _liveTranscript = result.recognizedWords;
          _statusText = result.finalResult ? 'Transcript ready' : 'Listening...';
        });

        if (result.finalResult) {
          _finishListening();
        }
      },
      partialResults: true,
      listenFor: const Duration(seconds: 20),
      pauseFor: const Duration(seconds: 2),
      cancelOnError: true,
    );
  }

  Future<void> _stopListening() async {
    await _speech.stop();
    _finishListening();
  }

  void _finishListening() {
    if (!mounted || !_isListening) {
      return;
    }

    final transcript = _liveTranscript.trim();
    setState(() {
      _isListening = false;
      _statusText = transcript.isEmpty ? 'Listening stopped' : 'Transcript ready';
    });
    widget.onListeningChanged?.call(false);

    if (transcript.isNotEmpty) {
      widget.onFinalTranscript(transcript);
    }
  }

  @override
  void dispose() {
    _speech.stop();
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
                  color: _isListening ? Colors.red.shade100 : Colors.blue.shade50,
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  _isListening ? Icons.mic : Icons.mic_none,
                  color: _isListening ? Colors.red.shade700 : Colors.blue.shade700,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _isListening ? 'Listening now' : 'Voice input',
                      style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      _statusText,
                      style: theme.textTheme.bodySmall?.copyWith(color: Colors.black54),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              FilledButton.icon(
                onPressed: _initializing
                    ? null
                    : (_isListening ? _stopListening : _startListening),
                icon: Icon(_isListening ? Icons.stop : Icons.mic),
                label: Text(_isListening ? 'Stop' : 'Start'),
              ),
            ],
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