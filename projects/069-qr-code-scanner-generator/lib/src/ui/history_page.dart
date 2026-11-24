import 'package:flutter/material.dart';

import '../../qr_core.dart';
import 'app_state.dart';
import 'payload_details.dart';
import 'qr_view.dart';

class HistoryPage extends StatefulWidget {
  const HistoryPage({super.key, required this.state});

  final AppState state;

  @override
  State<HistoryPage> createState() => _HistoryPageState();
}

class _HistoryPageState extends State<HistoryPage> {
  String _query = '';

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: widget.state,
      builder: (context, _) {
        final all = widget.state.history.entries;
        final shown = widget.state.history.search(_query);
        return Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 8, 8),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      key: const Key('history-search'),
                      decoration: const InputDecoration(
                        prefixIcon: Icon(Icons.search),
                        hintText: 'Search history',
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                      onChanged: (q) => setState(() => _query = q),
                    ),
                  ),
                  IconButton(
                    tooltip: 'Clear history',
                    icon: const Icon(Icons.delete_sweep_outlined),
                    onPressed: all.isEmpty ? null : () => _confirmClear(context),
                  ),
                ],
              ),
            ),
            Expanded(
              child: shown.isEmpty
                  ? Center(child: Text(all.isEmpty ? 'Nothing scanned or saved yet' : 'No matches'))
                  : ListView.builder(
                      itemCount: shown.length,
                      itemBuilder: (context, i) {
                        final entry = shown[i];
                        final payload = entry.payload;
                        return Dismissible(
                          key: ObjectKey(entry),
                          direction: DismissDirection.endToStart,
                          background: Container(
                            alignment: Alignment.centerRight,
                            padding: const EdgeInsets.only(right: 24),
                            color: Theme.of(context).colorScheme.errorContainer,
                            child: const Icon(Icons.delete_outline),
                          ),
                          onDismissed: (_) => widget.state.removeAt(all.indexOf(entry)),
                          child: ListTile(
                            leading: Icon(PayloadDetails.iconFor(payload)),
                            title: Text(
                              payload.summary,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            subtitle: Text(
                              '${payload.kind} · '
                              '${entry.source == HistorySource.scanned ? 'scanned' : 'generated'} · '
                              '${_ago(entry.at)}',
                            ),
                            onTap: () => _open(context, entry),
                          ),
                        );
                      },
                    ),
            ),
          ],
        );
      },
    );
  }

  void _open(BuildContext context, HistoryEntry entry) {
    QrCode? code;
    try {
      code = QrCode.encodeText(entry.raw);
    } on DataTooLongException {
      code = null;
    }
    showPayloadSheet(
      context,
      entry.raw,
      header: code == null ? null : QrView(code: code, size: 200),
    );
  }

  Future<void> _confirmClear(BuildContext context) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Clear history?'),
        content: const Text('This removes every scanned and saved code.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Clear')),
        ],
      ),
    );
    if (ok ?? false) widget.state.clear();
  }

  static String _ago(DateTime t) {
    final d = DateTime.now().difference(t);
    if (d.inMinutes < 1) return 'just now';
    if (d.inHours < 1) return '${d.inMinutes} min ago';
    if (d.inDays < 1) return '${d.inHours} h ago';
    return '${d.inDays} d ago';
  }
}
