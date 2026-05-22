import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';

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

/// Local audio recording service
/// Records audio to WAV format and prepares for upload to backend
class AudioRecorderService extends ChangeNotifier {
  final AudioRecorder _record = AudioRecorder();
  late Future<void> _initializationFuture;
  StreamSubscription<RecordingState>? _stateSubscription;

  RecordingState _state = RecordingState.idle;
  String? _currentRecordingPath;
  Duration _recordingDuration = Duration.zero;
  Timer? _durationTimer;
  AudioMetrics? _lastRecordingMetrics;
  String? _lastError;

  // Callbacks
  VoidCallback? onRecordingStarted;
  VoidCallback? onRecordingStopped;
  Function(Duration)? onDurationChanged;
  Function(String)? onError;

  // Configuration
  final String outputFormat = 'wav';
  final int sampleRate = 16000;
  final int channels = 1;
  final int bitRate = 128000;

  AudioRecorderService() {
    _initializationFuture = _initialize();
  }

  Future<void> _initialize() async {
    // Request permissions on init
    await requestMicrophonePermission();
  }

  /// Request microphone permission
  Future<bool> requestMicrophonePermission() async {
    final status = await Permission.microphone.request();
    return status.isGranted;
  }

  /// Check if microphone permission is granted
  Future<bool> hasMicrophonePermission() async {
    return await Permission.microphone.isGranted;
  }

  /// Start recording audio
  Future<bool> startRecording({String? customPath}) async {
    try {
      await _initializationFuture;

      final hasPermission = await hasMicrophonePermission();
      if (!hasPermission) {
        _setError('Microphone permission not granted');
        return false;
      }

      // Get output directory
      final appDir = await getApplicationDocumentsDirectory();
      final recordingsDir = Directory('${appDir.path}/voice_recordings');
      if (!await recordingsDir.exists()) {
        await recordingsDir.create(recursive: true);
      }

      // Create file path
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      _currentRecordingPath = customPath ?? '${recordingsDir.path}/recording_$timestamp.wav';

      await _record.start(
        const RecordConfig(
          encoder: AudioEncoder.wav,
          numChannels: 1,
          sampleRate: 16000,
        ),
        path: _currentRecordingPath!,
      );

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

  /// Stop recording and return file path
  Future<String?> stopRecording() async {
    try {
      if (_state != RecordingState.recording && _state != RecordingState.paused) {
        return null;
      }

      final stoppedPath = await _record.stop();
      _state = RecordingState.stopped;
      _stopDurationTimer();

      final recordingPath = stoppedPath ?? _currentRecordingPath;
      _currentRecordingPath = null;

      notifyListeners();
      onRecordingStopped?.call();

      // Verify file exists
      if (recordingPath != null && await File(recordingPath).exists()) {
        final fileSize = await File(recordingPath).length();
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

  /// Pause recording
  Future<void> pauseRecording() async {
    if (_state != RecordingState.recording) return;
    _state = RecordingState.paused;
    _stopDurationTimer();
    notifyListeners();
  }

  /// Resume recording
  Future<void> resumeRecording() async {
    if (_state != RecordingState.paused) return;
    _state = RecordingState.recording;
    _startDurationTimer();
    notifyListeners();
  }

  /// Get audio file as bytes
  Future<Uint8List?> getRecordingBytes(String? filePath) async {
    try {
      final path = filePath ?? _currentRecordingPath;
      if (path == null) return null;

      final file = File(path);
      if (!await file.exists()) return null;

      return await file.readAsBytes();
    } catch (e) {
      _setError('Failed to read recording: $e');
      return null;
    }
  }

  /// Delete recording file
  Future<bool> deleteRecording(String? filePath) async {
    try {
      final path = filePath ?? _currentRecordingPath;
      if (path == null) return false;

      final file = File(path);
      if (await file.exists()) {
        await file.delete();
        return true;
      }
      return false;
    } catch (e) {
      _setError('Failed to delete recording: $e');
      return false;
    }
  }

  /// Get duration of recording
  Duration getDuration() => _recordingDuration;

  /// Get recording state
  RecordingState getState() => _state;

  /// Get last error
  String? getLastError() => _lastError;

  /// Get last recording metrics
  AudioMetrics? getLastMetrics() => _lastRecordingMetrics;

  /// Check if currently recording
  bool isRecording() => _state == RecordingState.recording;

  /// Check if paused
  bool isPaused() => _state == RecordingState.paused;

  /// Clean up old recordings (older than specified days)
  Future<int> cleanupOldRecordings({int olderThanDays = 7}) async {
    try {
      final appDir = await getApplicationDocumentsDirectory();
      final recordingsDir = Directory('${appDir.path}/voice_recordings');

      if (!await recordingsDir.exists()) return 0;

      int deleted = 0;
      final now = DateTime.now();
      final cutoffTime = now.subtract(Duration(days: olderThanDays));

      for (final file in recordingsDir.listSync()) {
        if (file is File) {
          final lastModified = file.lastModifiedSync();
          if (lastModified.isBefore(cutoffTime)) {
            await file.delete();
            deleted++;
          }
        }
      }

      return deleted;
    } catch (e) {
      _setError('Cleanup failed: $e');
      return 0;
    }
  }

  /// Private helpers
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
    _stateSubscription?.cancel();
    _record.dispose();
    super.dispose();
  }
}
