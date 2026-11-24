import 'package:flutter_test/flutter_test.dart';
import 'package:qr_studio/qr_core.dart';

void main() {
  group('encode', () {
    test('Wi-Fi escapes special characters', () {
      const p = WifiPayload(ssid: r'Cafe;Free:"1"', password: r'a\b,c');
      expect(p.encode(), equals(r'WIFI:T:WPA;S:Cafe\;Free\:\"1\";P:a\\b\,c;;'));
    });

    test('open Wi-Fi omits the password, hidden flag is written', () {
      const p = WifiPayload(ssid: 'Lobby', security: WifiSecurity.none, hidden: true);
      expect(p.encode(), equals('WIFI:T:nopass;S:Lobby;H:true;;'));
    });

    test('mailto percent-encodes subject and body', () {
      const p = EmailPayload(to: 'me@example.com', subject: 'Hi there', body: 'a&b');
      expect(p.encode(), equals('mailto:me@example.com?subject=Hi%20there&body=a%26b'));
      expect(const EmailPayload(to: 'x@y.z').encode(), equals('mailto:x@y.z'));
    });

    test('geo trims trailing zeros and validates range', () {
      expect(GeoPayload(41.8781, -87.6298).encode(), equals('geo:41.8781,-87.6298'));
      expect(GeoPayload(10, 20).encode(), equals('geo:10,20'));
      expect(() => GeoPayload(91, 0), throwsRangeError);
    });

    test('URL normalization adds https only when no scheme', () {
      expect(UrlPayload.normalized(' example.com ').url, equals('https://example.com'));
      expect(UrlPayload.normalized('http://x.org').url, equals('http://x.org'));
    });

    test('MECARD contact', () {
      const p = ContactPayload(name: 'Ada Lovelace', phone: '+44 20', email: 'ada@x.uk');
      expect(p.encode(), equals(r'MECARD:N:Ada Lovelace;TEL:+44 20;EMAIL:ada@x.uk;;'));
    });
  });

  group('parse', () {
    test('round-trips every structured type', () {
      final samples = <QrPayload>[
        const UrlPayload('https://dart.dev/language?x=1'),
        const WifiPayload(ssid: r'we;ird:name', password: r'p\a,ss', security: WifiSecurity.wep),
        const WifiPayload(ssid: 'open', security: WifiSecurity.none),
        const EmailPayload(to: 'a@b.co', subject: 'Q&A', body: 'line 1\nline 2'),
        const PhonePayload('+1 555 0100'),
        const SmsPayload(number: '+15550100', message: 'on my way: 5 min'),
        GeoPayload(-33.8688, 151.2093),
        const ContactPayload(name: 'Grace Hopper', phone: '123', email: 'g@navy.mil', org: 'USN'),
        const TextPayload('just some text'),
      ];
      for (final p in samples) {
        expect(QrPayload.parse(p.encode()), equals(p), reason: p.encode());
      }
    });

    test('scheme matching is case-insensitive', () {
      expect(QrPayload.parse('wifi:S:x;T:WPA2;P:y;;'), isA<WifiPayload>());
      expect(QrPayload.parse('TEL:911'), equals(const PhonePayload('911')));
      expect(QrPayload.parse('MAILTO:x@y.z'), isA<EmailPayload>());
    });

    test('WPA2/WPA3 map to WPA; missing T means open', () {
      expect(
        (QrPayload.parse('WIFI:T:SAE;S:a;P:b;;') as WifiPayload).security,
        equals(WifiSecurity.wpa),
      );
      expect((QrPayload.parse('WIFI:S:a;;') as WifiPayload).security, equals(WifiSecurity.none));
    });

    test('MECARD "Last,First" is shown as "First Last"', () {
      final p = QrPayload.parse('MECARD:N:Turing,Alan;TEL:01;;') as ContactPayload;
      expect(p.name, equals('Alan Turing'));
      expect(p.phone, equals('01'));
    });

    test('vCard 3.0 with parameters', () {
      const vcard =
          'BEGIN:VCARD\r\nVERSION:3.0\r\nN:Hamilton;Margaret;;;\r\n'
          'FN:Margaret Hamilton\r\nORG:MIT;Apollo\r\nTEL;TYPE=work:+1 617\r\n'
          'EMAIL;TYPE=INTERNET:mh@mit.edu\r\nEND:VCARD';
      final p = QrPayload.parse(vcard) as ContactPayload;
      expect(p.name, equals('Margaret Hamilton'));
      expect(p.org, equals('MIT Apollo'));
      expect(p.phone, equals('+1 617'));
      expect(p.email, equals('mh@mit.edu'));
    });

    test('malformed structured payloads fall back to text', () {
      expect(QrPayload.parse('WIFI:T:WPA;P:nossid;;'), isA<TextPayload>());
      expect(QrPayload.parse('geo:abc,def'), isA<TextPayload>());
      expect(QrPayload.parse('geo:95,0'), isA<TextPayload>());
      expect(QrPayload.parse('BEGIN:VCARD\nEND:VCARD'), isA<TextPayload>());
      expect(QrPayload.parse('ftp://files.example'), isA<TextPayload>());
      expect(QrPayload.parse('http://'), isA<TextPayload>());
    });

    test('geo URI with altitude and parameters', () {
      final p = QrPayload.parse('geo:48.2,16.37,180;crs=wgs84?z=12') as GeoPayload;
      expect(p.latitude, equals(48.2));
      expect(p.longitude, equals(16.37));
    });

    test('summaries are single-line', () {
      expect(const TextPayload('a\nb').summary, equals('a b'));
      expect(const WifiPayload(ssid: 'Home').summary, equals('Home (WPA)'));
    });
  });

  test('every payload encodes into a valid QR code', () {
    final payloads = <QrPayload>[
      const WifiPayload(ssid: 'Home', password: 'hunter22'),
      const ContactPayload(name: 'Ada', email: 'ada@x.uk'),
      GeoPayload(0, 0),
    ];
    for (final p in payloads) {
      final qr = QrCode.encodeText(p.encode());
      expect(qr.size, equals(qr.version * 4 + 17));
    }
  });
}
