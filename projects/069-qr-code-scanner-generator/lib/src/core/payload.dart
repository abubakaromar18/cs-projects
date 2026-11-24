/// Structured QR payloads: building the de-facto string formats that phone
/// cameras understand, and parsing scanned strings back into structure.
///
/// Formats covered:
///   URL      https://example.com
///   Wi-Fi    WIFI:T:WPA;S:ssid;P:pass;H:false;;   (ZXing convention)
///   E-mail   mailto:a@b.c?subject=…&body=…
///   Phone    tel:+15551234567
///   SMS      SMSTO:+15551234567:message
///   Location geo:41.88,-87.63
///   Contact  MECARD:N:Name;TEL:…;EMAIL:…;;  (vCard 3.0 parsed too)
///   Text     anything else
library;

/// Common supertype. [encode] produces the string to put in a QR code.
sealed class QrPayload {
  const QrPayload();

  String encode();

  /// Short human-readable label for lists.
  String get kind;

  /// One-line summary shown in history.
  String get summary;

  /// Recognizes the format of a scanned string. Never throws: anything
  /// unrecognized (or malformed) becomes a [TextPayload].
  static QrPayload parse(String raw) {
    final s = raw.trim();
    final upper = s.toUpperCase();
    try {
      if (upper.startsWith('WIFI:')) return WifiPayload.parse(s);
      if (upper.startsWith('MAILTO:')) return EmailPayload.parse(s);
      if (upper.startsWith('TEL:')) return PhonePayload(s.substring(4));
      if (upper.startsWith('SMSTO:') || upper.startsWith('SMS:')) return SmsPayload.parse(s);
      if (upper.startsWith('GEO:')) return GeoPayload.parse(s);
      if (upper.startsWith('MECARD:')) return ContactPayload.parseMecard(s);
      if (upper.startsWith('BEGIN:VCARD')) return ContactPayload.parseVcard(s);
      final uri = Uri.tryParse(s);
      if (uri != null && (uri.scheme == 'http' || uri.scheme == 'https') && uri.host.isNotEmpty) {
        return UrlPayload(s);
      }
    } on FormatException {
      // fall through to plain text
    }
    return TextPayload(raw);
  }
}

class TextPayload extends QrPayload {
  const TextPayload(this.text);
  final String text;
  @override
  String encode() => text;
  @override
  String get kind => 'Text';
  @override
  String get summary => text.replaceAll('\n', ' ');
  @override
  bool operator ==(Object other) => other is TextPayload && other.text == text;
  @override
  int get hashCode => text.hashCode;
}

class UrlPayload extends QrPayload {
  const UrlPayload(this.url);
  final String url;

  /// Adds https:// when the user typed a bare domain.
  factory UrlPayload.normalized(String input) {
    final t = input.trim();
    return UrlPayload(RegExp(r'^[a-zA-Z][a-zA-Z0-9+.-]*://').hasMatch(t) ? t : 'https://$t');
  }

  @override
  String encode() => url;
  @override
  String get kind => 'URL';
  @override
  String get summary => url;
  @override
  bool operator ==(Object other) => other is UrlPayload && other.url == url;
  @override
  int get hashCode => url.hashCode;
}

enum WifiSecurity { wpa, wep, none }

class WifiPayload extends QrPayload {
  const WifiPayload({
    required this.ssid,
    this.password = '',
    this.security = WifiSecurity.wpa,
    this.hidden = false,
  });

  final String ssid;
  final String password;
  final WifiSecurity security;
  final bool hidden;

  @override
  String encode() {
    final t = switch (security) {
      WifiSecurity.wpa => 'WPA',
      WifiSecurity.wep => 'WEP',
      WifiSecurity.none => 'nopass',
    };
    final sb = StringBuffer('WIFI:T:$t;S:${_escape(ssid)};');
    if (security != WifiSecurity.none) sb.write('P:${_escape(password)};');
    if (hidden) sb.write('H:true;');
    sb.write(';');
    return sb.toString();
  }

