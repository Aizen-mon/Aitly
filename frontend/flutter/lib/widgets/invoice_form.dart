import 'package:flutter/material.dart';
import '../services/api.dart';

class InvoiceFormDialog extends StatefulWidget {
  final VoidCallback? onSuccess;

  const InvoiceFormDialog({
    this.onSuccess,
    Key? key,
  }) : super(key: key);

  @override
  _InvoiceFormDialogState createState() => _InvoiceFormDialogState();
}

class _InvoiceFormDialogState extends State<InvoiceFormDialog> {
  final _customerController = TextEditingController();
  final _itemNameController = TextEditingController();
  final _quantityController = TextEditingController();
  final _priceController = TextEditingController();
  final _discountController = TextEditingController();

  List<Map<String, dynamic>> _items = [];
  bool _isLoading = false;
  bool _snapshotLoading = true;
  String? _snapshotError;
  Map<String, dynamic> _snapshot = {};

  @override
  void initState() {
    super.initState();
    _loadTallySnapshot();
  }

  Future<void> _loadTallySnapshot() async {
    try {
      final data = await Api.get('/tally_snapshot?limit=8&days=30&period=today&threshold=10');
      if (!mounted) return;

      setState(() {
        _snapshot = data is Map
            ? Map<String, dynamic>.from(data as Map)
            : <String, dynamic>{};
        _snapshotLoading = false;
        _snapshotError = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _snapshotLoading = false;
        _snapshotError = e.toString();
      });
    }
  }

  void _addItem() {
    if (_itemNameController.text.isEmpty ||
        _quantityController.text.isEmpty ||
        _priceController.text.isEmpty) {
      _showSnackbar('Please fill all item fields');
      return;
    }

    setState(() {
      final discount = _discountController.text.trim().isEmpty
          ? 0.0
          : double.parse(_discountController.text);
      _items.add({
        'name': _itemNameController.text,
        'quantity': int.parse(_quantityController.text),
        'price': double.parse(_priceController.text),
        'discount': discount,
      });
      _itemNameController.clear();
      _quantityController.clear();
      _priceController.clear();
      _discountController.clear();
    });
  }

  void _selectCatalogItem(Map<String, dynamic> item) {
    setState(() {
      _itemNameController.text = item['name']?.toString() ?? '';
      _priceController.text = (item['dp'] ?? item['rate'] ?? 0).toString();
      _discountController.text = (item['discount_percent'] ?? 0).toString();
    });
  }

  void _removeItem(int index) {
    setState(() {
      _items.removeAt(index);
    });
  }

  double _calculateTotal() {
    double total = 0;
    for (var item in _items) {
      final quantity = (item['quantity'] as int);
      final price = (item['price'] as double);
      final discount = (item['discount'] as num?)?.toDouble() ?? 0;
      final discountedPrice = price * (1 - (discount / 100));
      total += quantity * discountedPrice;
    }
    return total;
  }

