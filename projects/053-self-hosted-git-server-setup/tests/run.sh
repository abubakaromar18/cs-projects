#!/usr/bin/env bash
# Minimal, dependency-free test runner for the stack's shell scripts.
#
#   tests/run.sh            run every test_* function
#   tests/run.sh prune      run tests whose name contains "prune"
#
# Each test runs in its own subshell against a fresh copy of scripts/ in a
# temp dir, with `docker compose` replaced by tests/stubs/fake-compose.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "$HERE/.." && pwd)"
FILTER="${1:-}"

# ---------------------------------------------------------------- helpers --
fail() { echo "    assertion failed: $*" >&2; exit 1; }
assert_eq()       { [[ "$1" == "$2" ]] || fail "expected [$2], got [$1]${3:+ ($3)}"; }
assert_file()     { [[ -f "$1" ]] || fail "expected file $1"; }
assert_no_file()  { [[ ! -e "$1" ]] || fail "did not expect $1"; }
assert_contains() { [[ "$1" == *"$2"* ]] || fail "expected output to contain [$2], got [$1]"; }
assert_not_contains() { [[ "$1" != *"$2"* ]] || fail "did not expect [$2] in [$1]"; }

# Fresh sandbox: copy of scripts + stub, isolated backup dir and fake state.
setup() {
  T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
  mkdir -p "$T/proj" "$T/state" "$T/backups"
  cp -r "$PROJECT/scripts" "$T/proj/"
  : > "$T/state/calls.log"
  export FAKE_STATE="$T/state"
  export COMPOSE="$PROJECT/tests/stubs/fake-compose"
  export BACKUP_DIR="$T/backups"
  export BACKUP_KEEP=7 POSTGRES_USER=gitea POSTGRES_DB=gitea
  export RESTORE_WAIT_SECONDS=2
  unset FAKE_DOWN FAKE_PGDUMP_FAIL FAKE_GITEA_DUMP_EMPTY FAKE_PSQL_FAIL FAKE_HEALTH_FAIL
}
lib() { source "$T/proj/scripts/lib/common.sh"; }
# Make an empty-but-valid-looking archive with the given timestamp.
mkbackup() { : > "$BACKUP_DIR/gitea-backup-$1.tar.gz"; }

# ------------------------------------------------------- lib/common.sh -----
test_load_env_parses_quotes_and_comments() {
  setup; lib
  cat > "$T/env" <<'EOF'
# comment
PLAIN=hello
DQ="with spaces"
SQ='single'
 SPACED =x
EMPTY=
1BAD=nope
INJECT=$(touch /tmp/should-not-exist-053)
EOF
  unset PLAIN DQ SQ SPACED EMPTY INJECT
  load_env "$T/env"
  assert_eq "$PLAIN" hello
  assert_eq "$DQ" "with spaces"
  assert_eq "$SQ" single
  assert_eq "$SPACED" x
  assert_eq "${EMPTY-unset}" ""
  assert_eq "$INJECT" '$(touch /tmp/should-not-exist-053)' "values are not evaluated"
  assert_no_file /tmp/should-not-exist-053
}

test_load_env_does_not_override_existing_env() {
  setup; lib
  echo "BACKUP_KEEP=99" > "$T/env"
  BACKUP_KEEP=3 load_env "$T/env"
  export BACKUP_KEEP=3; load_env "$T/env"
  assert_eq "$BACKUP_KEEP" 3
}

test_list_backups_sorted_and_filters_junk() {
  setup; lib
  mkbackup 20261102-000000; mkbackup 20261101-120000; mkbackup 20261101-090000
  touch "$BACKUP_DIR/gitea-backup-latest.tar.gz" "$BACKUP_DIR/notes.txt" \
        "$BACKUP_DIR/gitea-backup-20261103-000000.tar.gz.partial"
  out="$(list_backups "$BACKUP_DIR" | tr '\n' ' ')"
  assert_eq "$out" "gitea-backup-20261101-090000.tar.gz gitea-backup-20261101-120000.tar.gz gitea-backup-20261102-000000.tar.gz "
}

