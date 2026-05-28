import 'package:flutter/material.dart';
import '../services/api.dart';

class CustomersScreen extends StatefulWidget {
  const CustomersScreen({Key? key}) : super(key: key);

  @override
  State<CustomersScreen> createState() => _CustomersScreenState();
}

class _CustomersScreenState extends State<CustomersScreen> {
  final _searchController = TextEditingController();
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _gstController = TextEditingController();
  final _addressController = TextEditingController();
  final _dueController = TextEditingController();

  List<Map<String, dynamic>> _customers = [];
  List<Map<String, dynamic>> _filteredCustomers = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadCustomers();
  }

  Future<void> _loadCustomers() async {
    try {
      final data = await Api.get('/customers?per_page=100');
      final items = List<Map<String, dynamic>>.from(data?['items'] ?? []);
      if (!mounted) return;
      setState(() {
        _customers = items.map((item) {
          return {
            'id': item['id'],
            'name': item['customer_name'] ?? 'Unknown Customer',
            'phone': item['phone'] ?? '',
            'gst': item['gst_number'] ?? '',
            'address': item['address'] ?? '',
            'due': (item['pending_due'] as num?)?.toDouble() ?? 0,
            'last_payment_date': item['last_payment_date'],
            'last_payment_amount': (item['last_payment_amount'] as num?)?.toDouble() ?? 0,
            'created_at': item['created_at'] ?? '',
          };
        }).toList();
        _applyFilter();
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
      _showSnackBar('Failed to load customers: $e');
    }
  }

  void _applyFilter() {
    final query = _searchController.text.toLowerCase().trim();
    _filteredCustomers = query.isEmpty
        ? List<Map<String, dynamic>>.from(_customers)
        : _customers.where((customer) {
            final name = customer['name']?.toString().toLowerCase() ?? '';
            final phone = customer['phone']?.toString().toLowerCase() ?? '';
            final gst = customer['gst']?.toString().toLowerCase() ?? '';
            return name.contains(query) || phone.contains(query) || gst.contains(query);
          }).toList();
  }

  Future<void> _addCustomer() async {
    if (_nameController.text.trim().isEmpty) {
      _showSnackBar('Customer name is required');
      return;
    }

    final payload = {
      'customer_name': _nameController.text.trim(),
      'phone': _phoneController.text.trim(),
      'gst_number': _gstController.text.trim(),
      'address': _addressController.text.trim(),
      'pending_due': double.tryParse(_dueController.text.trim()) ?? 0,
    };

    setState(() => _loading = true);
    try {
      final response = await Api.post('/customers', payload);
      if (response == null) {
        throw Exception('No response from server');
      }
      _nameController.clear();
      _phoneController.clear();
      _gstController.clear();
      _addressController.clear();
      _dueController.clear();
      await _loadCustomers();
      _showSnackBar('Customer added successfully', isSuccess: true);
    } catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
      _showSnackBar('Failed to add customer: $e');
    }
  }

  Future<void> _deleteCustomer(int id) async {
    try {
      final response = await Api.delete('/customers/$id');
      if (response == null) {
        throw Exception('Delete failed');
      }
      await _loadCustomers();
      _showSnackBar('Customer removed', isSuccess: true);
    } catch (e) {
      _showSnackBar('Failed to remove customer: $e');
    }
  }

  void _showSnackBar(String message, {bool isSuccess = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isSuccess ? Colors.green[600] : Colors.red[400],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Customers'),
          actions: [
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: _loadCustomers,
            ),
          ],
        ),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : RefreshIndicator(
                onRefresh: _loadCustomers,
                child: ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    TextField(
                      controller: _searchController,
                      onChanged: (_) => setState(_applyFilter),
                      decoration: InputDecoration(
                        prefixIcon: const Icon(Icons.search),
                        hintText: 'Search customers',
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Add Customer', style: Theme.of(context).textTheme.titleMedium),
                            const SizedBox(height: 12),
                            TextField(controller: _nameController, decoration: const InputDecoration(labelText: 'Customer Name *')),
                            TextField(controller: _phoneController, decoration: const InputDecoration(labelText: 'Phone')),
                            TextField(controller: _gstController, decoration: const InputDecoration(labelText: 'GST Number')),
                            TextField(controller: _addressController, decoration: const InputDecoration(labelText: 'Address')),
                            TextField(controller: _dueController, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Pending Due')),
                            const SizedBox(height: 12),
                            SizedBox(
                              width: double.infinity,
                              child: ElevatedButton.icon(
                                onPressed: _addCustomer,
                                icon: const Icon(Icons.person_add),
                                label: const Text('Save Customer'),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Text('Customer List', style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 8),
                    if (_filteredCustomers.isEmpty)
                      const Padding(
                        padding: EdgeInsets.symmetric(vertical: 32),
                        child: Center(child: Text('No customers found')),
                      )
                    else
                      ..._filteredCustomers.map(
                        (customer) => Card(
                          child: ListTile(
                            leading: CircleAvatar(
                              child: Text((customer['name']?.toString() ?? '?').isNotEmpty
                                  ? customer['name'].toString()[0].toUpperCase()
                                  : '?'),
                            ),
                            title: Text(customer['name']?.toString() ?? 'Unknown Customer'),
                            subtitle: Text(
                              [
                                if ((customer['phone'] ?? '').toString().isNotEmpty) 'Phone: ${customer['phone']}',
                                if ((customer['gst'] ?? '').toString().isNotEmpty) 'GST: ${customer['gst']}',
                                if ((customer['due'] ?? 0) > 0) 'Due: ₹${(customer['due'] as num).toStringAsFixed(2)}',
                              ].join(' • '),
                            ),
                            onTap: () => _openCustomerDetails(customer),
                            trailing: IconButton(
                              icon: const Icon(Icons.delete_outline, color: Colors.red),
                              onPressed: customer['id'] is int ? () => _deleteCustomer(customer['id'] as int) : null,
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
      ),
    );
  }

  void _openCustomerDetails(Map<String, dynamic> customer) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => CustomerDetailsScreen(customer: customer, onPaymentRecorded: _loadCustomers),
      ),
    );
  }

  @override
  void dispose() {
    _searchController.dispose();
    _nameController.dispose();
    _phoneController.dispose();
    _gstController.dispose();
    _addressController.dispose();
    _dueController.dispose();
    super.dispose();
  }
}

class CustomerDetailsScreen extends StatefulWidget {
  final Map<String, dynamic> customer;
  final VoidCallback onPaymentRecorded;

  const CustomerDetailsScreen({
    Key? key,
    required this.customer,
    required this.onPaymentRecorded,
  }) : super(key: key);

  @override
  State<CustomerDetailsScreen> createState() => _CustomerDetailsScreenState();
}

class _CustomerDetailsScreenState extends State<CustomerDetailsScreen> {
  final _paymentAmountController = TextEditingController();
  final _paymentNotesController = TextEditingController();

  List<Map<String, dynamic>> _paymentHistory = [];
  Map<String, dynamic>? _dueReminder;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _loadPaymentData();
  }

  Future<void> _loadPaymentData() async {
    try {
      setState(() => _loading = true);
      final customerId = widget.customer['id'];

      // Fetch payment history
      final paymentData = await Api.get('/customers/$customerId/payments?per_page=50');
      final payments = List<Map<String, dynamic>>.from(paymentData?['items'] ?? []);

      // Fetch due reminder
      final reminderData = await Api.get('/customers/$customerId/due_reminder');

      if (!mounted) return;
      setState(() {
        _paymentHistory = payments;
        _dueReminder = reminderData as Map<String, dynamic>?;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
      _showSnackBar('Failed to load payment data: $e');
    }
  }

  Future<void> _recordPayment() async {
    final amount = double.tryParse(_paymentAmountController.text.trim());
    if (amount == null || amount <= 0) {
      _showSnackBar('Enter a valid payment amount');
      return;
    }

    try {
      setState(() => _loading = true);
      final customerId = widget.customer['id'];
      final payload = {
        'amount': amount,
        'payment_date': DateTime.now().toIso8601String().split('T')[0],
        'notes': _paymentNotesController.text.trim(),
      };

      final response = await Api.post('/customers/$customerId/payments', payload);
      if (response == null) {
        throw Exception('Payment recording failed');
      }

      _paymentAmountController.clear();
      _paymentNotesController.clear();
      await _loadPaymentData();
      widget.onPaymentRecorded();
      _showSnackBar('Payment recorded successfully', isSuccess: true);
    } catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
      _showSnackBar('Failed to record payment: $e');
    }
  }

  void _showSnackBar(String message, {bool isSuccess = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isSuccess ? Colors.green[600] : Colors.red[400],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final customerName = widget.customer['name'] ?? 'Customer';
    final due = (widget.customer['due'] as num?)?.toDouble() ?? 0;
    final reminder = _dueReminder?['reminder'] as Map<String, dynamic>?;

    return Scaffold(
      appBar: AppBar(
        title: Text(customerName),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadPaymentData,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadPaymentData,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  // Customer summary
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Customer Details', style: Theme.of(context).textTheme.titleMedium),
                          const SizedBox(height: 12),
                          if ((widget.customer['phone'] ?? '').toString().isNotEmpty)
                            Text('Phone: ${widget.customer['phone']}'),
                          if ((widget.customer['gst'] ?? '').toString().isNotEmpty)
                            Text('GST: ${widget.customer['gst']}'),
                          if ((widget.customer['address'] ?? '').toString().isNotEmpty)
                            Text('Address: ${widget.customer['address']}'),
                          const SizedBox(height: 12),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text('Pending Due:', style: Theme.of(context).textTheme.labelMedium),
                              Text('₹${due.toStringAsFixed(2)}',
                                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                                        color: due > 0 ? Colors.red : Colors.green,
                                        fontWeight: FontWeight.bold,
                                      )),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Due reminder
                  if (reminder != null)
                    Card(
                      color: Colors.orange[50],
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Row(
                          children: [
                            Icon(Icons.warning_amber_rounded, color: Colors.orange[700]),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('Payment Reminder',
                                      style: Theme.of(context).textTheme.labelMedium?.copyWith(fontWeight: FontWeight.bold)),
                                  Text(reminder['message']?.toString() ?? 'Payment overdue',
                                      style: Theme.of(context).textTheme.bodySmall),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  const SizedBox(height: 16),

                  // Record payment form
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Record Payment', style: Theme.of(context).textTheme.titleMedium),
                          const SizedBox(height: 12),
                          TextField(
                            controller: _paymentAmountController,
                            keyboardType: TextInputType.number,
                            decoration: const InputDecoration(
                              labelText: 'Payment Amount *',
                              prefixText: '₹ ',
                            ),
                          ),
                          const SizedBox(height: 8),
                          TextField(
                            controller: _paymentNotesController,
                            maxLines: 2,
                            decoration: const InputDecoration(
                              labelText: 'Notes (optional)',
                              hintText: 'e.g., Cheque #12345',
                            ),
                          ),
                          const SizedBox(height: 12),
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton.icon(
                              onPressed: _recordPayment,
                              icon: const Icon(Icons.payment),
                              label: const Text('Record Payment'),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Payment history
                  Text('Payment History', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  if (_paymentHistory.isEmpty)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 24),
                      child: Center(child: Text('No payments recorded yet')),
                    )
                  else
                    ..._paymentHistory.map((payment) {
                      return Card(
                        child: ListTile(
                          leading: const Icon(Icons.receipt),
                          title: Text('₹${(payment['amount'] as num?)?.toStringAsFixed(2) ?? '0'}'),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Date: ${payment['payment_date'] ?? 'N/A'}'),
                              if ((payment['notes'] ?? '').toString().isNotEmpty)
                                Text('Notes: ${payment['notes']}'),
                            ],
                          ),
                        ),
                      );
                    }),
                ],
              ),
            ),
    );
  }

  @override
  void dispose() {
    _paymentAmountController.dispose();
    _paymentNotesController.dispose();
    super.dispose();
  }
}