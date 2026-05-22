import 'dart:io';

import 'package:http/http.dart' as http;

Future<http.MultipartFile?> multipartAudioFile(String filePath) async {
  final file = File(filePath);
  if (!await file.exists()) {
    return null;
  }
  return http.MultipartFile(
    'audio',
    file.openRead(),
    await file.length(),
    filename: 'audio.wav',
  );
}
