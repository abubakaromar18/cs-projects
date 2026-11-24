#!/usr/bin/env bash
# Runs test/core/ on a bare Dart SDK (no Flutter, no pub.dev access needed).
#
# It builds a throwaway package in a temp dir that links the pure-Dart core
# (lib/qr_core.dart + lib/src/core) and test/core, resolves `flutter_test`
# to the small shim in tool/vm_test_shim, and runs every *_test.dart file.
# If you have Flutter, prefer: flutter test
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/lib/src" "$WORK/test" "$WORK/bin"
ln -s "$ROOT/lib/qr_core.dart" "$WORK/lib/qr_core.dart"
ln -s "$ROOT/lib/src/core" "$WORK/lib/src/core"
ln -s "$ROOT/test/core" "$WORK/test/core"

cat > "$WORK/pubspec.yaml" <<EOF
name: qr_studio
publish_to: none
environment:
  sdk: ">=3.4.0 <4.0.0"
dev_dependencies:
  flutter_test:
    path: $ROOT/tool/vm_test_shim
EOF

cat > "$WORK/analysis_options.yaml" <<'YAML'
analyzer:
  language:
    strict-casts: true
    strict-inference: true
    strict-raw-types: true
YAML

# Generate a runner that calls each test file's main().
{
  echo "import 'dart:io';"
  echo "import 'package:flutter_test/flutter_test.dart' show shimResults;"
  i=0
  for f in "$ROOT"/test/core/*_test.dart; do
    echo "import '../test/core/$(basename "$f")' as t$i;"
    i=$((i + 1))
  done
  echo "void main() {"
  for ((j = 0; j < i; j++)); do echo "  t$j.main();"; done
  cat <<'EOF'
  for (final f in shimResults.failures) {
    stderr.writeln('FAIL: $f\n');
  }
  stdout.writeln('${shimResults.passed} passed, ${shimResults.failures.length} failed');
  exit(shimResults.failures.isEmpty ? 0 : 1);
}
EOF
} > "$WORK/bin/run.dart"

cd "$WORK"
dart pub get --offline >/dev/null
dart analyze --fatal-infos lib test
dart run bin/run.dart
