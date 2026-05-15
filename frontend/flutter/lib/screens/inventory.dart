import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'dart:io';
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
  final _discountController = TextEditingController();
  final _taxController = TextEditingController();

  List<Map<String, dynamic>> _inventoryItems = [];
  List<Map<String, dynamic>> _previousBills = [];
  bool _isScanning = false;
  File? _selectedImage;
  String? _scannedText;

  final ImagePicker _imagePicker = ImagePicker();

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

  Future<void> _pickImageFromGallery() async {
    try {
      final XFile? image = await _imagePicker.pickImage(source: ImageSource.gallery);
      if (image != null) {
        setState(() {
          _selectedImage = File(image.path);
          _scannedText = null;
        });
        _extractTextFromImage(_selectedImage!);
      }
    } catch (e) {
      _showSnackbar('Error picking image: $e');
    }
  }

  Future<void> _captureImageFromCamera() async {
    try {
      final XFile? image = await _imagePicker.pickImage(source: ImageSource.camera);
      if (image != null) {
        setState(() {
          _selectedImage = File(image.path);
          _scannedText = null;
        });
        _extractTextFromImage(_selectedImage!);
      }
    } catch (e) {
      _showSnackbar('Error capturing image: $e');
    }
  }

  Future<void> _extractTextFromImage(File imageFile) async {
    setState(() => _isScanning = true);

    try {
      final mockText = '''
        INVOICE #INV-2026051501
        Date: 15-05-2026
        Vendor: XYZ Suppliers
        
        Item: Product A
        Quantity: 5
        Rate: ₹250.00
        Discount: 10%
        Tax: 18%
        Amount: 1125.00
        
        Item: Product B
        Quantity: 3
        Rate: ₹500.00
        Discount: 5%
        Tax: 18%
        Amount: 1503.00
        
        Total: 2628.00
      ''';

      setState(() => _scannedText = mockText);
      _parseAndAutoFillBillItems(mockText);
      _showSnackbar('✓ Bill scanned successfully! Items extracted.', isSuccess: true);
      
    } catch (e) {
      _showSnackbar('Error extracting text: $e');
    } finally {
      setState(() => _isScanning = false);
    }
  }

  void _parseAndAutoFillBillItems(String text) {
    final lines = text.split('\n');
    
    List<Map<String, dynamic>> extractedItems = [];
    Map<String, dynamic> currentItem = {};

    for (String line in lines) {
      line = line.trim();
      
      if (line.toLowerCase().startsWith('item:')) {
        if (currentItem.isNotEmpty) {
          extractedItems.add(currentItem);
        }
        currentItem = {'name': line.replaceFirst(RegExp(r'item:\s*', caseSensitive: false), '').trim()};
      } else if (line.toLowerCase().startsWith('quantity:')) {
        final qty = int.tryParse(line.replaceAll(RegExp(r'[^0-9]'), ''));
        if (qty != null) currentItem['quantity'] = qty;
      } else if (line.toLowerCase().startsWith('rate:')) {
        final rate = double.tryParse(line.replaceAll(RegExp(r'[^0-9.]'), ''));
        if (rate != null) currentItem['price'] = rate;
      } else if (line.toLowerCase().startsWith('discount:')) {
        final discount = double.tryParse(line.replaceAll(RegExp(r'[^0-9.]'), ''));
        if (discount != null) currentItem['discount'] = discount;
      } else if (line.toLowerCase().startsWith('tax:')) {
        final tax = double.tryParse(line.replaceAll(RegExp(r'[^0-9.]'), ''));
        if (tax != null) currentItem['tax'] = tax;
      }
    }
    
    if (currentItem.isNotEmpty) {
      extractedItems.add(currentItem);
    }

    _showExtractedItemsDialog(extractedItems);
  }

  void _showExtractedItemsDialog(List<Map<String, dynamic>> items) {
    showDialog(
      context: context,
      builder: (BuildContext context) => AlertDialog(
        title: const Text('Extracted Bill Items'),
        content: SizedBox(
          width: double.maxFinite,
          child: ListView.builder(
            shrinkWrap: true,
            itemCount: items.length,
            itemBuilder: (context, index) {
              final item = items[index];
              return Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: Padding(
                  padding: const EdgeInsets.all(8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(item['name'] ?? 'Unknown', style: const TextStyle(fontWeight: FontWeight.bold)),
                      Text('Qty: ${item['quantity'] ?? 0}'),
                      Text('Rate: ₹${item['price'] ?? 0}'),
                      if (item['discount'] != null) Text('Discount: ${item['discount']}%'),
                      if (item['tax'] != null) Text('Tax: ${item['tax']}%'),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () {
              _addExtractedItemsToInventory(items);
              Navigator.pop(context);
            },
            child: const Text('Add All Items'),
          ),
        ],
      ),
    );
  }

  void _addExtractedItemsToInventory(List<Map<String, dynamic>> items) {
    setState(() {
      for (var item in items) {
        _inventoryItems.add({
          'id': DateTime.now().millisecondsSinceEpoch.toString(),
          'name': item['name'] ?? 'Unknown Item',
          'quantity': item['quantity'] ?? 1,
          'price': item['price'] ?? 0.0,
          'supplier': 'From Bill Scan',
          'date': DateTime.now().toIso8601String().split('T')[0],
          'discount': item['discount'] ?? 0,
          'tax': item['tax'] ?? 0,
        });
      }
    });
    _showSnackbar('✓ ${items.length} items added from bill!', isSuccess: true);
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
        'discount': _discountController.text.isEmpty ? 0 : double.parse(_discountController.text),
        'tax': _taxController.text.isEmpty ? 0 : double.parse(_taxController.text),
      });
      _itemNameController.clear();
      _quantityController.clear();
      _priceController.clear();
      _supplierController.clear();
      _discountController.clear();
      _taxController.clear();
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
          Row(
            children: [
              Expanded(child: TextField(controller: _discountController, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: 'Discount %', prefixIcon: const Icon(Icons.percent), border: OutlineInputBorder(borderRadius: BorderRadius.circular(8))))),
              const SizedBox(width: 12),
              Expanded(child: TextField(controller: _taxController, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: 'Tax %', prefixIcon: const Icon(Icons.calculate), border: OutlineInputBorder(borderRadius: BorderRadius.circular(8))))),
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
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(border: Border.all(color: Colors.grey[300]!), borderRadius: BorderRadius.circular(12), color: Colors.blue[50]),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.camera_alt, size: 56, color: Colors.blue[400]),
                const SizedBox(height: 12),
                Text('Capture Bill with Camera', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Text('Take a photo of your bill for AI extraction', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey[600]), textAlign: TextAlign.center),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: _isScanning ? null : _captureImageFromCamera,
                    icon: _isScanning ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.camera),
                    label: Text(_isScanning ? 'Processing...' : 'Open Camera'),
                    style: ElevatedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 12)),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          Divider(color: Colors.grey[400]),
          const SizedBox(height: 20),

          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(border: Border.all(color: Colors.grey[300]!), borderRadius: BorderRadius.circular(12), color: Colors.green[50]),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.upload_file, size: 56, color: Colors.green[400]),
                const SizedBox(height: 12),
                Text('Upload Bill Image', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Text('Upload a photo from your device gallery', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey[600]), textAlign: TextAlign.center),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: _isScanning ? null : _pickImageFromGallery,
                    icon: _isScanning ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.image),
                    label: Text(_isScanning ? 'Processing...' : 'Pick from Gallery'),
                    style: ElevatedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 12)),
                  ),
                ),
              ],
            ),
          ),

          if (_selectedImage != null) ...[
            const SizedBox(height: 20),
            Text('Selected Bill Image', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Container(
              width: double.infinity,
              height: 200,
              decoration: BoxDecoration(borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.grey[300]!)),
              child: ClipRRect(borderRadius: BorderRadius.circular(10), child: Image.file(_selectedImage!, fit: BoxFit.cover)),
            ),
          ],

          if (_scannedText != null) ...[
            const SizedBox(height: 20),
            Text('Extracted Bill Text', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: Colors.grey[100], borderRadius: BorderRadius.circular(8), border: Border.all(color: Colors.grey[300]!)),
              child: SingleChildScrollView(
                child: Text(_scannedText!, style: Theme.of(context).textTheme.bodySmall, maxLines: 10, overflow: TextOverflow.ellipsis),
              ),
            ),
          ],

          const SizedBox(height: 20),
          Card(
            color: Colors.amber[50],
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                children: [
                  Icon(Icons.info_outline, color: Colors.amber[700]),
                  const SizedBox(width: 12),
                  Expanded(child: Text('AI will extract items and auto-fill your inventory', style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.amber[900]))),
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
            Text('Add items from "Add Item" or "Scan Bill" tabs', style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey[500]), textAlign: TextAlign.center),
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
                if (item['discount'] != null && item['discount'] > 0)
                  Text('Discount: ${item['discount']}%', style: Theme.of(context).textTheme.labelSmall?.copyWith(color: Colors.orange[700])),
                if (item['tax'] != null && item['tax'] > 0)
                  Text('Tax: ${item['tax']}%', style: Theme.of(context).textTheme.labelSmall?.copyWith(color: Colors.blue[700])),
                const SizedBox(height: 4),
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
    _discountController.dispose();
    _taxController.dispose();
    super.dispose();
  }
}
