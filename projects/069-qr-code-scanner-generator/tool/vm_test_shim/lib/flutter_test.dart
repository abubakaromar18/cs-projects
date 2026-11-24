// A tiny stand-in for the subset of `package:flutter_test` (really
// `package:test`) used by test/core/. It exists only so the pure-Dart core
// tests can run on a bare Dart SDK when neither Flutter nor pub.dev is
// reachable. With Flutter installed, just run `flutter test`.
//
// Tests run synchronously as they are declared; results are tallied in
// [shimResults] and printed by tool/run_core_tests.sh's generated runner.
library;

final shimResults = ShimResults();

class ShimResults {
  int passed = 0;
  final List<String> failures = [];
}

final List<String> _groups = [];
final List<List<void Function()>> _setUps = [[]];

void group(String name, void Function() body) {
  _groups.add(name);
  _setUps.add([]);
  try {
    body();
  } finally {
    _groups.removeLast();
    _setUps.removeLast();
  }
}

void setUp(void Function() fn) => _setUps.last.add(fn);

void test(String name, void Function() body) {
  final fullName = [..._groups, name].join(' > ');
  try {
    for (final level in _setUps) {
      for (final s in level) {
        s();
      }
    }
    body();
    shimResults.passed++;
  } catch (e, st) {
    shimResults.failures.add('$fullName\n  $e\n${st.toString().split('\n').take(4).join('\n')}');
  }
}

class TestFailure implements Exception {
  TestFailure(this.message);
  final String message;
  @override
  String toString() => message;
}

void expect(Object? actual, Object? matcher, {String? reason}) {
  final m = wrapMatcher(matcher);
  if (!m.matches(actual)) {
    throw TestFailure(
      'Expected: ${m.description}\n  Actual: ${_show(actual)}'
      '${reason == null ? '' : '\n  Reason: $reason'}',
    );
  }
}

String _show(Object? v) {
  final s = '$v';
  return s.length > 300 ? '${s.substring(0, 300)}…' : s;
}

abstract class Matcher {
  const Matcher();
  bool matches(Object? item);
  String get description;
}

Matcher wrapMatcher(Object? x) => x is Matcher ? x : equals(x);

class _Predicate extends Matcher {
  const _Predicate(this._fn, this.description);
  final bool Function(Object?) _fn;
  @override
  final String description;
  @override
  bool matches(Object? item) => _fn(item);
}

bool _deepEquals(Object? a, Object? b) {
  if (a is List && b is List) {
    if (a.length != b.length) return false;
    for (var i = 0; i < a.length; i++) {
      if (!_deepEquals(a[i], b[i])) return false;
    }
    return true;
  }
  if (a is Map && b is Map) {
    if (a.length != b.length) return false;
    for (final k in a.keys) {
      if (!b.containsKey(k) || !_deepEquals(a[k], b[k])) return false;
    }
    return true;
  }
  if (a is Set && b is Set) return a.length == b.length && a.containsAll(b);
  return a == b;
}

Matcher equals(Object? expected) =>
    _Predicate((a) => _deepEquals(a, expected), '${_show(expected)}');
const Matcher isTrue = _Predicate(_isTrue, 'true');
const Matcher isFalse = _Predicate(_isFalse, 'false');
const Matcher isNull = _Predicate(_isNull, 'null');
const Matcher isNotNull = _Predicate(_isNotNull, 'not null');
const Matcher isEmpty = _Predicate(_isEmpty, 'empty');
const Matcher isNotEmpty = _Predicate(_isNotEmpty, 'non-empty');
bool _isTrue(Object? a) => a == true;
bool _isFalse(Object? a) => a == false;
bool _isNull(Object? a) => a == null;
bool _isNotNull(Object? a) => a != null;
bool _isEmpty(Object? a) => (a as dynamic).isEmpty as bool;
bool _isNotEmpty(Object? a) => (a as dynamic).isNotEmpty as bool;

Matcher hasLength(int n) => _Predicate((a) => (a as dynamic).length == n, 'length $n');
Matcher contains(Object? x) => _Predicate((a) => (a as dynamic).contains(x) as bool, 'contains $x');
Matcher isA<T>() => _Predicate((a) => a is T, 'an instance of $T');
Matcher greaterThan(num n) => _Predicate((a) => (a! as num) > n, '> $n');
Matcher lessThan(num n) => _Predicate((a) => (a! as num) < n, '< $n');
Matcher greaterThanOrEqualTo(num n) => _Predicate((a) => (a! as num) >= n, '>= $n');
Matcher lessThanOrEqualTo(num n) => _Predicate((a) => (a! as num) <= n, '<= $n');
Matcher inInclusiveRange(num lo, num hi) =>
    _Predicate((a) => (a! as num) >= lo && (a as num) <= hi, 'in [$lo, $hi]');

Matcher throwsA(Object? inner) {
  final m = wrapMatcher(inner);
  return _Predicate((fn) {
    try {
      (fn! as Function)();
    } catch (e) {
      return m.matches(e);
    }
    return false;
  }, 'throws ${m.description}');
}

final Matcher throwsArgumentError = throwsA(isA<ArgumentError>());
final Matcher throwsRangeError = throwsA(isA<RangeError>());
final Matcher throwsStateError = throwsA(isA<StateError>());
final Matcher throwsFormatException = throwsA(isA<FormatException>());
