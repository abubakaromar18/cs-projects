#!/bin/sh
# cli_test.sh - end-to-end tests for the wc binary.
# Usage: sh tests/cli_test.sh ./wc
set -u

WC=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
cd "$TMP" || exit 1

pass=0
fail=0

# expect NAME EXPECTED_OUTPUT EXPECTED_STATUS -- ARGS...   (stdin from $STDIN)
expect() {
    name=$1; want=$2; want_status=$3; shift 4
    got=$(printf '%b' "${STDIN:-}" | "$WC" "$@" 2>/dev/null)
    status=$?
    if [ "$got" = "$(printf '%b' "$want")" ] && [ "$status" -eq "$want_status" ]; then
        pass=$((pass + 1))
    else
        fail=$((fail + 1))
        printf 'FAIL: %s\n  args: %s\n  want (%s): %s\n  got  (%s): %s\n' \
            "$name" "$*" "$want_status" "$(printf '%b' "$want")" "$status" "$got"
    fi
}

printf 'hello world\nfoo\n' > a.txt                 # 2 lines, 3 words, 16 bytes
printf 'h\303\251\tllo\n' > b.txt                     # UTF-8 + tab: 8 bytes, 7 chars
: > empty.txt
seq_file() { i=1; while [ $i -le 2000 ]; do echo $i; i=$((i + 1)); done; }
seq_file > big.txt                                   # 2000 lines, 8893 bytes

STDIN=
expect "default single file"   ' 2  3 16 a.txt'                     0 -- a.txt
expect "lines only"            '2 a.txt'                            0 -- -l a.txt
expect "words only"            '3 a.txt'                            0 -- -w a.txt
expect "bytes only"            '16 a.txt'                           0 -- -c a.txt
expect "utf-8 chars"           '7 b.txt'                            0 -- -m b.txt
expect "max line w/ tab"       '11 b.txt'                           0 -- -L b.txt
expect "empty file"            '0 0 0 empty.txt'                    0 -- empty.txt
expect "two files + total"     ' 2  3 16 a.txt\n 1  2  8 b.txt\n 3  5 24 total' 0 -- a.txt b.txt
expect "all columns"           ' 2  3 16 16 11 a.txt\n 1  2  7  8 11 b.txt\n 3  5 23 24 11 total' 0 -- -lwmcL a.txt b.txt
expect "clustered == separate" ' 2  3 a.txt' 0 -- -l -w a.txt
expect "long flags"            ' 2  3 a.txt' 0 -- --lines --words a.txt
expect "column width from total" '   0 empty.txt\n2000 big.txt\n2000 total' 0 -- -l empty.txt big.txt
expect "total=only"            '3 5 24'                             0 -- --total=only a.txt b.txt
expect "total=never"           ' 2  3 16 a.txt\n 1  2  8 b.txt'     0 -- --total=never a.txt b.txt
expect "total=always"          '2 a.txt\n2 total'                   0 -- --total=always -l a.txt
expect "missing file"          ' 2  3 16 a.txt\n 2  3 16 total'     1 -- a.txt missing.txt
expect "bad option"            ''                                   2 -- -z a.txt
expect "bad total"             ''                                   2 -- --total=maybe a.txt

STDIN='one two three\nfour\n'
expect "stdin (pipe) width 7"  '      2       4      19'            0 --
expect "stdin single column"   '2'                                  0 -- -l
expect "dash is stdin"         '      2       4      19 -\n      2       3      16 a.txt\n      4       7      35 total' 0 -- - a.txt
STDIN='no newline'
expect "no trailing newline"   '      0       2      10'            0 --

# "-- -l": operand literally named "-l"
printf 'x\ny\n' > ./-l
STDIN=
expect "file named -l"         '2 -l'                               0 -- -l -- -l

# Help/version succeed.
"$WC" --help >/dev/null 2>&1 && pass=$((pass + 1)) || { fail=$((fail + 1)); echo "FAIL: --help"; }
"$WC" --version | grep -q 'wc' && pass=$((pass + 1)) || { fail=$((fail + 1)); echo "FAIL: --version"; }

# Error message goes to stderr and names the file.
"$WC" missing.txt 2>&1 >/dev/null | grep -q 'missing.txt' && pass=$((pass + 1)) || { fail=$((fail + 1)); echo "FAIL: stderr message"; }

echo "cli: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
