import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../qr_core.dart';
import 'app_state.dart';
import 'qr_view.dart';

enum GenerateKind {
  text('Text', Icons.notes),
  url('URL', Icons.link),
  wifi('Wi-Fi', Icons.wifi),
  email('E-mail', Icons.email_outlined),
  phone('Phone', Icons.phone_outlined),
  contact('Contact', Icons.person_outline);

  const GenerateKind(this.label, this.icon);
  final String label;
  final IconData icon;
}

/// Form → payload string → [QrCode] → live preview.
class GeneratePage extends StatefulWidget {
  const GeneratePage({super.key, required this.state});

  final AppState state;

  @override
  State<GeneratePage> createState() => _GeneratePageState();
}

class _GeneratePageState extends State<GeneratePage> {
  GenerateKind _kind = GenerateKind.text;
  EcLevel _ecl = EcLevel.medium;
  WifiSecurity _wifiSecurity = WifiSecurity.wpa;
  bool _wifiHidden = false;

  // One controller per field name, created lazily and reused across kinds.
  final Map<String, TextEditingController> _fields = {};

  TextEditingController _c(String name) =>
      _fields.putIfAbsent(name, () => TextEditingController()..addListener(_changed));

  String _v(String name) => _c(name).text.trim();

  void _changed() => setState(() {});

  @override
  void dispose() {
    for (final c in _fields.values) {
      c.dispose();
    }
    super.dispose();
  }

  /// The encoded string, or null while required fields are empty.
  String? get _payload => switch (_kind) {
    GenerateKind.text => _c('text').text.isEmpty ? null : TextPayload(_c('text').text).encode(),
    GenerateKind.url => _v('url').isEmpty ? null : UrlPayload.normalized(_v('url')).encode(),
    GenerateKind.wifi =>
      _v('ssid').isEmpty
          ? null
          : WifiPayload(
              ssid: _v('ssid'),
              password: _c('wifiPass').text,
              security: _wifiSecurity,
              hidden: _wifiHidden,
            ).encode(),
    GenerateKind.email =>
      _v('to').isEmpty
          ? null
          : EmailPayload(to: _v('to'), subject: _v('subject'), body: _c('body').text).encode(),
    GenerateKind.phone => _v('phone').isEmpty ? null : PhonePayload(_v('phone')).encode(),
    GenerateKind.contact =>
      _v('name').isEmpty
          ? null
          : ContactPayload(
              name: _v('name'),
              phone: _v('cPhone'),
              email: _v('cEmail'),
              org: _v('org'),
            ).encode(),
  };

  List<Widget> _formFields() {
    Widget field(
      String name,
      String label, {
      TextInputType? type,
      bool obscure = false,
      int maxLines = 1,
      String? hint,
    }) => Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextField(
        key: ValueKey('field-$name'),
        controller: _c(name),
        keyboardType: type,
        obscureText: obscure,
        maxLines: obscure ? 1 : maxLines,
        minLines: 1,
        decoration: InputDecoration(
          labelText: label,
          hintText: hint,
          border: const OutlineInputBorder(),
        ),
      ),
    );

