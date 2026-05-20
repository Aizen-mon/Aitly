import 'package:flutter/material.dart';
import '../services/api.dart';
import '../widgets/simple_voice_control.dart';

class DashboardScreen extends StatefulWidget {
  @override
  _DashboardScreenState createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic> dashboard = {};
  Map<String, dynamic> assistantStatus = {};
  List<Map<String, dynamic>> assistantAlerts = [];
  String? assistantSummary;
  String? _voiceTranscript;
  String? _voiceResponse;
  bool _voiceProcessing = false;
  bool loading = true;
  String? errorMessage;
  final String _sessionId = DateTime.now().millisecondsSinceEpoch.toString();

  @override
  void initState() {
    super.initState();
    fetchDashboardData();
    fetchAssistantInsights();
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

  Future<void> fetchAssistantInsights() async {
    try {
      final status = await Api.get('/assistant/status');
      final summary = await Api.get('/assistant/summary');
      if (!mounted) return;
      setState(() {
        assistantStatus = (status is Map) ? Map<String, dynamic>.from(status as Map) : {};
        assistantAlerts = List<Map<String, dynamic>>.from((status is Map ? status['alerts'] : null) ?? []);
        assistantSummary = summary?['summary']?.toString();
      });
    } catch (_) {
      // Keep dashboard usable even if assistant endpoints are unavailable.
    }
  }

  @override
  Widget build(BuildContext context) {
    final kpis = dashboard['kpis'] as Map<String, dynamic>? ?? {};
    final todaySales = kpis['today_sales'] as Map<String, dynamic>? ?? {};
    final pendingDue = kpis['pending_due'] as Map<String, dynamic>? ?? {};
    final lowStock = kpis['low_stock_count'] as Map<String, dynamic>? ?? {};
    final inventoryValue = kpis['inventory_value'] as Map<String, dynamic>? ?? {};

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
          onRefresh: () async {
            await fetchDashboardData();
            await fetchAssistantInsights();
          },
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
                              if (assistantSummary != null) ...[
                                const SizedBox(height: 12),
                                Container(
                                  width: double.infinity,
                                  padding: const EdgeInsets.all(14),
                                  decoration: BoxDecoration(
                                    color: Colors.blue[50],
                                    borderRadius: BorderRadius.circular(14),
                                    border: Border.all(color: Colors.blue[100]!),
                                  ),
                                  child: Text(
                                    assistantSummary!,
                                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                      color: Colors.blue[900],
                                      height: 1.35,
                                    ),
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                        const SizedBox(height: 16),
                        _buildVoiceCommandCard(),
                        const SizedBox(height: 24),
                        if (assistantStatus.isNotEmpty) ...[
                          Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: _buildStatusCard(),
                          ),
                        ],
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
                                title: todaySales['label']?.toString() ?? 'Today\'s Sales',
                                value: '₹${(todaySales['value'] ?? 0).toString()}',
                                subtitle: '${todaySales['count'] ?? 0} invoices',
                                icon: Icons.trending_up,
                                color: Colors.blue,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: _buildKpiCard(
                                title: pendingDue['label']?.toString() ?? 'Pending Dues',
                                value: '₹${(pendingDue['value'] ?? 0).toString()}',
                                subtitle: '${pendingDue['count'] ?? 0} customers',
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
                                title: lowStock['label']?.toString() ?? 'Low Stock',
                                value: '${lowStock['value'] ?? 0}',
                                subtitle: 'items',
                                icon: Icons.warning_amber,
                                color: Colors.red,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: _buildKpiCard(
                                title: inventoryValue['label']?.toString() ?? 'Inventory',
                                value: '₹${(inventoryValue['value'] ?? 0).toString()}',
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
                        if (assistantAlerts.isNotEmpty) ...[
                          const SizedBox(height: 20),
                          Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: Text(
                              'Smart Alerts',
                              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                          ...assistantAlerts.take(5).map(_buildAlertTile),
                        ],
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

  Widget _buildStatusCard() {
    final sync = assistantStatus['sync'] as Map<String, dynamic>? ?? {};
    final connected = sync['connected'] == true;
    final pending = sync['pending_count'] ?? 0;
    final failed = sync['failed_count'] ?? 0;

    return Card(
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: (connected ? Colors.green : Colors.orange).withOpacity(0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(
                connected ? Icons.cloud_done : Icons.cloud_off,
                color: connected ? Colors.green : Colors.orange,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    connected ? 'Connected to Tally' : 'Tally disconnected',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Pending sync: $pending • Failed sync: $failed',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey[700]),
                  ),
                ],
              ),
            ),
            TextButton(
              onPressed: fetchAssistantInsights,
              child: const Text('Refresh'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildVoiceCommandCard() {
    return Card(
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.blue.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.mic, color: Colors.blue),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Voice Command',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Start and stop listening directly from the dashboard.',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey[700]),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            SimpleVoiceControl(
              onListeningChanged: (_) {},
              onFinalTranscript: _handleVoiceTranscript,
            ),
            if (_voiceProcessing) ...[
              const SizedBox(height: 12),
              const LinearProgressIndicator(minHeight: 3),
            ],
            if (_voiceTranscript != null) ...[
              const SizedBox(height: 12),
              Text(
                'Transcript',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 6),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.blueGrey[50],
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(_voiceTranscript!),
              ),
            ],
            if (_voiceResponse != null) ...[
              const SizedBox(height: 12),
              Text(
                'Assistant Response',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 6),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.green[50],
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(_voiceResponse!),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _handleVoiceTranscript(String transcript) async {
    if (!mounted || transcript.trim().isEmpty) {
      return;
    }

    setState(() {
      _voiceTranscript = transcript;
      _voiceResponse = null;
      _voiceProcessing = true;
    });

    try {
      final response = await Api.post('/parse', {
        'text': transcript,
        'session_id': _sessionId,
      });

      if (!mounted) return;
      setState(() {
        _voiceResponse = response['speech']?.toString() ?? response['message']?.toString() ?? 'Command processed';
      });

      await fetchAssistantInsights();
      await fetchDashboardData();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _voiceResponse = 'Could not process voice command: $e';
      });
    } finally {
      if (mounted) {
        setState(() {
          _voiceProcessing = false;
        });
      }
    }
  }

  Widget _buildAlertTile(Map<String, dynamic> alert) {
    final severity = alert['severity']?.toString() ?? 'info';
    final color = severity == 'critical'
        ? Colors.red
        : severity == 'warning'
            ? Colors.orange
            : Colors.blue;
    final icon = severity == 'critical'
        ? Icons.report
        : severity == 'warning'
            ? Icons.warning_amber
            : Icons.info_outline;

    return Card(
      color: color.withOpacity(0.05),
      child: ListTile(
        leading: Icon(icon, color: color),
        title: Text(alert['message']?.toString() ?? ''),
        subtitle: Text(alert['type']?.toString() ?? 'alert'),
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
