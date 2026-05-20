import 'package:flutter_tts/flutter_tts.dart';

final FlutterTts _tts = FlutterTts();

Future<void> speakAssistantText(String text) async {
  await _tts.setLanguage('en-IN');
  await _tts.setSpeechRate(0.48);
  await _tts.speak(text);
}