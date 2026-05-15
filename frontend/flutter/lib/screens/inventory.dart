import 'package:flutter/material.dart';
import '../services/api.dart';

class InventoryScreen extends StatefulWidget {
  const InventoryScreen({Key? key}) : super(key: key);

  @override
  _InventoryScreenState createState() => _InventoryScreenState();
}

class _InventoryScreenState extends State<InventoryScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final _itemNameController = TextEditingController();
  final _quantityController = TextEditingController();
  final _priceController = TextEditingController();
  final _supplierController = TextEditingController();

  List<Map<String, dynamic>> _inventoryItems = [];
  List<Map<String, dynamic>> _previousBills = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadInventory();
    _loadPreviousBills();
  }

  Future<void> _loadInventory() async {
    setState(() {
      _inventoryItems = [
        {'id': '1', 'name': 'Item A', 'quantity': 10, 'price': 500.0, 'supplier': 'Supplier 1', 'date': '2026-05-15'},
        {'id': '2', 'name': 'Item B', 'quantity': 5, 'price': 300.0, 'supplier': 'Supplier 2', 'date': '2026-05-14'},
      ];
    });
  }

  Future<void> _loadPreviousBills() async {
    try {
      final response = await Api.get('/tally_snapshot?limit=10');
      if (response != null) {
        final previousSales = response['quotation_context']?['previous_sales'] as List? ?? [];
        setState(() {
          _previousBills = previousSales.cast<Map<String, dynamic>>();
        });
      }
    } catch (e) {
      print('Error loading bills: $e');
    }
  }

  void _addInventoryItem() {
    if (_itemNameController.text.isEmpty ||
        _quantityController.text.isEmpty ||
        _priceController.text.isEmpty) {
      _showSnackbar('Please fill all required fields');
      return;
    }

    setState(() {
      _inventoryItems.add({
        'id': DateTime.now().millisecondsSinceEpoch.toString(),
        'name': _itemNameController.text,
        'quantity': int.parse(_quantityController.text),
        'price': double.parse(_priceController.text),
        'supplier': _supplierController.text.isEmpty ? 'Not specified' : _supplierController.text,
        'date': DateTime.now().toIso8601String().split('T')[0],
      });
      _itemNameController.clear();
      _quantityController.clear();
      _priceController.clear();
      _supplierController.clear();
    });

    _showSnackbar('Item added to inventory!', isSuccess: true);
  }

  void _addFromPreviousBill(Map<String, dynamic> bill) {
    setState(() {
      _itemNameController.text = bill['invoice'] ?? bill['party'] ?? '';
      _priceController.text = (bill['amount'] ?? 0).toString();
      _supplierController.text = bill['party'] ?? '';
    });
    _showSnackbar('Bill details loaded! Review and add to inventory.', isSuccess: true);
  }

  void _removeInventoryItem(int index) {
    setState(() => _inventoryItems.removeAt(index));
    _showSnackbar('Item removed', isSuccess: true);
  }

  void _showSnackbar(String message, {bool isSuccess = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isSuccess ? Colors.green[400] : Colors.orange[400],
        duration: const Duration(seconds: 2),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Inventory & Bill Scanning'),
        elevation: 0,
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.add_box), text: 'Add Item'),
            Tab(icon: Icon(Icons.receipt), text: 'Scan Bill'),
            Tab(icon: Icon(Icons.inventory_2), text: 'Inventory'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [_buildAddItemTab(), _buildScanBillTab(), _buildInventoryTab()],
      ),
    );
  }

  Widget _buildAddItemTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Add New Inventory Item', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          TextField(controller: _itemNameController, decoration: InputDecoration(labelText: 'Item Name *', hintText: 'e.g., Product X', prefixIcon: const Icon(Icons.shopping_bag_outlined), border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)))),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(child: TextField(controller: _quantityController, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: 'Quantity *', prefixIcon: const Icon(Icons.numbers), border: OutlineInputBorder(borderRadius: BorderRadius.circular(8))))),
              const SizedBox(width: 12),
              Expanded(child: TextField(controller: _priceController, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: 'Price (₹) *', prefixIcon: const Icon(Icons.currency_rupee), border: OutlineInputBorder(borderRadius: BorderRadius.circular(8))))),
            ],
          ),
          const SizedBox(height: 12),
          TextField(controller: _supplierController, decoration: InputDecoration(labelText: 'Supplier (optional)', hintText: 'Supplier name', prefixIcon: const Icon(Icons.store_outlined), border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)))),
          const SizedBox(height: 24),
          SizedBox(width: double.infinity, child: ElevatedButton.icon(onPressed: _addInventoryItem, icon: const Icon(Icons.add_circle_outline), label: const Text('Add to Inventory'), style: ElevatedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 14)))),
          const SizedBox(height: 32),
          if (_previousBills.isNotEmpty) ...[
            Text('Quick Add from Recent Bills', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            ..._previousBills.take(5).map((bill) => Card(
              child: ListTile(
                leading: const Icon(Icons.receipt_long, color: Colors.blue),
                title: Text(bill['invoice'] ?? bill['party'] ?? 'Bill'),
                subtitle: Text('₹${bill['amount'] ?? 0}'),
                trailing: IconButton(icon: const Icon(Icons.add, color: Colors.green), onPressed: () => _addFromPreviousBill(bill)),
              ),
            )),
          ],
        ],
      ),
    );
  }

  Widget _buildScanBillTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Scan or Upload Bill', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 24),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(32),
            decoration: BoxDecoration(border: Border.all(color: Colors.grey[300]!), borderRadius: BorderRadius.circular(12), color: Colors.blue[50]),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.camera_alt, size: 64, color: Colors.blue[400]),
                const SizedBox(height: 16),
                Text('Scan Bill with Camera', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Text('AI will automatically extract items and prices', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey[600]), textAlign: TextAlign.center),
                const SizedBox(height: 20),
                ElevatedButton.icon(onPressed: () => _showSnackbar('Camera feature coming soon!'), icon: const Icon(Icons.camera), label: const Text('Open Camera')),
              ],
            ),
          ),
          const SizedBox(height: 24),
          Divider(color: Colors.grey[400]),
          const SizedBox(height: 24),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(32),
            decoration: BoxDecoration(border: Border.all(color: Colors.grey[300]!), borderRadius: BorderRadius.circular(12), color: Colors.green[50]),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.upload_file, size: 64, color: Colors.green[400]),
                const SizedBox(height: 16),
                Text('Upload Bill Image or PDF', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Text('Upload a photo or PDF of your bill for processing', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey[600]), textAlign: TextAlign.center),
                const SizedBox(height: 20),
                ElevatedButton.icon(onPressed: () => _showSnackbar('File upload feature coming soon!'), icon: const Icon(Icons.file_upload), label: const Text('Upload File')),
              ],
            ),
          ),
          const SizedBox(height: 24),
          Card(
            color: Colors.amber[50],
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                children: [
                  Icon(Icons.info_outline, color: Colors.amber[700]),
                  const SizedBox(width: 12),
                  Expanded(child: Text('Tap "Add Item" tab to auto-fill from previous bills', style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.amber[900]))),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInventoryTab() {
    if (_inventoryItems.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.inventory_2_outlined, size: 64, color: Colors.grey[400]),
            const SizedBox(height: 16),
            Text('No inventory items yet', style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.grey[600])),
            const SizedBox(height: 8),
            Text('Add items from the "Add Item" or "Scan Bill" tab', style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey[500]), textAlign: TextAlign.center),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: _inventoryItems.length,
      itemBuilder: (context, index) {
        final item = _inventoryItems[index];
        final total = (item['quantity'] as int) * (item['price'] as double);

        return Card(
          margin: const EdgeInsets.only(bottom: 12),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(item['name'], style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold), overflow: TextOverflow.ellipsis),
                          const SizedBox(height: 4),
                          Text('Supplier: ${item['supplier']}', style: Theme.of(context).textTheme.bodySmall, overflow: TextOverflow.ellipsis),
                        ],
                      ),
                    ),
                    IconButton(icon: const Icon(Icons.delete_outline, color: Colors.red), onPressed: () => _removeInventoryItem(index)),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Quantity', style: Theme.of(context).textTheme.labelSmall),
                        Text('${item['quantity']} units', style: Theme.of(context).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600)),
                      ],
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text('Unit Price', style: Theme.of(context).textTheme.labelSmall),
                        Text('₹${(item['price'] as double).toStringAsFixed(2)}', style: Theme.of(context).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600)),
                      ],
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text('Total', style: Theme.of(context).textTheme.labelSmall),
                        Text('₹${total.toStringAsFixed(2)}', style: Theme.of(context).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600, color: Colors.green[700])),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text('Added: ${item['date']}', style: Theme.of(context).textTheme.labelSmall?.copyWith(color: Colors.grey[600])),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  void dispose() {
    _tabController.dispose();
    _itemNameController.dispose();
    _quantityController.dispose();
    _priceController.dispose();
    _supplierController.dispose();
    super.dispose();
  }
}