  void _submitInvoice() async {
    if (_customerController.text.isEmpty) {
      _showSnackbar('Please enter customer name');
      return;
    }

    if (_items.isEmpty) {
      _showSnackbar('Please add at least one item');
      return;
    }

    setState(() => _isLoading = true);

    try {
      final invoiceData = {
        'customer': _customerController.text,
        'items': _items,
        'total': _calculateTotal(),
        'date': DateTime.now().toIso8601String(),
      };

      final response = await Api.post('/create_invoice', invoiceData);

      if (response['status'] == 'success' || response['status'] == 'saved') {
        _showSnackbar('Invoice created successfully!', isSuccess: true);
        widget.onSuccess?.call();
        
        Future.delayed(Duration(seconds: 1), () {
          if (mounted) {
            Navigator.pop(context);
          }
        });
      } else {
        _showSnackbar('Failed to create invoice: ${response['message'] ?? 'Unknown error'}');
      }
    } catch (e) {
      _showSnackbar('Error: ${e.toString()}');
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  void _showSnackbar(String message, {bool isSuccess = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isSuccess ? Colors.green[400] : Colors.red[400],
        duration: const Duration(seconds: 2),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Create New Invoice',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              _buildSnapshotSection(),
              const SizedBox(height: 20),

              // Customer Name Field
              TextField(
                controller: _customerController,
                decoration: InputDecoration(
                  labelText: 'Customer Name',
                  hintText: 'Enter customer name',
                  prefixIcon: const Icon(Icons.person),
                ),
                enabled: !_isLoading,
              ),
              const SizedBox(height: 20),

              // Items Section
              Text(
                'Invoice Items',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 12),

              // Item Input Row
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.grey[300]!),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  children: [
                    TextField(
                      controller: _itemNameController,
                      decoration: InputDecoration(
                        labelText: 'Item Name',
                        hintText: 'e.g., Product X',
                        prefixIcon: const Icon(Icons.shopping_bag),
                        enabled: !_isLoading,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _quantityController,
                            keyboardType: TextInputType.number,
                            decoration: InputDecoration(
                              labelText: 'Qty',
                              prefixIcon: const Icon(Icons.numbers),
                              enabled: !_isLoading,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: TextField(
                            controller: _priceController,
                            keyboardType: TextInputType.number,
                            decoration: InputDecoration(
                              labelText: 'Price',
                              prefixIcon: const Icon(Icons.currency_rupee),
                              enabled: !_isLoading,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    TextField(
                      controller: _discountController,
                      keyboardType: TextInputType.number,
                      decoration: InputDecoration(
                        labelText: 'Discount % (optional)',
                        prefixIcon: const Icon(Icons.percent),
                        enabled: !_isLoading,
                      ),
                    ),
                    const SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: _isLoading ? null : _addItem,
                        icon: const Icon(Icons.add),
                        label: const Text('Add Item'),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Items List
              if (_items.isNotEmpty) ...[
                Container(
                  constraints: const BoxConstraints(maxHeight: 200),
                  child: ListView.builder(
                    shrinkWrap: true,
                    itemCount: _items.length,
                    itemBuilder: (context, index) {
                      final item = _items[index];
                      final quantity = item['quantity'] as int;
                      final price = item['price'] as double;
                      final discount = (item['discount'] as num?)?.toDouble() ?? 0;
                      final subtotal = quantity * price * (1 - (discount / 100));
                      return Card(
                        margin: const EdgeInsets.only(bottom: 8),
                        child: ListTile(
                          title: Text(item['name']),
                          subtitle: Text(
                            'Qty: $quantity × ₹${price.toStringAsFixed(2)}${discount > 0 ? ' - ${discount.toStringAsFixed(0)}%' : ''} = ₹${subtotal.toStringAsFixed(2)}',
                          ),
                          trailing: IconButton(
                            icon: const Icon(Icons.delete, color: Colors.red),
                            onPressed: () => _removeItem(index),
                          ),
                        ),
                      );
                    },
                  ),
                ),
                const SizedBox(height: 12),

                // Total
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.blue[50],
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Total Amount:',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        '₹${_calculateTotal().toStringAsFixed(2)}',
                        style:
                            Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: Colors.green[700],
                        ),
                      ),
                    ],
                  ),
                ),
              ] else
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  child: Text(
                    'No items added yet',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Colors.grey[600],
                    ),
                  ),
                ),

              const SizedBox(height: 24),

              // Action Buttons
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: _isLoading ? null : () => Navigator.pop(context),
                    child: const Text('Cancel'),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton.icon(
                    onPressed:
                        (_isLoading || _items.isEmpty) ? null : _submitInvoice,
                    icon: _isLoading
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                            ),
                          )
                        : const Icon(Icons.check),
                    label: Text(_isLoading ? 'Creating...' : 'Create Invoice'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSnapshotSection() {
    if (_snapshotLoading) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 8),
        child: Center(child: CircularProgressIndicator()),
      );
    }

