import 'dart:typed_data';

import 'package:http/http.dart' as http;

Future<String> createRecordingPath() async {
  throw UnsupportedError('Web recordings do not use filesystem paths');
}

Future<bool> recordingExists(String path) async => path.isNotEmpty;

Future<int> recordingLength(String path) async {
  final bytes = await readRecordingBytes(path);
  return bytes?.length ?? 0;
}

Future<Uint8List?> readRecordingBytes(String path) async {
  if (path.isEmpty) {
    return null;
  }
  final uri = Uri.parse(path);
  final response = await http.get(uri);
  if (response.statusCode != 200) {
    return null;
  }
  return Uint8List.fromList(response.bodyBytes);
}

Future<bool> deleteRecordingFile(String path) async => true;

Future<int> cleanupOldRecordings({required int olderThanDays}) async => 0;
