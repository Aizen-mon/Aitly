import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'services/audio_recorder_service.dart';
import 'services/transcription_service.dart';
import 'services/tts_service.dart';
import 'services/api.dart';

/// Enhanced voice assistant screen with local Faster-Whisper integration
class VoiceAssistantScreen extends StatefulWidget {
  const VoiceAssistantScreen({Key? key}) : super(key: key);

  @override
  State<VoiceAssistantScreen> createState() => _VoiceAssistantScreenState();
}

class _VoiceAssistantScreenState extends State<VoiceAssistantScreen> {
  late AudioRecorderService _recorderService;
  late TranscriptionService _transcriptionService;
  late TTSService _ttsService;

  List<ConversationMessage> _messages = [];
  bool _isListening = false;
  bool _isProcessing = false;
  String? _currentTranscript;
  String? _statusMessage;

  @override
  void initState() {
    super.initState();
    _initializeServices();
  }

  void _initializeServices() {
    _recorderService = AudioRecorderService();
    final apiClient = context.read<ApiClient>();
    _transcriptionService = TranscriptionService(apiClient);
    _ttsService = TTSService();

    // Set up callbacks
    _recorderService.onRecordingStarted = _onRecordingStarted;
    _recorderService.onRecordingStopped = _onRecordingStopped;
    _recorderService.onDurationChanged = _onDurationChanged;
    _recorderService.onError = _onError;

    _ttsService.onSpeechStart = _onSpeechStart;
    _ttsService.onSpeechComplete = _onSpeechComplete;
    _ttsService.onError = _onError;
  }

  void _onRecordingStarted() {
    setState(() {
      _isListening = true;
      _statusMessage = 'Listening...';
    });
  }

  void _onRecordingStopped() {
    setState(() {
      _isListening = false;
      _statusMessage = 'Processing...';
      _isProcessing = true;
    });
  }

  void _onDurationChanged(Duration duration) {
    // Update UI if needed
    if (duration.inSeconds > 30) {
      _stopRecording();
    }
  }

  void _onError(String error) {
    setState(() {
      _statusMessage = 'Error: $error';
      _isListening = false;
      _isProcessing = false;
    });
  }

  void _onSpeechStart() {
    setState(() {
      _statusMessage = 'Speaking...';
    });
  }

  void _onSpeechComplete() {
    setState(() {
      _statusMessage = 'Ready';
    });
  }

  Future<void> _startRecording() async {
    final success = await _recorderService.startRecording();
    if (!success) {
      _showError('Failed to start recording');
    }
  }

  Future<void> _stopRecording() async {
    final filePath = await _recorderService.stopRecording();
    if (filePath != null) {
      await _transcribeAudio(filePath);
    }
  }

  Future<void> _transcribeAudio(String filePath) async {
    try {
      setState(() {
        _statusMessage = 'Transcribing...';
      });

      final result = await _transcriptionService.transcribeFile(
        filePath,
        language: 'en',
      );

      if (result != null && result.success) {
        setState(() {
          _currentTranscript = result.text;
          _statusMessage = 'Transcribed';
        });

        _addMessage(
          result.text,
          isUser: true,
          timestamp: DateTime.now(),
        );

        // Send to backend for processing
        await _processVoiceCommand(result.text);
      } else {
        _showError('Transcription failed');
      }
    } catch (e) {
      _showError('Error: $e');
    } finally {
      setState(() {
        _isProcessing = false;
      });
    }
  }

  Future<void> _processVoiceCommand(String transcript) async {
    try {
      setState(() {
        _statusMessage = 'Processing command...';
      });

      final apiClient = context.read<ApiClient>();
      final response = await apiClient.post('/voice/process', {
        'transcript': transcript,
      });

      if (response != null) {
        final message = response['message'] ?? 'Command processed';
        _addMessage(
          message,
          isUser: false,
          timestamp: DateTime.now(),
        );

        // Speak response
        await _ttsService.speakInIndianEnglish(message);

        setState(() {
          _statusMessage = 'Ready';
        });
      }
    } catch (e) {
      _showError('Error processing command: $e');
    }
  }

  void _addMessage(String text,
      {required bool isUser, required DateTime timestamp}) {
    setState(() {
      _messages.add(
        ConversationMessage(
          text: text,
          isUser: isUser,
          timestamp: timestamp,
        ),
      );
    });
  }

  void _showError(String message) {
    _addMessage(
      message,
      isUser: false,
      timestamp: DateTime.now(),
    );
  }

  void _toggleMute() {
    _ttsService.toggleMute();
  }

