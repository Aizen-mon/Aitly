import 'package:flutter/material.dart';
import '../services/api.dart';
import '../services/assistant_speech.dart';
import '../widgets/chat_widgets.dart';
import '../widgets/invoice_form.dart';
import '../widgets/simple_voice_control.dart';

class ChatScreen extends StatefulWidget {
  @override
  _ChatScreenState createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final String _sessionId = DateTime.now().millisecondsSinceEpoch.toString();
  
  List<Map<String, dynamic>> messages = [];
  List<Map<String, dynamic>> suggestedPrompts = [];
  List<Map<String, dynamic>> recentQueries = [];
  List<Map<String, dynamic>> voiceHistory = [];
  Map<String, dynamic> assistantStatus = {};
  List<Map<String, dynamic>> assistantAlerts = [];
  bool isLoading = false;
  bool showPrompts = true;
  bool isListening = false;
  bool muted = isAssistantMuted;

  @override
  void initState() {
    super.initState();
    loadSuggestedPrompts();
    loadRecentQueries();
    loadAssistantStatus();
  }

  loadRecentQueries() async {
    try {
      final data = await Api.get('/query_history?per_page=8');
      if (!mounted) return;
      setState(() {
        recentQueries = List<Map<String, dynamic>>.from(data['items'] ?? [])
            .map((item) => {
                  ...item,
                  'query': _safeDisplayText(item['query']),
                })
            .where((item) => (item['query'] as String).trim().isNotEmpty)
            .toList();
      });
    } catch (e) {
      print('Error loading queries: $e');
    }
  }

  loadSuggestedPrompts() async {
    try {
      final data = await Api.get('/suggested_prompts');
      if (!mounted) return;
      setState(() {
        suggestedPrompts = List<Map<String, dynamic>>.from(data['prompts'] ?? [])
            .map((item) => {
                  ...item,
                  'text': _safeDisplayText(item['text']),
                })
            .where((item) => (item['text'] as String).trim().isNotEmpty)
            .toList();
      });
    } catch (e) {
      print('Error loading prompts: $e');
    }
  }

  loadAssistantStatus() async {
    try {
      final data = await Api.get('/assistant/status');
      if (!mounted) return;
      setState(() {
        assistantStatus = data is Map ? Map<String, dynamic>.from(data) : {};
        assistantAlerts = List<Map<String, dynamic>>.from(
          (data is Map<String, dynamic> ? data['alerts'] : null) ?? [],
        );
      });
    } catch (e) {
      print('Error loading assistant status: $e');
    }
  }

