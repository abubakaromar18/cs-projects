# shellcheck shell=bash
# Unit tests for the pure GFS selection function in lib/rotate.sh.

_load_rotate() {
  # shellcheck source=lib/common.sh
  source "$ROOT/lib/common.sh"
  # shellcheck source=lib/rotate.sh
  source "$ROOT/lib/rotate.sh"
}

test_rotate_archive_ts_parses_name_with_dashes() {
  _load_rotate
  assert_eq "$(archive_ts 'my-site--20261103T024100Z.dir.tar.gz')" 20261103T024100Z
}

test_rotate_keep_last_only() {
  _load_rotate
  local out
  out=$(printf '%s\n' \
    a--20260101T000000Z.sqlite.gz \
    a--20260103T000000Z.sqlite.gz \
    a--20260102T000000Z.sqlite.gz \
    a--20260104T000000Z.sqlite.gz | rotate_select 2 0 0 0 0)
  assert_eq "$out" $'a--20260102T000000Z.sqlite.gz\na--20260101T000000Z.sqlite.gz'
}

test_rotate_daily_keeps_newest_per_day() {
  _load_rotate
  local out
  # Three backups on Jan 2, one on Jan 1. Daily=2 keeps the newest on each day.
  out=$(printf '%s\n' \
    a--20260101T120000Z.sqlite.gz \
    a--20260102T010000Z.sqlite.gz \
    a--20260102T080000Z.sqlite.gz \
    a--20260102T230000Z.sqlite.gz | rotate_select 0 2 0 0 0)
  assert_eq "$out" $'a--20260102T080000Z.sqlite.gz\na--20260102T010000Z.sqlite.gz'
}

test_rotate_weekly_uses_iso_weeks() {
  _load_rotate
  local out
  # 2026-01-04 is a Sunday (ISO week 1); 2026-01-05 is Monday (week 2).
  # 2026-01-01..04 are all week 1, so only the newest of them survives.
  out=$(printf '%s\n' \
    a--20260101T000000Z.sqlite.gz \
    a--20260104T000000Z.sqlite.gz \
    a--20260105T000000Z.sqlite.gz | rotate_select 0 0 2 0 0)
  assert_eq "$out" 'a--20260101T000000Z.sqlite.gz'
}

test_rotate_monthly_and_yearly() {
  _load_rotate
  local out
  out=$(printf '%s\n' \
    a--20240615T000000Z.sqlite.gz \
    a--20250101T000000Z.sqlite.gz \
    a--20250301T000000Z.sqlite.gz \
    a--20250315T000000Z.sqlite.gz \
    a--20250401T000000Z.sqlite.gz | rotate_select 0 0 0 2 2)
  # monthly=2 keeps 0401 (Apr) and 0315 (Mar); yearly=2 keeps 0401 (2025)
  # and 20240615 (2024). Dropped: 0301 (older in March) and 0101.
  assert_eq "$out" $'a--20250301T000000Z.sqlite.gz\na--20250101T000000Z.sqlite.gz'
}

test_rotate_rules_are_a_union() {
  _load_rotate
  local out
  out=$(printf '%s\n' \
    a--20260101T000000Z.sqlite.gz \
    a--20260201T000000Z.sqlite.gz \
    a--20260301T000000Z.sqlite.gz | rotate_select 1 0 0 3 0)
  assert_eq "$out" ''
}

test_rotate_empty_input() {
  _load_rotate
  assert_eq "$(printf '' | rotate_select 3 7 4 6 0)" ''
}

test_rotate_simulated_90_days_of_daily_backups() {
  _load_rotate
  # Simulate one backup per day for 90 days and apply the default policy.
  local start i out kept
  start=$(epoch '2026-01-01 02:00:00')
  out=$(for ((i = 0; i < 90; i++)); do
    printf 'a--%s.sqlite.gz\n' "$(epoch_to_ts $((start + i * 86400)))"
  done | rotate_select 3 7 4 6 0)
  kept=$((90 - $(printf '%s\n' "$out" | grep -c .)))
  # last 3 are inside the 7 dailies; 4 weeklies overlap the dailies by ~1;
  # 6 monthlies reach back to January. The total stays small and bounded.
  ((kept >= 10 && kept <= 14)) || fail "expected 10-14 kept, got $kept"
  # The very first backup (Jan 1) is the oldest in January -> not the
  # newest of its month, so it must be rotated out...
  assert_contains "$out" 'a--20260101T020000Z.sqlite.gz'
  # ...while the newest backup of January (Jan 31) is kept as a monthly.
  [[ $out != *'a--20260131T020000Z'* ]] || fail "Jan 31 should be kept as a monthly"
}
