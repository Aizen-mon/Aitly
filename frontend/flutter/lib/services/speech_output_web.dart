import 'dart:js' as js;

Future<void> speakAssistantText(String text) async {
  js.context.callMethod('speakText', [text]);
}