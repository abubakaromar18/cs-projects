#!/usr/bin/env bash
# cli_test.sh - End-to-end checks of the bf command-line tool.
set -u
BF="${1:-./build/bf}"
DIR="$(cd "$(dirname "$0")/.." && pwd)"
pass=0 fail=0

check() { # name expected actual
    if [[ "$2" == "$3" ]]; then pass=$((pass + 1)); echo "  $1 ok"
    else fail=$((fail + 1)); echo "  $1 FAIL: expected [$2] got [$3]"; fi
}

echo "cli tests"
check hello      "Hello World!"  "$("$BF" "$DIR/examples/hello.bf")"
check reverse    "cba"           "$(printf 'abc' | "$BF" "$DIR/examples/reverse.bf")"
check expr       "A"             "$("$BF" -e '++++++++[>++++++++<-]>+.')"
check bench      "OK"            "$("$BF" "$DIR/examples/bench.bf")"
check O0-expr    "B"             "$("$BF" -e '++++++++[>++++++++<-]>++.' -O0)"

err="$("$BF" -e '+]' 2>&1)"; code=$?
check syntax-msg "<expr>:1:2: error: unmatched ']'" "$err"
check syntax-code 1 "$code"

"$BF" -t 3 -e '>>>' 2>/dev/null; check bounds-code 1 $?
"$BF" -m 100 -e '+[]' 2>/dev/null; check steplimit-code 1 $?
"$BF" -O 7 -e '+' 2>/dev/null; check bad-opt 2 $?

dump="$("$BF" -d -e '[-]>[->++<]')"
check dump-has-set    2 "$(grep -c 'SET' <<<"$dump")"
check dump-has-muladd 1 "$(grep -c 'MULADD' <<<"$dump")"

echo "$pass passed, $fail failed"
[[ $fail -eq 0 ]]
