#!/usr/bin/env bash
# run_tests.sh - a tiny dependency-free test runner.
#
# Each tests/test_*.sh file defines functions named test_*. Every test runs in
# its own subshell with a fresh temporary directory ($T), so tests cannot leak
# state into each other. Usage:
#
#   tests/run_tests.sh              # run everything
#   tests/run_tests.sh rotate       # only tests whose name contains "rotate"

set -uo pipefail

TESTS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$TESTS_DIR/.." && pwd)
BKP="$ROOT/bin/bkp"
export TESTS_DIR ROOT BKP

filter=${1:-}
pass=0 fail=0
failed=()

# ---- assertions -----------------------------------------------------------
fail() { printf '    assertion failed: %s\n' "$*" >&2; exit 1; }

assert_eq() {
  [[ $1 == "$2" ]] || fail "${3:-values differ}"$'\n'"      expected: $2"$'\n'"      actual:   $1"
}
# shellcheck disable=SC2016
assert_contains() {
  [[ $1 == *"$2"* ]] || fail "${3:-expected output to contain '$2'}"$'\n'"      output: $1"
}
assert_file() { [[ -f $1 ]] || fail "expected file to exist: $1"; }
assert_no_file() { [[ ! -e $1 ]] || fail "expected path to be absent: $1"; }

# assert_fails CMD... - CMD must exit non-zero. Its stderr is kept in $ERR.
assert_fails() {
  if "$@" 2>"$T/.err" >/dev/null; then
    fail "expected failure: $*"
  fi
  # shellcheck disable=SC2034 # read by the tests
  ERR=$(<"$T/.err")
}

# count_archives DIR - number of archive files (excluding .sha256 sidecars).
count_archives() {
  local n=0 f
  for f in "$1"/*--*; do
    [[ -f $f && $f != *.sha256 ]] && n=$((n + 1))
  done
  echo "$n"
}

# epoch "YYYY-MM-DD HH:MM:SS" - helper for pinning BKP_NOW.
epoch() { date -u -d "$1" +%s; }

# ---- runner ---------------------------------------------------------------
for file in "$TESTS_DIR"/test_*.sh; do
  # shellcheck source=/dev/null
  source "$file"
done

mapfile -t tests < <(declare -F | awk '{print $3}' | grep '^test_' | sort)

for t in "${tests[@]}"; do
  [[ -z $filter || $t == *"$filter"* ]] || continue
  T=$(mktemp -d)
  export T BKP_LOG=''
  # Run outside an `if` so that `set -e` really is active inside the test
  # (bash ignores errexit in commands that are part of a condition).
  (set -e; cd "$T"; "$t") >"$T/.out" 2>&1
  rc=$?
  if ((rc == 0)); then
    printf '  \033[32mPASS\033[0m %s\n' "$t"
    pass=$((pass + 1))
  else
    printf '  \033[31mFAIL\033[0m %s\n' "$t"
    sed 's/^/    | /' "$T/.out"
    fail=$((fail + 1))
    failed+=("$t")
  fi
  rm -rf "$T"
done

printf '\n%d passed, %d failed\n' "$pass" "$fail"
((fail == 0))
