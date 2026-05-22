import 'dart:io';
import 'dart:typed_data';

import 'package:path_provider/path_provider.dart';

Future<String> createRecordingPath() async {
  final appDir = await getApplicationDocumentsDirectory();
  final recordingsDir = Directory('${appDir.path}/voice_recordings');
  if (!await recordingsDir.exists()) {
    await recordingsDir.create(recursive: true);
  }
  final timestamp = DateTime.now().millisecondsSinceEpoch;
  return '${recordingsDir.path}/recording_$timestamp.wav';
}

Future<bool> recordingExists(String path) => File(path).exists();

Future<int> recordingLength(String path) => File(path).length();

Future<Uint8List?> readRecordingBytes(String path) async {
  final file = File(path);
  if (!await file.exists()) {
    return null;
  }
  return file.readAsBytes();
}

Future<bool> deleteRecordingFile(String path) async {
  final file = File(path);
  if (!await file.exists()) {
    return false;
  }
  await file.delete();
  return true;
}

Future<int> cleanupOldRecordings({required int olderThanDays}) async {
  final appDir = await getApplicationDocumentsDirectory();
  final recordingsDir = Directory('${appDir.path}/voice_recordings');
  if (!await recordingsDir.exists()) {
    return 0;
  }

  int deleted = 0;
  final cutoffTime = DateTime.now().subtract(Duration(days: olderThanDays));
  for (final file in recordingsDir.listSync()) {
    if (file is File && file.lastModifiedSync().isBefore(cutoffTime)) {
      await file.delete();
      deleted++;
    }
  }
  return deleted;
}