test_backups_to_prune_keeps_newest() {
  setup; lib
  for d in 01 02 03 04 05; do mkbackup "202611${d}-000000"; done
  out="$(backups_to_prune "$BACKUP_DIR" 3 | tr '\n' ' ')"
  assert_eq "$out" "gitea-backup-20261101-000000.tar.gz gitea-backup-20261102-000000.tar.gz "
  assert_eq "$(backups_to_prune "$BACKUP_DIR" 5)" ""
  assert_eq "$(backups_to_prune "$BACKUP_DIR" 10)" ""
}

test_prune_removes_archive_and_checksum() {
  setup; lib
  for d in 01 02 03; do mkbackup "202611${d}-000000"; touch "$BACKUP_DIR/gitea-backup-202611${d}-000000.tar.gz.sha256"; done
  prune_backups "$BACKUP_DIR" 1 2>/dev/null
  assert_eq "$(ls "$BACKUP_DIR" | tr '\n' ' ')" "gitea-backup-20261103-000000.tar.gz gitea-backup-20261103-000000.tar.gz.sha256 "
}

test_prune_refuses_keep_zero() {
  setup; lib
  mkbackup 20261101-000000
  ( prune_backups "$BACKUP_DIR" 0 ) 2>/dev/null && fail "keep=0 should be refused"
  assert_file "$BACKUP_DIR/gitea-backup-20261101-000000.tar.gz"
}

test_checksum_detects_tampering() {
  setup; lib
  f="$BACKUP_DIR/gitea-backup-20261101-000000.tar.gz"
  echo "original" > "$f"
  write_checksum "$f"
  verify_checksum "$f" || fail "fresh checksum should verify"
  echo "tampered" > "$f"
  verify_checksum "$f" && fail "tampered archive should not verify"
  rm "$f.sha256"
  verify_checksum "$f" 2>/dev/null && fail "missing checksum should not verify"
  return 0
}

test_resolve_backup_forms() {
  setup; lib
  mkbackup 20261101-000000; mkbackup 20261105-000000
  assert_eq "$(resolve_backup "$BACKUP_DIR" latest)" "$BACKUP_DIR/gitea-backup-20261105-000000.tar.gz"
  assert_eq "$(resolve_backup "$BACKUP_DIR" gitea-backup-20261101-000000.tar.gz)" "$BACKUP_DIR/gitea-backup-20261101-000000.tar.gz"
  assert_eq "$(resolve_backup "$BACKUP_DIR" "$BACKUP_DIR/gitea-backup-20261101-000000.tar.gz")" "$BACKUP_DIR/gitea-backup-20261101-000000.tar.gz"
  resolve_backup "$BACKUP_DIR" nope.tar.gz && fail "missing backup should not resolve"
  resolve_backup "$T/empty-dir" latest && fail "latest in empty dir should not resolve"
  return 0
}

# ------------------------------------------------------------ backup.sh ----
test_backup_creates_verified_archive() {
  setup
  out="$("$T/proj/scripts/backup.sh" 2>"$T/err")" || { cat "$T/err"; fail "backup.sh failed"; }
  archive="$out"
  assert_file "$archive"; assert_file "$archive.sha256"
  [[ "$(basename "$archive")" =~ ^gitea-backup-[0-9]{8}-[0-9]{6}\.tar\.gz$ ]] || fail "bad name $archive"
  ( cd "$BACKUP_DIR" && sha256sum --quiet -c "$(basename "$archive").sha256" ) || fail "checksum"
  assert_eq "$(tar -tzf "$archive" | sort | tr '\n' ' ')" "db.sql.gz gitea-dump.zip metadata.env "
  mkdir "$T/x"; tar -C "$T/x" -xzf "$archive"
  assert_contains "$(gzip -dc "$T/x/db.sql.gz")" "CREATE TABLE repository"
  assert_contains "$(cat "$T/x/gitea-dump.zip")" "fake-gitea-dump"
  assert_contains "$(cat "$T/x/metadata.env")" "GITEA_VERSION=Gitea version 1.22.3"
  assert_contains "$(cat "$T/state/calls.log")" "pg_dump -U gitea -d gitea --clean --if-exists"
  assert_contains "$(cat "$T/state/calls.log")" "gitea dump --skip-db --type zip"
  assert_eq "$(find "$BACKUP_DIR" -name "*.partial" | wc -l | tr -d " ")" 0
}

