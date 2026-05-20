import 'package:flutter/material.dart';
import '../services/voice_input.dart';

class VoiceButton extends StatefulWidget {
  final Function(String) onResult;
  final ValueChanged<bool>? onListeningChanged;
  final bool continuous;

  const VoiceButton({
    required this.onResult,
    this.onListeningChanged,
    this.continuous = false,
    Key? key,
  }) : super(key: key);

  @override
  _VoiceButtonState createState() => _VoiceButtonState();
}

class _VoiceButtonState extends State<VoiceButton> {
  bool _isListening = false;
  bool _stopRequested = false;

  Future<void> _startWebSpeechRecognition() async {
    _stopRequested = false;
    _setListening(true);

    try {
      while (!_stopRequested) {
        final result = await startVoiceInput();
        if (!mounted || _stopRequested) {
          break;
        }

        if (result != null && result.toString().isNotEmpty) {
          widget.onResult(result.toString());
        }

        if (!widget.continuous) {
          break;
        }
      }
    } catch (e) {
      _showErrorSnackbar('Microphone access denied or not available');
    } finally {
      _setListening(false);
    }
  }

  void _stopListening() {
    _stopRequested = true;
    _setListening(false);
  }

  void _setListening(bool listening) {
    if (!mounted) return;
    setState(() {
      _isListening = listening;
    });
    widget.onListeningChanged?.call(listening);
  }

  void _showErrorSnackbar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        duration: const Duration(seconds: 3),
        backgroundColor: Colors.red[400],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedScale(
      scale: _isListening ? 1.08 : 1.0,
      duration: const Duration(milliseconds: 180),
      child: Container(
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: _isListening ? Colors.red[400] : Colors.blue,
          boxShadow: _isListening
              ? [
                  BoxShadow(
                    color: Colors.red.withOpacity(0.5),
                    spreadRadius: 8,
                    blurRadius: 12,
                  ),
                ]
              : [],
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: _isListening ? _stopListening : _startWebSpeechRecognition,
            customBorder: const CircleBorder(),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Icon(
                _isListening ? Icons.mic : Icons.mic_none,
                color: Colors.white,
                size: 24,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
