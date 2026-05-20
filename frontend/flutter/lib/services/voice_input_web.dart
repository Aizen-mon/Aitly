import 'dart:js' as js;

Future<String?> startVoiceInput() async {
  final result = await js.context.callMethod('startVoiceInput');
  return result?.toString();
}