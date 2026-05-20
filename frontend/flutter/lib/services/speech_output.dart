export 'speech_output_stub.dart'
    if (dart.library.html) 'speech_output_web.dart'
    if (dart.library.io) 'speech_output_native.dart';