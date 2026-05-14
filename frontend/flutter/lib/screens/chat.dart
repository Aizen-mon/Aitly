import 'package:flutter/material.dart';
import '../services/api.dart';
import '../widgets/chat_widgets.dart';
import '../widgets/voice_button.dart';
import '../widgets/invoice_form.dart';

class ChatScreen extends StatefulWidget {
  @override
  _ChatScreenState createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  
  List<Map<String, dynamic>> messages = [];
  List<Map<String, dynamic>> suggestedPrompts = [];
  bool isLoading = false;
  bool showPrompts = true;

  @override
  void initState() {
    super.initState();
    loadSuggestedPrompts();
  }

  loadSuggestedPrompts() async {
    try {
      final data = await Api.get('/suggested_prompts');
      if (!mounted) return;
      setState(() {
        suggestedPrompts = List<Map<String, dynamic>>.from(data['prompts'] ?? []);
      });
    } catch (e) {
      print('Error loading prompts: $e');
    }
  }

  sendMessage(String text) async {
    if (text.trim().isEmpty) return;

    setState(() {
      messages.add({'role': 'user', 'text': text});
      isLoading = true;
      showPrompts = false;
    });

    _scrollToBottom();

    try {
      final response = await Api.post('/parse', {'text': text});
      if (!mounted) return;
      
      setState(() {
        messages.add({
          'role': 'assistant',
          ...?response as Map<String, dynamic>,
        });
        isLoading = false;
      });
      
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
        ),
        body: Column(
          children: [
            Expanded(
              child: messages.isEmpty && showPrompts
                  ? Center(
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
                          const SizedBox(height: 32),
                          if (suggestedPrompts.isNotEmpty)
                            SuggestedPromptsWidget(
                              prompts: suggestedPrompts,
                              onPromptSelected: _handlePromptSelected,
                            ),
                        ],
                      ),
                    )
                  : ListView.builder(
                      controller: _scrollController,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 8,
                      ),
                      itemCount: messages.length + (isLoading ? 1 : 0),
                      itemBuilder: (context, index) {
                        if (isLoading && index == messages.length) {
                          return const ChatLoadingWidget();
                        }

                        final msg = messages[index];
                        return ChatMessageWidget(
                          message: msg,
                          isUser: msg['role'] == 'user',
                        );
                      },
                    ),
            ),
            if (messages.isNotEmpty && (suggestedPrompts?.isNotEmpty ?? false))
              SuggestedPromptsWidget(
                prompts: suggestedPrompts,
                onPromptSelected: _handlePromptSelected,
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
                        hintText: 'Type or press mic to speak...',
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
                  VoiceButton(
                    onResult: (text) {
                      setState(() {
                        _controller.text = text;
                      });
                      sendMessage(text);
                    },
                    onStart: () {
                      print('Voice input started');
                    },
                    onStop: () {
                      print('Voice input stopped');
                    },
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

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }
}
