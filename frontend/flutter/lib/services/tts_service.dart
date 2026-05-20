import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';

/// Text-to-Speech service using flutter_tts
class TTSService extends ChangeNotifier {
  late FlutterTts _tts;
  bool _isInitialized = false;
  bool _isSpeaking = false;
  bool _isMuted = false;
  double _speechRate = 0.85;
  double _pitch = 1.0;
  double _volume = 1.0;
  String _language = 'en-IN';

  /// Callback when speech starts
  VoidCallback? onSpeechStart;

  /// Callback when speech completes
  VoidCallback? onSpeechComplete;

  /// Callback when error occurs
  Function(String)? onError;

  TTSService() {
    _initializeTTS();
  }

  /// Initialize TTS engine
  Future<void> _initializeTTS() async {
    try {
      _tts = FlutterTts();

      // Set language to Indian English
      await _tts.setLanguage(_language);

      // Set default parameters
      await _tts.setSpeechRate(_speechRate);
      await _tts.setPitch(_pitch);
      await _tts.setVolume(_volume);

      // Set up callbacks
      _tts.setStartHandler(() {
        _isSpeaking = true;
        notifyListeners();
        onSpeechStart?.call();
      });

      _tts.setCompletionHandler(() {
        _isSpeaking = false;
        notifyListeners();
        onSpeechComplete?.call();
      });

      _tts.setErrorHandler((message) {
        _isSpeaking = false;
        onError?.call(message);
        notifyListeners();
      });

      _isInitialized = true;
      notifyListeners();
    } catch (e) {
      debugPrint('TTS initialization failed: $e');
      onError?.call('Failed to initialize TTS: $e');
    }
  }

  /// Check if TTS is initialized
  bool get isInitialized => _isInitialized;

  /// Check if currently speaking
  bool get isSpeaking => _isSpeaking;

  /// Check if muted
  bool get isMuted => _isMuted;

  /// Get current speech rate
  double get speechRate => _speechRate;

  /// Get current pitch
  double get pitch => _pitch;

  /// Speak text
  Future<void> speak(String text) async {
    if (!_isInitialized) {
      onError?.call('TTS not initialized');
      return;
    }

    if (text.isEmpty) return;

    if (_isMuted) {
      debugPrint('TTS muted: $text');
      return;
    }

    try {
      await _tts.stop();
      await _tts.speak(text);
    } catch (e) {
      onError?.call('Failed to speak: $e');
    }
  }

  /// Stop speaking
  Future<void> stop() async {
    try {
      await _tts.stop();
      _isSpeaking = false;
      notifyListeners();
    } catch (e) {
      onError?.call('Failed to stop speaking: $e');
    }
  }

  /// Pause speaking (if supported)
  Future<void> pause() async {
    try {
      await _tts.pause();
    } catch (e) {
      debugPrint('Pause not supported: $e');
    }
  }

  /// Set speech rate (0.0 - 1.0)
  Future<void> setSpeechRate(double rate) async {
    if (rate < 0.0 || rate > 1.0) return;
    try {
      await _tts.setSpeechRate(rate);
      _speechRate = rate;
      notifyListeners();
    } catch (e) {
      onError?.call('Failed to set speech rate: $e');
    }
  }

  /// Set pitch (0.5 - 2.0)
  Future<void> setPitch(double pitch) async {
    if (pitch < 0.5 || pitch > 2.0) return;
    try {
      await _tts.setPitch(pitch);
      _pitch = pitch;
      notifyListeners();
    } catch (e) {
      onError?.call('Failed to set pitch: $e');
    }
  }

  /// Set volume (0.0 - 1.0)
  Future<void> setVolume(double volume) async {
    if (volume < 0.0 || volume > 1.0) return;
    try {
      await _tts.setVolume(volume);
      _volume = volume;
      notifyListeners();
    } catch (e) {
      onError?.call('Failed to set volume: $e');
    }
  }

  /// Set language
  Future<void> setLanguage(String languageCode) async {
    try {
      await _tts.setLanguage(languageCode);
      _language = languageCode;
      notifyListeners();
    } catch (e) {
      onError?.call('Failed to set language: $e');
    }
  }

  /// Toggle mute
  void toggleMute() {
    _isMuted = !_isMuted;
    notifyListeners();
  }

  /// Set mute state
  void setMuted(bool muted) {
    _isMuted = muted;
    if (muted) {
      stop();
    }
    notifyListeners();
  }

  /// Speak with Indian accent optimized configuration
  Future<void> speakInIndianEnglish(String text) async {
    try {
      // Optimize for Indian English
      await setLanguage('en-IN');
      await setSpeechRate(0.85); // Slightly slower for clarity
      await setPitch(1.0);

      await speak(text);
    } catch (e) {
      onError?.call('Failed to speak: $e');
    }
  }

  /// Speak a formatted invoice confirmation
  Future<void> speakInvoiceConfirmation({
    required String customerName,
    required double amount,
    required List<String> items,
  }) async {
    final itemsList = items.join(', ');
    final text =
        'Invoice for $customerName. Items: $itemsList. Total rupees $amount. Confirm?';

    await speakInIndianEnglish(text);
  }

  /// Speak a payment confirmation
  Future<void> speakPaymentConfirmation({
    required String customerName,
    required double amount,
  }) async {
    final text =
        'Payment of rupees $amount received from $customerName. Confirm?';

    await speakInIndianEnglish(text);
  }

  /// Speak inventory update
  Future<void> speakInventoryUpdate({
    required String productName,
    required int quantity,
    required String action,
  }) async {
    final text = '$action $quantity $productName in inventory.';

    await speakInIndianEnglish(text);
  }

  /// Speak dashboard summary
  Future<void> speakDashboardSummary({
    required double todaysSales,
    required int lowStockCount,
    required double pendingDues,
  }) async {
    final text =
        "Today's sales: rupees $todaysSales. Low stock items: $lowStockCount. Pending dues: rupees $pendingDues.";

    await speakInIndianEnglish(text);
  }

  @override
  void dispose() {
    _tts.stop();
    super.dispose();
  }
}
