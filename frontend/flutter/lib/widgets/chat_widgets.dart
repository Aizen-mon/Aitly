import 'package:flutter/material.dart';

class ChatMessageWidget extends StatelessWidget {
  final Map<String, dynamic> message;
  final bool isUser;

  const ChatMessageWidget({
    required this.message,
    required this.isUser,
    Key? key,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    if (isUser) {
      return Align(
        alignment: Alignment.centerRight,
        child: Container(
          margin: const EdgeInsets.only(top: 8, bottom: 8, left: 60),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          decoration: BoxDecoration(
            color: Colors.blue,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            message['text'] ?? '',
            style: const TextStyle(color: Colors.white, fontSize: 14),
          ),
        ),
      );
    }

    // Bot response
    final intent = message['intent'] ?? 'general';
    final title = message['title'] ?? 'Response';
    final messageText = message['message'] ?? '';
    final color = _getColorForIntent(intent);
    final icon = _getIconForIntent(intent);

    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(top: 8, bottom: 8, right: 60),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Card(
              elevation: 1,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              child: Container(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(6),
                          decoration: BoxDecoration(
                            color: color.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Icon(icon, color: color, size: 20),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            title,
                            style: Theme.of(context)
                                .textTheme
                                .titleMedium
                                ?.copyWith(fontWeight: FontWeight.bold),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Text(
                      messageText,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    if (message['details'] != null) ...[
                      const SizedBox(height: 10),
                      _buildDetailsSection(context, message['details'] ?? {}),
                    ],
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDetailsSection(BuildContext context, Map details) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.grey[50],
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: details.entries.map<Widget>((entry) {
          final key = entry.key;
          final value = entry.value;

          if (value is List) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _formatLabel(key),
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: Colors.grey,
                    ),
                  ),
                  ...value.map((item) {
                    if (item is Map) {
                      return Text(
                        '• ${item['name']}: ${item['qty']} (Reorder: ${item['reorder']})',
                        style: const TextStyle(fontSize: 12),
                      );
                    }
                    return Text('• $item', style: const TextStyle(fontSize: 12));
                  }),
                ],
              ),
            );
          }

          return Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  _formatLabel(key),
                  style: const TextStyle(fontSize: 12, color: Colors.grey),
                ),
                Text(
                  '$value',
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }

  Color _getColorForIntent(String intent) {
    switch (intent) {
      case 'today_sales':
        return Colors.blue;
      case 'low_stock':
        return Colors.red;
      case 'pending_dues':
        return Colors.orange;
      case 'create_invoice':
        return Colors.green;
      case 'inventory':
        return Colors.teal;
      default:
        return Colors.grey;
    }
  }

  IconData _getIconForIntent(String intent) {
    switch (intent) {
      case 'today_sales':
        return Icons.trending_up;
      case 'low_stock':
        return Icons.warning_amber;
      case 'pending_dues':
        return Icons.account_balance_wallet;
      case 'create_invoice':
        return Icons.receipt_long;
      case 'inventory':
        return Icons.inventory_2;
      default:
        return Icons.help;
    }
  }

  String _formatLabel(String label) {
    return label
        .replaceAll('_', ' ')
        .split(' ')
        .map((word) => word[0].toUpperCase() + word.substring(1))
        .join(' ');
  }
}

class SuggestedPromptsWidget extends StatelessWidget {
  final List<Map<String, dynamic>> prompts;
  final Function(String) onPromptSelected;

  const SuggestedPromptsWidget({
    required this.prompts,
    required this.onPromptSelected,
    Key? key,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    if (prompts.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(left: 4, bottom: 8),
            child: Text(
              'Try asking me:',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: Colors.grey,
                  ),
            ),
          ),
          Wrap(
            spacing: 8,
            children: prompts
                .map((prompt) => PromptChip(
                      text: prompt['text'] ?? '',
                      onPressed: () => onPromptSelected(prompt['intent'] ?? ''),
                    ))
                .toList(),
          ),
        ],
      ),
    );
  }
}

class PromptChip extends StatelessWidget {
  final String text;
  final VoidCallback onPressed;

  const PromptChip({
    required this.text,
    required this.onPressed,
    Key? key,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return InputChip(
      label: Text(text),
      onPressed: onPressed,
      backgroundColor: Colors.blue[50],
      labelStyle: const TextStyle(
        color: Colors.blue,
        fontWeight: FontWeight.w500,
      ),
    );
  }
}

class ChatLoadingWidget extends StatelessWidget {
  const ChatLoadingWidget({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(strokeWidth: 2),
            const SizedBox(width: 12),
            Text(
              'Thinking...',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}
