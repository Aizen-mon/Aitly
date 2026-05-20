import 'dart:js' as js;
import 'dart:js_util' as js_util;

Future<String?> startVoiceInput() async {
  try {
    // Call the JS function which returns a Promise and convert it to a Dart Future
    final jsPromise = js.context.callMethod('startVoiceInput');
    final result = await js_util.promiseToFuture(jsPromise);
    return result?.toString();
  } catch (e) {
    // If anything goes wrong (no function, rejected promise), return null
    return null;
  }
}