import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'api.dart';

/// Transcription result
class TranscriptionResult {
  final String text;
  final String language;
  final double confidence;
  final List<Segment> segments;
  final double duration;
  final bool success;
  final String? error;

  TranscriptionResult({
    required this.text,
    required this.language,
    required this.confidence,
    required this.segments,
    required this.duration,
    required this.success,
    this.error,
  });

  factory TranscriptionResult.fromJson(Map<String, dynamic> json) {
    return TranscriptionResult(
      text: json['text'] ?? json['transcript'] ?? '',
      language: json['language'] ?? 'unknown',
      confidence: (json['confidence'] ?? 0).toDouble(),
      segments: (json['segments'] as List<dynamic>?)
              ?.map((s) => Segment.fromJson(s))
              .toList() ??
          [],
      duration: (json['duration_seconds'] ?? 0).toDouble(),
      success: json['success'] ?? false,
      error: json['error'],
    );
  }

  Map<String, dynamic> toJson() => {
        'text': text,
        'language': language,
        'confidence': confidence,
        'segments': segments.map((s) => s.toJson()).toList(),
        'duration_seconds': duration,
        'success': success,
        'error': error,
      };
}

/// Audio segment with timing
class Segment {
  final int id;
  final double start;
  final double end;
  final String text;
  final double confidence;

  Segment({
    required this.id,
    required this.start,
    required this.end,
    required this.text,
    required this.confidence,
  });

  factory Segment.fromJson(Map<String, dynamic> json) {
    return Segment(
      id: json['id'] ?? 0,
      start: (json['start'] ?? 0).toDouble(),
      end: (json['end'] ?? 0).toDouble(),
      text: json['text'] ?? '',
      confidence: (json['confidence'] ?? 0).toDouble(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'start': start,
        'end': end,
        'text': text,
        'confidence': confidence,
      };
}

/// Service for transcribing audio using backend Faster-Whisper
class TranscriptionService extends ChangeNotifier {
  bool _isTranscribing = false;
  String? _lastError;
  TranscriptionResult? _lastResult;

  TranscriptionService();

  /// Check if currently transcribing
  bool get isTranscribing => _isTranscribing;

  /// Get last error
  String? get lastError => _lastError;

  /// Get last result
  TranscriptionResult? get lastResult => _lastResult;

  /// Transcribe audio file
  Future<TranscriptionResult?> transcribeFile(
    String filePath, {
    String language = 'en',
  }) async {
    try {
      _isTranscribing = true;
      _lastError = null;
      notifyListeners();

      final file = File(filePath);
      if (!await file.exists()) {
        _lastError = 'Audio file not found';
        _isTranscribing = false;
        notifyListeners();
        return null;
      }

      // Create multipart request
      final uri = Uri.parse('${Api.base}/voice/transcribe');
      final request = http.MultipartRequest('POST', uri)
        ..fields['language'] = language
        ..files.add(
          http.MultipartFile(
            'audio',
            file.openRead(),
            await file.length(),
            filename: 'audio.wav',
          ),
        );

      // Send request
      final response = await request.send();
      final responseBody = await response.stream.bytesToString();

      if (response.statusCode == 200) {
        final json = jsonDecode(responseBody);
        _lastResult = TranscriptionResult.fromJson(json);

        _isTranscribing = false;
        notifyListeners();

        return _lastResult;
      } else {
        final json = jsonDecode(responseBody);
        _lastError = json['message'] ?? 'Transcription failed';

        _isTranscribing = false;
        notifyListeners();

        return null;
      }
    } catch (e) {
      _lastError = 'Error: $e';
      _isTranscribing = false;
      notifyListeners();
      return null;
    }
  }

  /// Transcribe audio from bytes
  Future<TranscriptionResult?> transcribeBytes(
    List<int> audioBytes, {
    String language = 'en',
  }) async {
    try {
      _isTranscribing = true;
      _lastError = null;
      notifyListeners();

      // Encode to base64
      final base64Audio = base64Encode(audioBytes);

      // Send request
      final response = await Api.post('/voice/transcribe', {
        'audio_base64': base64Audio,
        'language': language,
      });

      if (response != null && response['success'] == true) {
        _lastResult = TranscriptionResult.fromJson(response);

        _isTranscribing = false;
        notifyListeners();

        return _lastResult;
      } else {
        _lastError = response?['message'] ?? 'Transcription failed';

        _isTranscribing = false;
        notifyListeners();

        return null;
      }
    } catch (e) {
      _lastError = 'Error: $e';
      _isTranscribing = false;
      notifyListeners();
      return null;
    }
  }

  /// Get STT model information
  Future<Map<String, dynamic>?> getModelInfo() async {
    try {
      final result = await Api.get('/voice/models');
      return result is Map<String, dynamic> ? result : null;
    } catch (e) {
      _lastError = 'Failed to get model info: $e';
      return null;
    }
  }

  /// Clear last error
  void clearError() {
    _lastError = null;
    notifyListeners();
  }

  /// Clear last result
  void clearResult() {
    _lastResult = null;
    notifyListeners();
  }
}