test_backup_applies_retention() {
  setup
  for d in 01 02 03 04; do mkbackup "202601${d}-000000"; done
  "$T/proj/scripts/backup.sh" --keep 2 >/dev/null 2>&1 || fail "backup.sh failed"
  names="$(cd "$BACKUP_DIR" && ls ./*.tar.gz | sed 's|^\./||')"
  assert_eq "$(echo "$names" | wc -l | tr -d ' ')" 2
  assert_contains "$names" "gitea-backup-20260104-000000.tar.gz"
  assert_not_contains "$names" "20260103"
}

test_backup_fails_if_service_down() {
  setup
  FAKE_DOWN=gitea "$T/proj/scripts/backup.sh" >/dev/null 2>"$T/err" && fail "should fail"
  assert_contains "$(cat "$T/err")" "service 'gitea' is not running"
  assert_eq "$(ls "$BACKUP_DIR")" ""
}

test_backup_fails_on_pg_dump_error_without_leaving_files() {
  setup
  FAKE_PGDUMP_FAIL=1 "$T/proj/scripts/backup.sh" >/dev/null 2>&1 && fail "should fail"
  assert_eq "$(ls "$BACKUP_DIR")" "" "no archive or .partial left behind"
}

test_backup_fails_on_empty_gitea_dump() {
  setup
  FAKE_GITEA_DUMP_EMPTY=1 "$T/proj/scripts/backup.sh" >/dev/null 2>"$T/err" && fail "should fail"
  assert_contains "$(cat "$T/err")" "gitea dump produced no output"
  assert_eq "$(ls "$BACKUP_DIR")" ""
}

test_backup_rejects_bad_keep() {
  setup
  "$T/proj/scripts/backup.sh" --keep 0 >/dev/null 2>&1 && fail "keep 0"
  "$T/proj/scripts/backup.sh" --keep abc >/dev/null 2>&1 && fail "keep abc"
  "$T/proj/scripts/backup.sh" --bogus >/dev/null 2>&1 && fail "unknown flag"
  return 0
}

# ----------------------------------------------------------- restore.sh ----
make_real_backup() {
  FAKE_DUMP_ID="${1:-1}" "$T/proj/scripts/backup.sh" 2>/dev/null
  : > "$T/state/calls.log"
}

test_restore_happy_path_order_of_operations() {
  setup
  archive="$(make_real_backup)"
  "$T/proj/scripts/restore.sh" latest --yes 2>"$T/err" || { cat "$T/err"; fail "restore failed"; }
  assert_contains "$(cat "$T/state/psql_input.sql")" "CREATE TABLE repository"
  assert_eq "$(sort "$T/state/run_mount_listing" | tr '\n' ' ')" "db.sql.gz gitea-dump.zip metadata.env "
  # Extract the sequence of meaningful steps from the call log.
  steps="$(grep -oE '^(stop gitea|up -d db|exec -T db psql|run --rm|start gitea|exec -T -u git gitea gitea admin regenerate hooks)' "$T/state/calls.log" | tr '\n' '|')"
  assert_eq "$steps" "stop gitea|up -d db|exec -T db psql|run --rm|start gitea|exec -T -u git gitea gitea admin regenerate hooks|"
  assert_contains "$(cat "$T/state/calls.log")" "ON_ERROR_STOP=1 --single-transaction"
  assert_contains "$(cat "$T/err")" "restore complete from $(basename "$archive")"
}

test_restore_requires_yes_when_not_interactive() {
  setup
  make_real_backup >/dev/null
  "$T/proj/scripts/restore.sh" latest </dev/null >/dev/null 2>"$T/err" && fail "should refuse"
  assert_contains "$(cat "$T/err")" "without --yes"
  assert_not_contains "$(cat "$T/state/calls.log")" "stop gitea"
}

test_restore_refuses_bad_checksum() {
  setup
  archive="$(make_real_backup)"
  echo "corruption" >> "$archive"
  "$T/proj/scripts/restore.sh" "$archive" --yes >/dev/null 2>"$T/err" && fail "should refuse"
  assert_contains "$(cat "$T/err")" "checksum verification failed"
  assert_eq "$(cat "$T/state/calls.log")" "" "nothing touched"
}