    return switch (_kind) {
      GenerateKind.text => [field('text', 'Text', maxLines: 5)],
      GenerateKind.url => [field('url', 'URL', type: TextInputType.url, hint: 'example.com')],
      GenerateKind.wifi => [
        field('ssid', 'Network name (SSID)'),
        SegmentedButton<WifiSecurity>(
          segments: const [
            ButtonSegment(value: WifiSecurity.wpa, label: Text('WPA/WPA2')),
            ButtonSegment(value: WifiSecurity.wep, label: Text('WEP')),
            ButtonSegment(value: WifiSecurity.none, label: Text('Open')),
          ],
          selected: {_wifiSecurity},
          onSelectionChanged: (s) => setState(() => _wifiSecurity = s.first),
        ),
        const SizedBox(height: 12),
        if (_wifiSecurity != WifiSecurity.none) field('wifiPass', 'Password', obscure: true),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Hidden network'),
          value: _wifiHidden,
          onChanged: (v) => setState(() => _wifiHidden = v),
        ),
      ],
      GenerateKind.email => [
        field('to', 'To', type: TextInputType.emailAddress),
        field('subject', 'Subject'),
        field('body', 'Body', maxLines: 4),
      ],
      GenerateKind.phone => [field('phone', 'Phone number', type: TextInputType.phone)],
      GenerateKind.contact => [
        field('name', 'Name'),
        field('org', 'Organization'),
        field('cPhone', 'Phone', type: TextInputType.phone),
        field('cEmail', 'E-mail', type: TextInputType.emailAddress),
      ],
    };
  }

  @override
  Widget build(BuildContext context) {
    final payload = _payload;
    QrCode? code;
    String? error;
    if (payload != null) {
      try {
        code = QrCode.encodeText(payload, ecl: _ecl);
      } on DataTooLongException {
        error =
            'Too much data for a QR code at level ${_ecl.letter}. '
            'Shorten it or lower the error correction.';
      }
    }

    final preview = _Preview(
      code: code,
      error: error,
      onCopy: payload == null ? null : () => _copy(payload),
      onSave: code == null ? null : () => _save(payload!),
    );

    final form = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final k in GenerateKind.values)
              ChoiceChip(
                avatar: Icon(k.icon, size: 18),
                label: Text(k.label),
                selected: _kind == k,
                onSelected: (_) => setState(() => _kind = k),
              ),
          ],
        ),
        const SizedBox(height: 16),
        ..._formFields(),
        const SizedBox(height: 4),
        Text('Error correction', style: Theme.of(context).textTheme.labelLarge),
        const SizedBox(height: 8),
        SegmentedButton<EcLevel>(
          segments: [
            for (final e in EcLevel.values)
              ButtonSegment(value: e, label: Text(e.letter), tooltip: _eclHelp(e)),
          ],
          selected: {_ecl},
          onSelectionChanged: (s) => setState(() => _ecl = s.first),
        ),
      ],
    );

    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= 720;
        if (wide) {
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: SingleChildScrollView(padding: const EdgeInsets.all(24), child: form),
              ),
              SizedBox(
                width: 360,
                child: Padding(padding: const EdgeInsets.all(24), child: preview),
              ),
            ],
          );
        }
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [preview, const SizedBox(height: 24), form],
        );
      },
    );
  }

  static String _eclHelp(EcLevel e) => switch (e) {
    EcLevel.low => 'Low: ~7% damage tolerated',
    EcLevel.medium => 'Medium: ~15%',
    EcLevel.quartile => 'Quartile: ~25%',
    EcLevel.high => 'High: ~30% (good for printed codes with a logo)',
  };

  Future<void> _copy(String payload) async {
    await Clipboard.setData(ClipboardData(text: payload));
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(const SnackBar(content: Text('Copied encoded text')));
  }

  void _save(String payload) {
    widget.state.record(payload, HistorySource.generated);
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Saved to history')));
  }
}

class _Preview extends StatelessWidget {
  const _Preview({required this.code, required this.error, this.onCopy, this.onSave});

  final QrCode? code;
  final String? error;
  final VoidCallback? onCopy;
  final VoidCallback? onSave;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final Widget body;
    if (error != null) {
      body = Text(
        error!,
        key: const Key('qr-error'),
        style: TextStyle(color: theme.colorScheme.error),
      );
    } else if (code == null) {
      body = Text('Fill in the form to create a code', style: theme.textTheme.bodyMedium);
    } else {
      body = Column(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: QrView(key: const Key('qr-preview'), code: code!),
          ),
          const SizedBox(height: 8),
          Text(
            'Version ${code!.version} · ${code!.size}×${code!.size} · '
            'level ${code!.errorCorrection.letter} · mask ${code!.mask}',
            key: const Key('qr-info'),
            style: theme.textTheme.bodySmall,
          ),
        ],
      );
    }
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            SizedBox(height: 280, child: Center(child: body)),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                TextButton.icon(
                  onPressed: onCopy,
                  icon: const Icon(Icons.copy),
                  label: const Text('Copy text'),
                ),
                const SizedBox(width: 8),
                FilledButton.icon(
                  key: const Key('save-button'),
                  onPressed: onSave,
                  icon: const Icon(Icons.bookmark_add_outlined),
                  label: const Text('Save'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
