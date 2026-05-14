import 'package:flutter/material.dart';
import 'dart:js' as js;

class VoiceButton extends StatefulWidget {
  final Function(String) onResult;
  final VoidCallback? onStart;
  final VoidCallback? onStop;

  const VoiceButton({
    required this.onResult,
    this.onStart,
    this.onStop,
    Key? key,
  }) : super(key: key);

  @override
  _VoiceButtonState createState() => _VoiceButtonState();
}

class _VoiceButtonState extends State<VoiceButton> {
  bool _isListening = false;
  String _recognizedText = '';

  void _startWebSpeechRecognition() async {
    widget.onStart?.call();
    
    if (mounted) {
      setState(() {
        _isListening = true;
        _recognizedText = '';
      });
    }

    try {
      // Use Web Speech API via JavaScript
      final result = await js.context.callMethod('startVoiceInput');
      
      if (result != null && result.toString().isNotEmpty) {
        _recognizedText = result.toString();
        if (mounted) {
          widget.onResult(_recognizedText);
          setState(() {
            _isListening = false;
          });
        }
        widget.onStop?.call();
      } else {
        if (mounted) {
          setState(() {
            _isListening = false;
          });
        }
        widget.onStop?.call();
      }
    } catch (e) {
      print('Speech recognition error: $e');
      _showErrorSnackbar('Microphone access denied or not available');
      if (mounted) {
        setState(() {
          _isListening = false;
        });
      }
      widget.onStop?.call();
    }
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
    return Container(
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
          onTap: _isListening ? null : _startWebSpeechRecognition,
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
    );
  }
}