test_restore_unknown_backup() {
  setup
  "$T/proj/scripts/restore.sh" gitea-backup-19990101-000000.tar.gz --yes >/dev/null 2>"$T/err" && fail "should fail"
  assert_contains "$(cat "$T/err")" "no backup found"
}

test_restore_stops_if_sql_load_fails() {
  setup
  make_real_backup >/dev/null
  FAKE_PSQL_FAIL=1 "$T/proj/scripts/restore.sh" latest --yes >/dev/null 2>&1 && fail "should fail"
  log="$(cat "$T/state/calls.log")"
  assert_not_contains "$log" "run --rm"
  assert_not_contains "$log" "start gitea"
}

test_restore_reports_unhealthy_gitea() {
  setup
  make_real_backup >/dev/null
  FAKE_HEALTH_FAIL=7 "$T/proj/scripts/restore.sh" latest --yes >/dev/null 2>"$T/err" && fail "should fail"
  assert_contains "$(cat "$T/err")" "did not report healthy"
}

# ------------------------------------------------------- create-admin.sh ---
test_create_admin_validates_input() {
  setup
  "$T/proj/scripts/create-admin.sh" "bad user" a@b.co >/dev/null 2>&1 && fail "bad username"
  "$T/proj/scripts/create-admin.sh" omar not-an-email >/dev/null 2>&1 && fail "bad email"
  "$T/proj/scripts/create-admin.sh" omar omar@example.com >/dev/null 2>&1 || fail "valid input"
  assert_contains "$(cat "$T/state/calls.log")" "admin user create --admin --username omar --email omar@example.com --random-password --must-change-password"
}

# --------------------------------------------------- docker-compose.yml ----
# Uses the real Docker Compose CLI to parse/interpolate the file (no daemon or
# images needed). Skipped if compose is not installed.
compose_json() { (cd "$PROJECT" && docker compose --env-file /dev/null -f docker-compose.yml config --format json 2>&1); }

test_compose_requires_password() {
  command -v docker >/dev/null && docker compose version >/dev/null 2>&1 || { echo "    (skipped: docker compose not installed)"; return 0; }
  out="$(env -u POSTGRES_PASSWORD bash -c "$(declare -f compose_json); PROJECT='$PROJECT'; compose_json")" && fail "config should fail without password"
  assert_contains "$out" "POSTGRES_PASSWORD"
}

test_compose_is_valid_and_binds_localhost() {
  command -v docker >/dev/null && docker compose version >/dev/null 2>&1 || { echo "    (skipped: docker compose not installed)"; return 0; }
  json="$(export POSTGRES_PASSWORD=test; compose_json)" || fail "compose config failed: $json"
  python3 - "$json" <<'PY' || exit 1
import json, sys
cfg = json.loads(sys.argv[1])
svc = cfg["services"]
assert set(svc) == {"db", "gitea"}, svc.keys()
ports = svc["gitea"]["ports"]
assert {p["target"] for p in ports} == {3000, 22}, ports
assert all(p["host_ip"] == "127.0.0.1" for p in ports), "ports must bind to localhost by default"
assert "ports" not in svc["db"], "postgres must not be published"
assert svc["gitea"]["depends_on"]["db"]["condition"] == "service_healthy"
env = svc["gitea"]["environment"]
assert env["GITEA__database__DB_TYPE"] == "postgres"
assert env["GITEA__service__DISABLE_REGISTRATION"] == "true"
for s in svc.values():
    assert "healthcheck" in s and s["restart"] == "unless-stopped"
assert {"gitea-data", "db-data"} <= set(cfg["volumes"])
PY
}

# ---------------------------------------------------------------- runner ---
pass=0; failed=0; failures=()
for t in $(declare -F | awk '{print $3}' | grep '^test_'); do
  [[ -z "$FILTER" || "$t" == *"$FILTER"* ]] || continue
  if ( set -e; "$t" ) ; then
    echo "ok   $t"; pass=$((pass+1))
  else
    echo "FAIL $t"; failed=$((failed+1)); failures+=("$t")
  fi
done
echo
echo "$pass passed, $failed failed"
(( failed == 0 )) || { printf '  - %s\n' "${failures[@]}"; exit 1; }
