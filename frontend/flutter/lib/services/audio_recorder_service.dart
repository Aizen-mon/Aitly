import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';

import 'recorder_fs_web.dart' if (dart.library.io) 'recorder_fs_io.dart' as recorder_fs;

/// Audio recording state
enum RecordingState {
  idle,
  recording,
  processing,
  paused,
  stopped,
}

/// Audio recording metrics
class AudioMetrics {
  final Duration duration;
  final int fileSize;
  final double sampleRate;
  final int channels;

  AudioMetrics({
    required this.duration,
    required this.fileSize,
    this.sampleRate = 16000,
    this.channels = 1,
  });
}

/// Local audio recording service.
/// Native: WAV file via path_provider. Web: in-memory bytes from blob URL.
class AudioRecorderService extends ChangeNotifier {
  final AudioRecorder _record = AudioRecorder();
  late Future<void> _initializationFuture;

  RecordingState _state = RecordingState.idle;
  String? _currentRecordingPath;
  Uint8List? _lastRecordingBytes;
  Duration _recordingDuration = Duration.zero;
  Timer? _durationTimer;
  AudioMetrics? _lastRecordingMetrics;
  String? _lastError;

  VoidCallback? onRecordingStarted;
  VoidCallback? onRecordingStopped;
  Function(Duration)? onDurationChanged;
  Function(String)? onError;

  final int sampleRate = 16000;
  final int channels = 1;

  AudioRecorderService() {
    _initializationFuture = _initialize();
  }

  Future<void> _initialize() async {
    await requestMicrophonePermission();
  }

  Future<bool> requestMicrophonePermission() async {
    if (kIsWeb) {
      return _record.hasPermission();
    }
    final status = await Permission.microphone.request();
    return status.isGranted;
  }

  Future<bool> hasMicrophonePermission() async {
    if (kIsWeb) {
      return _record.hasPermission();
    }
    return Permission.microphone.isGranted;
  }

  Future<bool> startRecording({String? customPath}) async {
    try {
      await _initializationFuture;

      final hasPermission = await hasMicrophonePermission();
      if (!hasPermission) {
        _setError('Microphone permission not granted');
        return false;
      }

      const config = RecordConfig(
        encoder: AudioEncoder.wav,
        numChannels: 1,
        sampleRate: 16000,
      );

      if (kIsWeb) {
        // Path is ignored on web; stop() returns a blob URL for byte download.
        await _record.start(config, path: '');
        _currentRecordingPath = null;
      } else {
        _currentRecordingPath = customPath ?? await recorder_fs.createRecordingPath();
        await _record.start(config, path: _currentRecordingPath!);
      }

      _lastRecordingBytes = null;
      _state = RecordingState.recording;
      _recordingDuration = Duration.zero;
      _startDurationTimer();
      notifyListeners();
      onRecordingStarted?.call();
      return true;
    } catch (e) {
      _setError('Failed to start recording: $e');
      return false;
    }
  }

  Future<String?> stopRecording() async {
    try {
      if (_state != RecordingState.recording && _state != RecordingState.paused) {
        return null;
      }

      final stoppedPath = await _record.stop();
      _state = RecordingState.stopped;
      _stopDurationTimer();

      final recordingPath = kIsWeb ? (stoppedPath ?? '') : (stoppedPath ?? _currentRecordingPath);
      _currentRecordingPath = null;
      notifyListeners();
      onRecordingStopped?.call();

      if (kIsWeb) {
        if (recordingPath == null || recordingPath.isEmpty) {
          return null;
        }
        _lastRecordingBytes = await recorder_fs.readRecordingBytes(recordingPath);
        if (_lastRecordingBytes == null || _lastRecordingBytes!.isEmpty) {
          return null;
        }
        _lastRecordingMetrics = AudioMetrics(
          duration: _recordingDuration,
          fileSize: _lastRecordingBytes!.length,
          sampleRate: sampleRate.toDouble(),
          channels: channels,
        );
        return recordingPath;
      }

      if (recordingPath != null && await recorder_fs.recordingExists(recordingPath)) {
        final fileSize = await recorder_fs.recordingLength(recordingPath);
        _lastRecordingBytes = await recorder_fs.readRecordingBytes(recordingPath);
        _lastRecordingMetrics = AudioMetrics(
          duration: _recordingDuration,
          fileSize: fileSize,
          sampleRate: sampleRate.toDouble(),
          channels: channels,
        );
        return recordingPath;
      }

      return null;
    } catch (e) {
      _setError('Failed to stop recording: $e');
      return null;
    }
  }

  Future<void> pauseRecording() async {
    if (_state != RecordingState.recording) return;
    _state = RecordingState.paused;
    _stopDurationTimer();
    notifyListeners();
  }

  Future<void> resumeRecording() async {
    if (_state != RecordingState.paused) return;
    _state = RecordingState.recording;
    _startDurationTimer();
    notifyListeners();
  }

  Future<Uint8List?> getRecordingBytes([String? filePath]) async {
    try {
      if (_lastRecordingBytes != null && _lastRecordingBytes!.isNotEmpty) {
        return _lastRecordingBytes;
      }

      final path = filePath;
      if (path == null || path.isEmpty) {
        return null;
      }

      return recorder_fs.readRecordingBytes(path);
    } catch (e) {
      _setError('Failed to read recording: $e');
      return null;
    }
  }

  Future<bool> deleteRecording(String? filePath) async {
    try {
      _lastRecordingBytes = null;
      final path = filePath;
      if (path == null || path.isEmpty) {
        return false;
      }
      return recorder_fs.deleteRecordingFile(path);
    } catch (e) {
      _setError('Failed to delete recording: $e');
      return false;
    }
  }

  Duration getDuration() => _recordingDuration;
  RecordingState getState() => _state;
  String? getLastError() => _lastError;
  AudioMetrics? getLastMetrics() => _lastRecordingMetrics;
  bool isRecording() => _state == RecordingState.recording;
  bool isPaused() => _state == RecordingState.paused;

  Future<int> cleanupOldRecordings({int olderThanDays = 7}) async {
    try {
      return recorder_fs.cleanupOldRecordings(olderThanDays: olderThanDays);
    } catch (e) {
      _setError('Cleanup failed: $e');
      return 0;
    }
  }

  void _startDurationTimer() {
    _durationTimer = Timer.periodic(const Duration(milliseconds: 100), (_) {
      _recordingDuration += const Duration(milliseconds: 100);
      onDurationChanged?.call(_recordingDuration);
      notifyListeners();
    });
  }

  void _stopDurationTimer() {
    _durationTimer?.cancel();
    _durationTimer = null;
  }

  void _setError(String error) {
    _lastError = error;
    onError?.call(error);
    debugPrint('AudioRecorderService Error: $error');
  }

  @override
  void dispose() {
    _stopDurationTimer();
    _record.dispose();
    super.dispose();
  }
}