  sendMessage(String text) async {
    if (text.trim().isEmpty) return;
    final timestamp = DateTime.now().toIso8601String();

    setState(() {
      messages.add({'role': 'user', 'text': text, 'timestamp': timestamp, 'source': 'typed'});
      isLoading = true;
      showPrompts = false;
    });

    _scrollToBottom();

    try {
      final response = await Api.post('/parse', {'text': text, 'session_id': _sessionId});
      if (!mounted) return;
      
      setState(() {
        messages.add({
          'role': 'assistant',
          'timestamp': DateTime.now().toIso8601String(),
          ...Map<String, dynamic>.from(response as Map),
        });
        isLoading = false;
      });

      final assistantMessage = (response['speech'] ?? response['message'])?.toString();
      if (assistantMessage != null && assistantMessage.isNotEmpty) {
        await speakAssistantText(assistantMessage);
      }
      await loadRecentQueries();
      await loadAssistantStatus();
      
      // Show invoice form dialog if action is show_invoice_form
      if (response['action'] == 'show_invoice_form') {
        _showInvoiceForm();
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        messages.add({
          'role': 'assistant',
          'intent': 'error',
          'title': 'Oops!',
          'message': 'Could not process request. Please try again.',
          'error': true,
        });
        isLoading = false;
      });
    }
    _controller.clear();
    _scrollToBottom();
  }

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 100), () {
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    });
  }

  void _handlePromptSelected(String intent) {
    final promptMap = {
      'today_sales': 'Show today\'s sales',
      'low_stock': 'Show low stock items',
      'pending_dues': 'Show pending dues',
      'create_invoice': 'Create a new invoice',
    };
    sendMessage(promptMap[intent] ?? intent);
  }

  void _handleVoiceResult(String text) {
    final timestamp = DateTime.now().toIso8601String();
    setState(() {
      voiceHistory.insert(0, {'text': text, 'timestamp': timestamp});
      _controller.text = text;
    });
    sendMessage(text);
  }

  void _showInvoiceForm() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => InvoiceFormDialog(
        onSuccess: () {
          ScaffoldMessenger.of(this.context).showSnackBar(
            const SnackBar(
              content: Text('Invoice created and ready to send!'),
              backgroundColor: Colors.green,
              duration: Duration(seconds: 2),
            ),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Scaffold(
        appBar: AppBar(
          title: const Text('AI Assistant'),
          centerTitle: false,
          elevation: 0,
          backgroundColor: Colors.white,
          foregroundColor: Colors.black87,
          actions: [
            IconButton(
              tooltip: muted ? 'Unmute assistant' : 'Mute assistant',
              icon: Icon(muted ? Icons.volume_off : Icons.volume_up),
              onPressed: () {
                setState(() {
                  muted = !muted;
                  setAssistantMuted(muted);
                });
              },
            ),
          ],
        ),
        body: Column(
          children: [
            Expanded(
              child: ListView(
                controller: _scrollController,
                padding: const EdgeInsets.only(bottom: 12),
                children: [
                  if (messages.isEmpty && showPrompts)
                    SizedBox(
                      height: MediaQuery.of(context).size.height * 0.42,
                      child: Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.support_agent,
                              size: 64,
                              color: Colors.blue[200],
                            ),
                            const SizedBox(height: 16),
                            Text(
                              'How can I assist you?',
                              style: Theme.of(context).textTheme.headlineSmall,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Ask me about your business metrics',
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                            const SizedBox(height: 24),
                            if (suggestedPrompts.isNotEmpty)
                              SuggestedPromptsWidget(
                                prompts: suggestedPrompts,
                                onPromptSelected: _handlePromptSelected,
                              ),
                          ],
                        ),
                      ),
                    )
                  else
                    ...messages.map(
                      (msg) => ChatMessageWidget(
                        message: msg,
                        isUser: msg['role'] == 'user',
                      ),
                    ),
                  if (isLoading) const ChatLoadingWidget(),
                  if (assistantStatus.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      child: Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.blueGrey[50],
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: Colors.blueGrey[100]!),
                        ),
                        child: Row(
                          children: [
                            Icon(
                              assistantStatus['tally'] == 'connected' ? Icons.cloud_done : Icons.cloud_off,
                              color: assistantStatus['tally'] == 'connected' ? Colors.green : Colors.orange,
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                assistantStatus['tally'] == 'connected'
                                    ? 'Connected to Tally'
                                    : 'Tally disconnected. Actions will queue locally.',
                                style: Theme.of(context).textTheme.bodyMedium,
                              ),
                            ),
                            Text(
                              '${assistantStatus['pending_sync_count'] ?? 0} pending',
                              style: Theme.of(context).textTheme.labelSmall,
                            ),
                          ],
                        ),
                      ),
                    ),
                  if (assistantAlerts.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                      child: Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: assistantAlerts.take(3).map((alert) {
                          return Chip(
                            avatar: const Icon(Icons.notifications_active, size: 16),
                            label: Text(alert['message']?.toString() ?? ''),
                          );
                        }).toList(),
                      ),
                    ),
                  if (messages.isNotEmpty && suggestedPrompts.isNotEmpty)
                    SuggestedPromptsWidget(
                      prompts: suggestedPrompts,
                      onPromptSelected: _handlePromptSelected,
                    ),
                  if (recentQueries.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Recent Voice Queries',
                            style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 8),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: recentQueries
                                .map(
                                  (item) => InputChip(
                                    label: Text(
                                      item['query']?.toString() ?? '',
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    onPressed: () {
                                      final query = _safeDisplayText(item['query']);
                                      if (query.isNotEmpty) {
                                        sendMessage(query);
                                      }
                                    },
                                  ),
                                )
                                .toList(),
                          ),
                        ],
                      ),
                    ),
                  if (voiceHistory.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Voice History',
                            style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 8),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: voiceHistory
                                .map(
                                  (item) => Chip(
                                    avatar: const Icon(Icons.mic, size: 16),
                                    label: Text('${item['text']?.toString() ?? ''} • ${_formatTime(item['timestamp']?.toString())}'),
                                  ),
                                )
                                .toList(),
                          ),
                        ],
                      ),
                    ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
                    child: SimpleVoiceControl(
                      onListeningChanged: (listening) {
                        setState(() => isListening = listening);
                      },
                      onFinalTranscript: _handleVoiceResult,
                    ),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
              decoration: BoxDecoration(
                color: Colors.white,
                border: Border(top: BorderSide(color: Colors.grey[200]!)),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      onSubmitted: (text) => sendMessage(text),
                      enabled: !isLoading,
                      decoration: InputDecoration(
                        hintText: isListening ? 'Listening... speak now' : 'Type a message',
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                          borderSide: BorderSide(color: Colors.grey[300]!),
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                          borderSide: BorderSide(color: Colors.grey[300]!),
                        ),
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 12,
                        ),
                        suffixIcon: isLoading
                            ? const SizedBox(
                                width: 40,
                                child: Center(
                                  child: SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                    ),
                                  ),
                                ),
                              )
                            : null,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  FloatingActionButton(
                    mini: true,
                    onPressed: isLoading
                        ? null
                        : () => sendMessage(_controller.text),
                    elevation: 0,
                    backgroundColor:
                        isLoading ? Colors.grey[300] : Colors.blue,
                    child: Icon(
                      Icons.send,
                      color: isLoading ? Colors.grey : Colors.white,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _formatTime(String? isoTime) {
    if (isoTime == null || isoTime.isEmpty) return '';
    try {
      final dt = DateTime.parse(isoTime).toLocal();
      final hour = dt.hour.toString().padLeft(2, '0');
      final minute = dt.minute.toString().padLeft(2, '0');
      return '$hour:$minute';
    } catch (_) {
      return '';
    }
  }

  String _safeDisplayText(dynamic value) {
    final text = value?.toString().trim() ?? '';
    if (text.isEmpty) {
      return '';
    }

    final lower = text.toLowerCase();
    if (lower == '[object promise]' ||
        lower.startsWith('instance of') ||
        lower == 'null' ||
        lower == 'undefined') {
      return '';
    }

    return text;
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }
}
