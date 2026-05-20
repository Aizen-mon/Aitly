import 'dart:async';

import 'package:speech_to_text/speech_to_text.dart' as stt;

Future<String?> startVoiceInput() async {
  final speech = stt.SpeechToText();
  final completer = Completer<String?>();
  String recognizedWords = '';

  final available = await speech.initialize(
    onStatus: (status) {
      if ((status == 'done' || status == 'notListening') && !completer.isCompleted) {
        completer.complete(recognizedWords.isEmpty ? null : recognizedWords);
      }
    },
    onError: (errorNotification) {
      if (!completer.isCompleted) {
        completer.complete(null);
      }
    },
  );

  if (!available) {
    return null;
  }

  await speech.listen(
    onResult: (result) {
      recognizedWords = result.recognizedWords;
      if (result.finalResult && !completer.isCompleted) {
        completer.complete(recognizedWords.isEmpty ? null : recognizedWords);
      }
    },
    listenFor: const Duration(seconds: 8),
    pauseFor: const Duration(seconds: 2),
    partialResults: true,
  );

  return completer.future.timeout(
    const Duration(seconds: 12),
    onTimeout: () async {
      await speech.stop();
      return recognizedWords.isEmpty ? null : recognizedWords;
    },
  );
}