  factory WifiPayload.parse(String raw) {
    final fields = _parseFields(raw.substring(raw.indexOf(':') + 1));
    final ssid = fields['S'];
    if (ssid == null) throw const FormatException('Wi-Fi payload without SSID');
    final t = (fields['T'] ?? '').toUpperCase();
    final security = switch (t) {
      'WEP' => WifiSecurity.wep,
      '' || 'NOPASS' => WifiSecurity.none,
      _ => WifiSecurity.wpa, // WPA, WPA2, WPA3, SAE…
    };
    return WifiPayload(
      ssid: ssid,
      password: fields['P'] ?? '',
      security: security,
      hidden: (fields['H'] ?? '').toLowerCase() == 'true',
    );
  }

  @override
  String get kind => 'Wi-Fi';
  @override
  String get summary => '$ssid (${security.name.toUpperCase()})';
  @override
  bool operator ==(Object other) =>
      other is WifiPayload &&
      other.ssid == ssid &&
      other.password == password &&
      other.security == security &&
      other.hidden == hidden;
  @override
  int get hashCode => Object.hash(ssid, password, security, hidden);
}

class EmailPayload extends QrPayload {
  const EmailPayload({required this.to, this.subject = '', this.body = ''});
  final String to;
  final String subject;
  final String body;

  @override
  String encode() {
    final query = <String>[
      if (subject.isNotEmpty) 'subject=${Uri.encodeComponent(subject)}',
      if (body.isNotEmpty) 'body=${Uri.encodeComponent(body)}',
    ];
    return 'mailto:$to${query.isEmpty ? '' : '?${query.join('&')}'}';
  }

  factory EmailPayload.parse(String raw) {
    final rest = raw.substring('mailto:'.length);
    final q = rest.indexOf('?');
    final to = Uri.decodeComponent(q < 0 ? rest : rest.substring(0, q));
    final params = q < 0 ? const <String, String>{} : Uri.splitQueryString(rest.substring(q + 1));
    return EmailPayload(to: to, subject: params['subject'] ?? '', body: params['body'] ?? '');
  }

  @override
  String get kind => 'E-mail';
  @override
  String get summary => subject.isEmpty ? to : '$to — $subject';
  @override
  bool operator ==(Object other) =>
      other is EmailPayload && other.to == to && other.subject == subject && other.body == body;
  @override
  int get hashCode => Object.hash(to, subject, body);
}

class PhonePayload extends QrPayload {
  const PhonePayload(this.number);
  final String number;
  @override
  String encode() => 'tel:$number';
  @override
  String get kind => 'Phone';
  @override
  String get summary => number;
  @override
  bool operator ==(Object other) => other is PhonePayload && other.number == number;
  @override
  int get hashCode => number.hashCode;
}

class SmsPayload extends QrPayload {
  const SmsPayload({required this.number, this.message = ''});
  final String number;
  final String message;
  @override
  String encode() => 'SMSTO:$number:$message';

  factory SmsPayload.parse(String raw) {
    final rest = raw.substring(raw.indexOf(':') + 1);
    final sep = rest.indexOf(':');
    return sep < 0
        ? SmsPayload(number: rest)
        : SmsPayload(number: rest.substring(0, sep), message: rest.substring(sep + 1));
  }

  @override
  String get kind => 'SMS';
  @override
  String get summary => message.isEmpty ? number : '$number: $message';
  @override
  bool operator ==(Object other) =>
      other is SmsPayload && other.number == number && other.message == message;
  @override
  int get hashCode => Object.hash(number, message);
}

class GeoPayload extends QrPayload {
  GeoPayload(this.latitude, this.longitude) {
    if (latitude.abs() > 90) throw RangeError.range(latitude, -90, 90, 'latitude');
    if (longitude.abs() > 180) throw RangeError.range(longitude, -180, 180, 'longitude');
  }
  final double latitude;
  final double longitude;

  @override
  String encode() => 'geo:${_num(latitude)},${_num(longitude)}';

  factory GeoPayload.parse(String raw) {
    // geo:lat,lng[,alt][;params][?query]
    final body = raw.substring(4).split(RegExp(r'[;?]')).first;
    final parts = body.split(',');
    if (parts.length < 2) throw const FormatException('geo URI needs latitude,longitude');
    final lat = double.tryParse(parts[0]);
    final lng = double.tryParse(parts[1]);
    if (lat == null || lng == null || lat.abs() > 90 || lng.abs() > 180) {
      throw const FormatException('invalid coordinates');
    }
    return GeoPayload(lat, lng);
  }

