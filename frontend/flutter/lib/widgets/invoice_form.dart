import 'package:flutter/material.dart';
import '../services/api.dart';

class InvoiceFormDialog extends StatefulWidget {
  final VoidCallback? onSuccess;
  final Map<String, dynamic>? prefill;

  const InvoiceFormDialog({
    this.onSuccess,
    this.prefill,
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
  List<Map<String, dynamic>> _availableItems = [];
  List<Map<String, dynamic>> _filteredItems = [];
  bool _isLoading = false;
  bool _snapshotLoading = true;
  String? _snapshotError;
  Map<String, dynamic> _snapshot = {};
  bool _showItemSuggestions = false;

  @override
  void initState() {
    super.initState();
    _itemNameController.addListener(_onItemNameChanged);
    _loadTallySnapshot();
    // Apply prefill if provided
    final pre = widget.prefill;
    if (pre != null) {
      try {
        final party = pre['party_name'] ?? pre['customer_name'] ?? pre['party'] ?? pre['customer'] ?? '';
        if (party.toString().isNotEmpty) {
          _customerController.text = party.toString();
        }

        final items = pre['items'] as List? ?? pre['line_items'] as List? ?? [];
        if (items.isNotEmpty) {
          for (var raw in items) {
            if (raw is Map) {
              final name = raw['name'] ?? raw['item_name'] ?? raw['product'] ?? '';
              final qty = (raw['qty'] ?? raw['quantity'] ?? raw['count'] ?? 1);
              final rate = (raw['rate'] ?? raw['price'] ?? raw['amount'] ?? 0);
              final discount = (raw['discount_percent'] ?? raw['discount'] ?? 0);
              _items.add({
                'name': name?.toString() ?? '',
                'quantity': (qty is num) ? qty.toInt() : int.tryParse(qty.toString()) ?? 1,
                'price': (rate is num) ? rate.toDouble() : double.tryParse(rate.toString()) ?? 0.0,
                'discount': (discount is num) ? discount.toDouble() : double.tryParse(discount.toString()) ?? 0.0,
              });
            }
          }
        }
      } catch (e) {
        // ignore prefill errors and continue with empty form
      }
    }
  }

  void _onItemNameChanged() {
    final query = _itemNameController.text.toLowerCase().trim();
    
    setState(() {
      if (query.isEmpty) {
        _filteredItems = [];
        _showItemSuggestions = false;
      } else {
        _filteredItems = _availableItems.where((item) {
          final name = item['name']?.toString().toLowerCase() ?? '';
          return name.contains(query);
        }).toList();
        _showItemSuggestions = _filteredItems.isNotEmpty;
      }
    });
  }

  Future<void> _loadTallySnapshot() async {
    try {
      final data = await Api.get('/tally_snapshot?limit=8&days=30&period=today&threshold=10');
      if (!mounted) return;

      setState(() {
        _snapshot = data is Map
          ? Map<String, dynamic>.from(data)
            : <String, dynamic>{};
        
        // Extract available items from catalog and inventory
        final quotationContext = _snapshot['quotation_context'] as Map? ?? _snapshot;
        final catalog = quotationContext['catalog'] as List? ?? [];
        final inventory = _snapshot['inventory'] as Map?;
        final inventoryItems = (inventory?['items'] as List?) ?? [];
        
        // Build combined list of available items
        _availableItems = [];
        
        // Add catalog items
        for (var item in catalog) {
          if (item is Map) {
            _availableItems.add(Map<String, dynamic>.from(item));
          }
        }
        
        // Add inventory items if not already in catalog
        for (var item in inventoryItems) {
          if (item is Map) {
            final itemMap = Map<String, dynamic>.from(item);
            final name = itemMap['name']?.toString().toLowerCase() ?? '';
            if (!_availableItems.any((i) => (i['name']?.toString().toLowerCase() ?? '') == name)) {
              _availableItems.add(itemMap);
            }
          }
        }
        
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
      _priceController.text = (item['dp'] ?? item['rate'] ?? item['price'] ?? 0).toString();
      _discountController.text = (item['discount_percent'] ?? item['discount'] ?? 0).toString();
      _showItemSuggestions = false;
      _filteredItems = [];
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
      // Generate invoice number (format: INV-YYYYMMDD-HHMMSS)
      final now = DateTime.now();
      final invoiceNo = 'INV-${now.year}${now.month.toString().padLeft(2, '0')}${now.day.toString().padLeft(2, '0')}-${now.hour.toString().padLeft(2, '0')}${now.minute.toString().padLeft(2, '0')}${now.second.toString().padLeft(2, '0')}';
      
      // Format date as YYYYMMDD for Tally
      final dateStr = '${now.year}${now.month.toString().padLeft(2, '0')}${now.day.toString().padLeft(2, '0')}';
      
      // Transform items: rename quantity→qty, price→rate
      final transformedItems = _items.map((item) {
        final discountAmount = (item['price'] as double) * (item['discount'] as double) / 100;
        final finalRate = (item['price'] as double) - discountAmount;
        return {
          'name': item['name'],
          'qty': item['quantity'],
          'rate': finalRate,
          'original_price': item['price'],
          'discount_percent': item['discount'],
        };
      }).toList();

      // Build invoice data matching Tally backend format
      final invoiceData = {
        'invoice_no': invoiceNo,
        'date': dateStr,
        'party_name': _customerController.text,
        'items': transformedItems,
        'total': _calculateTotal(),
      };

      // Send to Tally backend (will attempt Tally push, fallback to pending queue)
      final response = await Api.post('/send_invoice', invoiceData);

      if (response != null) {
        final status = response['status'];
        if (status == 'sent') {
          _showSnackbar('✓ Invoice sent to Tally successfully!', isSuccess: true);
        } else if (status == 'pending') {
          _showSnackbar('⏳ Tally offline. Invoice saved as pending.', isSuccess: true);
        } else {
          _showSnackbar('Invoice saved. Status: ${response['status'] ?? 'unknown'}', isSuccess: true);
        }
        
        widget.onSuccess?.call();
        Future.delayed(Duration(seconds: 2), () {
          if (mounted) {
            Navigator.pop(context);
          }
        });
      } else {
        _showSnackbar('Failed to process invoice');
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
              // ==================== HEADER ====================
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Create Invoice & Bill',
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
              const SizedBox(height: 4),
              Text(
                'Build quotations with Tally data and send to Tally',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Colors.grey[600],
                ),
              ),
              const Divider(height: 24),

              // ==================== QUOTATION REFERENCE SECTION ====================
              _buildSnapshotSection(),
              const Divider(height: 24),

              // ==================== CUSTOMER DETAILS ====================
              Text(
                'Customer Details',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _customerController,
                decoration: InputDecoration(
                  labelText: 'Customer Name *',
                  hintText: 'Enter customer name or select from history',
                  prefixIcon: const Icon(Icons.person_outline),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
                enabled: !_isLoading,
              ),
              const SizedBox(height: 20),

              // ==================== BILLING SECTION ====================
              Container(
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.blue[200]!),
                  borderRadius: BorderRadius.circular(12),
                  color: Colors.blue[50],
                ),
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.receipt_long, color: Colors.blue[700]),
                        const SizedBox(width: 8),
                        Text(
                          'Billing Items',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                            color: Colors.blue[900],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),

                    // Item Input Form
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        border: Border.all(color: Colors.grey[300]!),
                        borderRadius: BorderRadius.circular(8),
                        color: Colors.white,
                      ),
                      child: Column(
                        children: [
                          // Item Name Input with Autocomplete
                          Column(
                            children: [
                              TextField(
                                controller: _itemNameController,
                                decoration: InputDecoration(
                                  labelText: 'Item Name *',
                                  hintText: 'Enter product name (or tap catalog below)',
                                  prefixIcon: const Icon(Icons.shopping_bag_outlined),
                                  suffixIcon: _itemNameController.text.isNotEmpty
                                      ? IconButton(
                                          icon: const Icon(Icons.clear),
                                          onPressed: () {
                                            setState(() {
                                              _itemNameController.clear();
                                              _filteredItems = [];
                                              _showItemSuggestions = false;
                                            });
                                          },
                                        )
                                      : null,
                                  border: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                ),
                                enabled: !_isLoading,
                                onChanged: (_) => _onItemNameChanged(),
                              ),
                              // Autocomplete Suggestions Dropdown
                              if (_showItemSuggestions && _filteredItems.isNotEmpty)
                                Container(
                                  margin: const EdgeInsets.only(top: 4),
                                  decoration: BoxDecoration(
                                    border: Border.all(color: Colors.grey[300]!),
                                    borderRadius: BorderRadius.circular(6),
                                    color: Colors.white,
                                  ),
                                  constraints: BoxConstraints(
                                    maxHeight: 200,
                                  ),
                                  child: ListView.builder(
                                    shrinkWrap: true,
                                    itemCount: _filteredItems.length,
                                    itemBuilder: (context, index) {
                                      final item = _filteredItems[index];
                                      final name = item['name']?.toString() ?? '';
                                      final stock = item['stock_qty'] ?? item['qty'] ?? 'N/A';
                                      final rate = item['rate'] ?? item['dp'] ?? item['price'] ?? 0;
                                      
                                      return Material(
                                        child: InkWell(
                                          onTap: () {
                                            _selectCatalogItem(item);
                                            FocusScope.of(context).unfocus();
                                          },
                                          child: Padding(
                                            padding: const EdgeInsets.symmetric(
                                              horizontal: 12,
                                              vertical: 10,
                                            ),
                                            child: Column(
                                              crossAxisAlignment: CrossAxisAlignment.start,
                                              children: [
                                                Text(
                                                  name,
                                                  style: const TextStyle(
                                                    fontWeight: FontWeight.w600,
                                                    fontSize: 14,
                                                  ),
                                                ),
                                                const SizedBox(height: 4),
                                                Row(
                                                  mainAxisAlignment:
                                                      MainAxisAlignment.spaceBetween,
                                                  children: [
                                                    Text(
                                                      'Stock: $stock | Rate: ₹$rate',
                                                      style: TextStyle(
                                                        fontSize: 12,
                                                        color: Colors.grey[600],
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                              ],
                                            ),
                                          ),
                                        ),
                                      );
                                    },
                                  ),
                                ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          Row(
                            children: [
                              Expanded(
                                child: TextField(
                                  controller: _quantityController,
                                  keyboardType: TextInputType.number,
                                  decoration: InputDecoration(
                                    labelText: 'Qty *',
                                    prefixIcon: const Icon(Icons.numbers),
                                    border: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                  ),
                                  enabled: !_isLoading,
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: TextField(
                                  controller: _priceController,
                                  keyboardType: TextInputType.number,
                                  decoration: InputDecoration(
                                    labelText: 'Rate (₹) *',
                                    prefixIcon: const Icon(Icons.currency_rupee),
                                    border: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                  ),
                                  enabled: !_isLoading,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          TextField(
                            controller: _discountController,
                            keyboardType: TextInputType.number,
                            decoration: InputDecoration(
                              labelText: 'Discount % (optional)',
                              prefixIcon: const Icon(Icons.percent),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(6),
                              ),
                            ),
                            enabled: !_isLoading,
                          ),
                          const SizedBox(height: 12),
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton.icon(
                              onPressed: _isLoading ? null : _addItem,
                              icon: const Icon(Icons.add_circle_outline),
                              label: const Text('Add Item to Bill'),
                              style: ElevatedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(vertical: 12),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Items List / Bill Table
                    if (_items.isNotEmpty) ...[
                      Text(
                        'Bill Summary',
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Container(
                        constraints: const BoxConstraints(maxHeight: 250),
                        decoration: BoxDecoration(
                          border: Border.all(color: Colors.grey[300]!),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: ListView.builder(
                          shrinkWrap: true,
                          itemCount: _items.length,
                          itemBuilder: (context, index) {
                            final item = _items[index];
                            final quantity = item['quantity'] as int;
                            final price = item['price'] as double;
                            final discount = (item['discount'] as num?)?.toDouble() ?? 0;
                            final subtotal = quantity * price * (1 - (discount / 100));
                            
                            return Column(
                              children: [
                                Padding(
                                  padding: const EdgeInsets.all(12),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                        children: [
                                          Expanded(
                                            child: Text(
                                              item['name'],
                                              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                                fontWeight: FontWeight.bold,
                                              ),
                                              overflow: TextOverflow.ellipsis,
                                            ),
                                          ),
                                          IconButton(
                                            icon: const Icon(Icons.delete_outline, color: Colors.red),
                                            onPressed: () => _removeItem(index),
                                            constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                                            padding: EdgeInsets.zero,
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 6),
                                      Row(
                                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                        children: [
                                          Text(
                                            '$quantity × ₹${price.toStringAsFixed(2)}',
                                            style: Theme.of(context).textTheme.bodyMedium,
                                          ),
                                          if (discount > 0)
                                            Text(
                                              '- ${discount.toStringAsFixed(0)}%',
                                              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                                color: Colors.orange[700],
                                                fontWeight: FontWeight.w600,
                                              ),
                                            ),
                                        ],
                                      ),
                                      const SizedBox(height: 4),
                                      Row(
                                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                        children: [
                                          const Text('Subtotal:'),
                                          Text(
                                            '₹${subtotal.toStringAsFixed(2)}',
                                            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                              fontWeight: FontWeight.w600,
                                              color: Colors.green[700],
                                            ),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                                Divider(height: 1, color: Colors.grey[300]),
                              ],
                            );
                          },
                        ),
                      ),
                      const SizedBox(height: 12),

                      // Total Amount Box
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: Colors.green[50],
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.green[300]!),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              'Total Bill Amount:',
                              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            Text(
                              '₹${_calculateTotal().toStringAsFixed(2)}',
                              style: Theme.of(context).textTheme.titleMedium?.copyWith(
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
                        child: Center(
                          child: Text(
                            'No items added yet. Fill details and click "Add Item to Bill"',
                            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: Colors.grey[600],
                            ),
                            textAlign: TextAlign.center,
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              // ==================== ACTION BUTTONS ====================
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: _isLoading ? null : () => Navigator.pop(context),
                    child: const Text('Cancel'),
                  ),
                  const SizedBox(width: 12),
                  ElevatedButton.icon(
                    onPressed: (_isLoading || _items.isEmpty) ? null : _submitInvoice,
                    icon: _isLoading
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.cloud_upload_outlined),
                    label: Text(_isLoading ? 'Sending to Tally...' : 'Send to Tally'),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 24,
                        vertical: 12,
                      ),
                    ),
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
        if (inventory != null && inventory['items'] is List && (inventory['items'] as List).isNotEmpty) ...[
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
    _itemNameController.removeListener(_onItemNameChanged);
    _itemNameController.dispose();
    _quantityController.dispose();
    _priceController.dispose();
    _discountController.dispose();
    super.dispose();
  }
}