    if (_snapshotError != null) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.red[50],
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.red[200]!),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Could not load Tally snapshot',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.bold,
                color: Colors.red[700],
              ),
            ),
            const SizedBox(height: 4),
            Text(
              _snapshotError ?? '',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Colors.red[700],
              ),
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: _loadTallySnapshot,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    final inventory = _snapshot['inventory'] as Map?;
    final salesSummary = _snapshot['sales_summary'] as Map?;
    final recentTransactions = (_snapshot['recent_transactions'] as Map?)?['transactions'] as List?;
    final lowStock = (_snapshot['low_stock'] as Map?)?['items'] as List?;
    final quotationContext = _snapshot['quotation_context'] as Map? ?? _snapshot;
    final catalog = quotationContext['catalog'] as List?;
    final previousSales = quotationContext['previous_sales'] as List?;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Tally Snapshot',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _snapshotCard(
                label: 'Inventory Items',
                value: '${inventory?['total_items'] ?? 0}',
                subtitle: 'Available now',
                color: Colors.teal,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _snapshotCard(
                label: 'Today Sales',
                value: '₹${salesSummary?['total'] ?? 0}',
                subtitle: '${salesSummary?['count'] ?? 0} invoices',
                color: Colors.blue,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: _snapshotCard(
                label: 'Low Stock',
                value: '${lowStock?.length ?? 0}',
                subtitle: 'Needs reorder',
                color: Colors.red,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _snapshotCard(
                label: 'Recent Sales',
                value: '${recentTransactions?.length ?? 0}',
                subtitle: 'Last 30 days',
                color: Colors.orange,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        if (inventory?['items'] is List && (inventory['items'] as List).isNotEmpty) ...[
          Text(
            'Available Quantity',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          ...((inventory['items'] as List).take(4).map((item) {
            final map = item is Map ? Map<String, dynamic>.from(item) : <String, dynamic>{};
            return Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      map['name']?.toString() ?? '',
                      style: Theme.of(context).textTheme.bodyMedium,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Text(
                    'Qty: ${map['qty'] ?? 0}',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            );
          })),
        ],
        if (recentTransactions != null && recentTransactions.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text(
            'Previous Sales',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          ...recentTransactions.take(3).map((txn) {
            final map = txn is Map ? Map<String, dynamic>.from(txn) : <String, dynamic>{};
            return Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      '${map['invoice'] ?? map['description'] ?? 'Sale'}',
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Text('₹${map['amount'] ?? 0}'),
                ],
              ),
            );
          }),
        ],
        if (catalog != null && catalog.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text(
            'Quotation Catalog',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          ...catalog.take(5).map((item) {
            final map = item is Map ? Map<String, dynamic>.from(item) : <String, dynamic>{};
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: InkWell(
                onTap: () => _selectCatalogItem(map),
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.blue[50],
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: Colors.blue[100]!),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        map['name']?.toString() ?? '',
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Stock: ${map['stock_qty'] ?? 0} ${map['unit'] ?? ''} | Rate: ₹${map['rate'] ?? 0} | DP: ₹${map['dp'] ?? 0} | Discount: ${map['discount_percent'] ?? 0}%',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Tap to use this item in the quote',
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: Colors.blue[700],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          }),
        ],
        if (previousSales != null && previousSales.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text(
            'Previous Sales History',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          ...previousSales.take(3).map((sale) {
            final map = sale is Map ? Map<String, dynamic>.from(sale) : <String, dynamic>{};
            return Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      '${map['invoice'] ?? 'Sale'} - ${map['party'] ?? ''}',
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Text('₹${map['amount'] ?? 0}'),
                ],
              ),
            );
          }),
        ],
      ],
    );
  }

  Widget _snapshotCard({
    required String label,
    required String value,
    required String subtitle,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: Colors.grey[700],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            subtitle,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Colors.grey[600],
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _customerController.dispose();
    _itemNameController.dispose();
    _quantityController.dispose();
    _priceController.dispose();
    _discountController.dispose();
    super.dispose();
  }
}
