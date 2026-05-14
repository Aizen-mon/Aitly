import 'package:flutter/material.dart';
import '../services/api.dart';

class DashboardScreen extends StatefulWidget {
  @override
  _DashboardScreenState createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic> dashboard = {};
  bool loading = true;
  String? errorMessage;

  @override
  void initState() {
    super.initState();
    fetchDashboardData();
  }

  fetchDashboardData() async {
    try {
      setState(() => loading = true);
      final data = await Api.get('/dashboard_summary');
      if (!mounted) return;
      setState(() {
        dashboard = (data is Map)
            ? Map<String, dynamic>.from(data as Map)
            : <String, dynamic>{};
        loading = false;
        errorMessage = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        loading = false;
        errorMessage = e.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Business Dashboard'),
          centerTitle: false,
          elevation: 0,
          backgroundColor: Colors.white,
          foregroundColor: Colors.black87,
        ),
        body: RefreshIndicator(
          onRefresh: () async => fetchDashboardData(),
          child: loading
              ? const Center(child: CircularProgressIndicator())
              : errorMessage != null
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.error_outline, size: 48, color: Colors.red[300]),
                          const SizedBox(height: 16),
                          Text('Could not load data',
                              style: Theme.of(context).textTheme.headlineSmall),
                          const SizedBox(height: 8),
                          Text(errorMessage ?? '',
                              style: Theme.of(context).textTheme.bodyMedium,
                              textAlign: TextAlign.center),
                          const SizedBox(height: 24),
                          ElevatedButton.icon(
                            onPressed: fetchDashboardData,
                            icon: const Icon(Icons.refresh),
                            label: const Text('Retry'),
                          ),
                        ],
                      ),
                    )
                  : ListView(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      children: [
                        // Dashboard Header
                        Padding(
                          padding: const EdgeInsets.only(bottom: 24),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Business Dashboard',
                                style: Theme.of(context).textTheme.headlineLarge,
                              ),
                              const SizedBox(height: 4),
                              Text(
                                'Real-time business metrics',
                                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                  color: Colors.grey[600],
                                ),
                              ),
                            ],
                          ),
                        ),
                        // KPI Section Title
                        Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: Text(
                            'Key Metrics',
                            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        // KPI Cards Row 1
                        Row(
                          children: [
                            Expanded(
                              child: _buildKpiCard(
                                title: 'Today\'s Sales',
                                value: '₹15,432',
                                subtitle: '5 invoices',
                                icon: Icons.trending_up,
                                color: Colors.blue,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: _buildKpiCard(
                                title: 'Pending Dues',
                                value: '₹8,750',
                                subtitle: '3 customers',
                                icon: Icons.account_balance_wallet,
                                color: Colors.orange,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        // KPI Cards Row 2
                        Row(
                          children: [
                            Expanded(
                              child: _buildKpiCard(
                                title: 'Low Stock',
                                value: '4',
                                subtitle: 'items',
                                icon: Icons.warning_amber,
                                color: Colors.red,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: _buildKpiCard(
                                title: 'Inventory',
                                value: '₹1.25L',
                                subtitle: 'total value',
                                icon: Icons.inventory_2,
                                color: Colors.green,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 28),
                        // Recent Activity
                        Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: Text(
                            'Recent Activity',
                            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        ...?dashboard['recent_activity']
                            ?.map<Widget>((activity) => _buildActivityTile(activity))
                            .toList(),
                        const SizedBox(height: 28),
                        // Low Stock Items
                        Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: Text(
                            'Low Stock Items',
                            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        ..._buildLowStockList(),
                      ],
                    ),
        ),
      ),
    );
  }

  Widget _buildKpiCard({
    required String title,
    required String value,
    required String subtitle,
    required IconData icon,
    required Color color,
  }) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(
                          color: Colors.grey,
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        value,
                        style: const TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        subtitle,
                        style: const TextStyle(
                          color: Colors.grey,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(icon, color: color, size: 24),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActivityTile(Map activity) {
    return ListTile(
      leading: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: Colors.blue[50],
          borderRadius: BorderRadius.circular(6),
        ),
        child: Icon(Icons.receipt_long, color: Colors.blue[700], size: 20),
      ),
      title: Text(activity['action'] ?? ''),
      subtitle: Text(activity['time'] ?? ''),
      trailing: Text(
        '${activity['amount'] ?? 0}',
        style: TextStyle(
          fontWeight: FontWeight.bold,
          color: (activity['amount'] ?? 0) > 0 ? Colors.green : Colors.red,
        ),
      ),
    );
  }

  List<Widget> _buildLowStockList() {
    final items = dashboard['low_stock_items'] as List?;
    if (items == null || items.isEmpty) {
      return [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 16),
          child: Text(
            'No low stock items',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ),
      ];
    }
    return items.map<Widget>((item) {
      return Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.red[50],
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.red[200]!, width: 1),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item['name'] ?? '',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 4),
                Text(
                  'Reorder: ${item['reorder_qty'] ?? 0}',
                  style: const TextStyle(fontSize: 12, color: Colors.grey),
                ),
              ],
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.red,
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                '${item['qty'] ?? 0}',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        ),
      );
    }).toList();
  }
}