  static String _num(double v) {
    final s = v.toStringAsFixed(6);
    return s.replaceFirst(RegExp(r'\.?0+$'), '');
  }

  @override
  String get kind => 'Location';
  @override
  String get summary => '${_num(latitude)}, ${_num(longitude)}';
  @override
  bool operator ==(Object other) =>
      other is GeoPayload && other.latitude == latitude && other.longitude == longitude;
  @override
  int get hashCode => Object.hash(latitude, longitude);
}

class ContactPayload extends QrPayload {
  const ContactPayload({required this.name, this.phone = '', this.email = '', this.org = ''});
  final String name;
  final String phone;
  final String email;
  final String org;

  /// MECARD is much shorter than vCard, so the QR code stays small.
  @override
  String encode() {
    final sb = StringBuffer('MECARD:N:${_escape(name)};');
    if (org.isNotEmpty) sb.write('ORG:${_escape(org)};');
    if (phone.isNotEmpty) sb.write('TEL:${_escape(phone)};');
    if (email.isNotEmpty) sb.write('EMAIL:${_escape(email)};');
    sb.write(';');
    return sb.toString();
  }

  factory ContactPayload.parseMecard(String raw) {
    final f = _parseFields(raw.substring('MECARD:'.length));
    // MECARD names are "Last,First"; show them as "First Last".
    final n = f['N'] ?? '';
    final comma = n.indexOf(',');
    final name = comma < 0 ? n : '${n.substring(comma + 1)} ${n.substring(0, comma)}'.trim();
    return ContactPayload(
      name: name,
      phone: f['TEL'] ?? '',
      email: f['EMAIL'] ?? '',
      org: f['ORG'] ?? '',
    );
  }

  factory ContactPayload.parseVcard(String raw) {
    String? fn, n, tel, email, org;
    for (final line in raw.split(RegExp(r'\r?\n'))) {
      final colon = line.indexOf(':');
      if (colon < 0) continue;
      // Property name may carry parameters, e.g. "TEL;TYPE=cell".
      final key = line.substring(0, colon).split(';').first.toUpperCase();
      final value = line.substring(colon + 1).trim();
      switch (key) {
        case 'FN':
          fn ??= value;
        case 'N':
          n ??= value.split(';').where((p) => p.isNotEmpty).toList().reversed.join(' ');
        case 'TEL':
          tel ??= value;
        case 'EMAIL':
          email ??= value;
        case 'ORG':
          org ??= value.replaceAll(';', ' ').trim();
      }
    }
    final name = fn ?? n;
    if (name == null) throw const FormatException('vCard without a name');
    return ContactPayload(name: name, phone: tel ?? '', email: email ?? '', org: org ?? '');
  }

  @override
  String get kind => 'Contact';
  @override
  String get summary => [name, phone, email].where((s) => s.isNotEmpty).join(' · ');
  @override
  bool operator ==(Object other) =>
      other is ContactPayload &&
      other.name == name &&
      other.phone == phone &&
      other.email == email &&
      other.org == org;
  @override
  int get hashCode => Object.hash(name, phone, email, org);
}

// ---- shared helpers for the "KEY:value;KEY:value;;" family (Wi-Fi, MECARD) ----

const _special = r'\;,:"';

String _escape(String s) {
  final sb = StringBuffer();
  for (final ch in s.split('')) {
    if (_special.contains(ch)) sb.write(r'\');
    sb.write(ch);
  }
  return sb.toString();
}

/// Splits on unescaped ';', then each field on its first unescaped ':'.
/// Backslash escapes are removed. The first occurrence of a key wins.
Map<String, String> _parseFields(String body) {
  final fields = <String, String>{};
  final key = StringBuffer();
  final value = StringBuffer();
  var inValue = false;
  var escaped = false;

  void flush() {
    final k = key.toString().toUpperCase();
    if (k.isNotEmpty) fields.putIfAbsent(k, () => value.toString());
    key.clear();
    value.clear();
    inValue = false;
  }

  for (final ch in body.split('')) {
    final target = inValue ? value : key;
    if (escaped) {
      target.write(ch);
      escaped = false;
    } else if (ch == r'\') {
      escaped = true;
    } else if (ch == ';') {
      flush();
    } else if (ch == ':' && !inValue) {
      inValue = true;
    } else {
      target.write(ch);
    }
  }
  flush();
  return fields;
}
