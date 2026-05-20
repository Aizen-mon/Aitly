import 'speech_output.dart' as platform_speech;

bool _muted = false;
Future<void> _queue = Future.value();

bool get isAssistantMuted => _muted;

void setAssistantMuted(bool value) {
  _muted = value;
}

Future<void> toggleAssistantMute() async {
  _muted = !_muted;
}

Future<void> speakAssistantText(String text) {
  if (_muted || text.trim().isEmpty) {
    return Future.value();
  }
  _queue = _queue.then((_) => platform_speech.speakAssistantText(text)).catchError((_) {});
  return _queue;
}