  void _clearHistory() {
    setState(() {
      _messages.clear();
      _statusMessage = 'Ready';
    });
  }

  @override
  void dispose() {
    _recorderService.dispose();
    _ttsService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Voice Assistant'),
        elevation: 2,
        actions: [
          IconButton(
            icon: Icon(_ttsService.isMuted ? Icons.volume_off : Icons.volume_up),
            onPressed: _toggleMute,
            tooltip: 'Toggle volume',
          ),
          IconButton(
            icon: const Icon(Icons.delete_outline),
            onPressed: _clearHistory,
            tooltip: 'Clear history',
          ),
        ],
      ),
      body: Column(
        children: [
          // Status indicator
          _buildStatusBar(),

          // Conversation history
          Expanded(
            child: _buildConversationHistory(),
          ),

          // Waveform and recording controls
          _buildControlPanel(),
        ],
      ),
    );
  }

  Widget _buildStatusBar() {
    Color statusColor = Colors.grey;
    IconData statusIcon = Icons.radio_button_unchecked;

    if (_isListening) {
      statusColor = Colors.red;
      statusIcon = Icons.mic;
    } else if (_isProcessing) {
      statusColor = Colors.orange;
      statusIcon = Icons.hourglass_bottom;
    } else if (_ttsService.isSpeaking) {
      statusColor = Colors.blue;
      statusIcon = Icons.speaker;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      color: statusColor.withOpacity(0.1),
      child: Row(
        children: [
          Icon(statusIcon, color: statusColor, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              _statusMessage ?? 'Ready',
              style: TextStyle(
                color: statusColor,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          if (_isListening)
            _buildWaveformAnimation(),
        ],
      ),
    );
  }

  Widget _buildWaveformAnimation() {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (int i = 0; i < 3; i++)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 2),
            child: AnimatedContainer(
              duration: Duration(milliseconds: 200 + (i * 50)),
              height: 8 + (i * 4),
              width: 4,
              decoration: BoxDecoration(
                color: Colors.red,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildConversationHistory() {
    return ListView.builder(
      padding: const EdgeInsets.all(12),
      reverse: true,
      itemCount: _messages.length,
      itemBuilder: (context, index) {
        final message = _messages[_messages.length - 1 - index];
        return _buildMessageBubble(message);
      },
    );
  }

  Widget _buildMessageBubble(ConversationMessage message) {
    return Align(
      alignment: message.isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 8),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        decoration: BoxDecoration(
          color: message.isUser
              ? Colors.blue.shade600
              : Colors.grey.shade300,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              message.text,
              style: TextStyle(
                color: message.isUser ? Colors.white : Colors.black87,
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              _formatTime(message.timestamp),
              style: TextStyle(
                color: message.isUser ? Colors.white70 : Colors.black54,
                fontSize: 11,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildControlPanel() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: Colors.grey.shade300)),
      ),
      child: Column(
        children: [
          // Recording duration indicator
          if (_isListening)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(
                'Recording: ${_recorderService.getDuration().inSeconds}s',
                style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
              ),
            ),

          // Main action buttons
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              // Mic button
              FloatingActionButton.large(
                onPressed: _isListening ? _stopRecording : _startRecording,
                backgroundColor:
                    _isListening ? Colors.red.shade600 : Colors.blue.shade600,
                child: Icon(
                  _isListening ? Icons.stop : Icons.mic,
                  size: 28,
                ),
              ),

              // Controls
              Column(
                children: [
                  IconButton(
                    icon: const Icon(Icons.clear),
                    onPressed: _messages.isEmpty ? null : _clearHistory,
                    tooltip: 'Clear history',
                  ),
                  const Text('Clear', style: TextStyle(fontSize: 11)),
                ],
              ),
            ],
          ),

          const SizedBox(height: 8),

          // Quick commands
          Wrap(
            spacing: 8,
            children: [
              _buildQuickCommandButton('Show sales'),
              _buildQuickCommandButton('Low stock'),
              _buildQuickCommandButton('New invoice'),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildQuickCommandButton(String label) {
    return ActionChip(
      label: Text(label, style: const TextStyle(fontSize: 12)),
      onPressed: () async {
        // Simulate voice command
        _addMessage(label, isUser: true, timestamp: DateTime.now());
        await _processVoiceCommand(label);
      },
      backgroundColor: Colors.grey.shade200,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
    );
  }

  String _formatTime(DateTime time) {
    return '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}';
  }
}

/// Conversation message model
class ConversationMessage {
  final String text;
  final bool isUser;
  final DateTime timestamp;

  ConversationMessage({
    required this.text,
    required this.isUser,
    required this.timestamp,
  });
}
