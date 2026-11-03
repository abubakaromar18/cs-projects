# shellcheck shell=bash
# End-to-end tests that drive bin/bkp against real files in a temp dir.

_make_tree() {
  mkdir -p "$T/src/sub dir"
  echo hello >"$T/src/a.txt"
  echo 'nested file' >"$T/src/sub dir/b.txt"
  printf '\x00\x01binary' >"$T/src/bin.dat"
}

_make_db() {
  sqlite3 "$T/app.db" "CREATE TABLE notes(id INTEGER PRIMARY KEY, body TEXT);
                       INSERT INTO notes(body) VALUES ('first'), ('second');"
}

test_cli_help_and_version() {
  assert_contains "$("$BKP" help)" 'RETENTION'
  assert_contains "$("$BKP" version)" 'bkp 1.'
}

test_cli_unknown_command_is_usage_error() {
  set +e
  "$BKP" frobnicate >/dev/null 2>&1
  assert_eq "$?" 2
}

test_cli_dir_backup_and_restore_roundtrip() {
  _make_tree
  local archive
  archive=$("$BKP" backup --source "dir:$T/src" --dest "$T/backups" --name site)
  assert_file "$archive"
  assert_file "$archive.sha256"
  [[ ${archive##*/} =~ ^site--[0-9]{8}T[0-9]{6}Z\.dir\.tar\.gz$ ]] || fail "bad name: $archive"

  "$BKP" restore --dest "$T/backups" --name site --target "$T/out"
  diff -r "$T/src" "$T/out" || fail "restored tree differs from source"
}

test_cli_default_name_from_source() {
  mkdir -p "$T/my web root"
  echo x >"$T/my web root/f"
  local archive
  archive=$("$BKP" backup --source "dir:$T/my web root" --dest "$T/b")
  assert_contains "${archive##*/}" 'my_web_root--'
}

test_cli_sqlite_backup_and_restore_roundtrip() {
  _make_db
  "$BKP" backup --source "sqlite:$T/app.db" --dest "$T/b" --name db >/dev/null
  # Mutate the live db after the backup; restore must bring back the snapshot.
  sqlite3 "$T/app.db" "DELETE FROM notes;"
  "$BKP" restore --dest "$T/b" --name db --target "$T/restored.db"
  assert_eq "$(sqlite3 "$T/restored.db" 'SELECT group_concat(body) FROM notes;')" 'first,second'
}

test_cli_restore_refuses_to_overwrite_without_force() {
  _make_db
  "$BKP" backup --source "sqlite:$T/app.db" --dest "$T/b" --name db >/dev/null
  assert_fails "$BKP" restore --dest "$T/b" --name db --target "$T/app.db"
  assert_contains "$ERR" '--force'
  "$BKP" restore --dest "$T/b" --name db --target "$T/app.db" --force
}

test_cli_restore_refuses_nonempty_dir_without_force() {
  _make_tree
  "$BKP" backup --source "dir:$T/src" --dest "$T/b" --name s >/dev/null
  mkdir -p "$T/out" && touch "$T/out/existing"
  assert_fails "$BKP" restore --dest "$T/b" --name s --target "$T/out"
  "$BKP" restore --dest "$T/b" --name s --target "$T/out" --force
  assert_file "$T/out/a.txt"
}

test_cli_verify_detects_corruption() {
  _make_tree
  local archive
  archive=$("$BKP" backup --source "dir:$T/src" --dest "$T/b" --name s)
  assert_contains "$("$BKP" verify --dest "$T/b")" 'OK'
  # Flip a byte in the middle of the archive.
  printf 'X' | dd of="$archive" bs=1 seek=20 conv=notrunc status=none
  assert_fails "$BKP" verify --dest "$T/b"
  assert_contains "$ERR" 'failed verification'
  # ...and restore refuses to use it.
  assert_fails "$BKP" restore --dest "$T/b" --name s --target "$T/out"
  assert_contains "$ERR" 'refusing to restore'
  assert_no_file "$T/out"
}

test_cli_rotation_after_backup_applies_policy() {
  _make_db
  local base i
  base=$(epoch '2026-03-01 02:00:00')
  for ((i = 0; i < 10; i++)); do
    BKP_NOW=$((base + i * 86400)) "$BKP" backup --source "sqlite:$T/app.db" --dest "$T/b" \
      --name db --keep-last 2 --keep-daily 0 --keep-weekly 0 --keep-monthly 0 >/dev/null
  done
  assert_eq "$(count_archives "$T/b")" 2
  # Sidecars are removed along with their archives.
  local sums=("$T"/b/*.sha256)
  assert_eq "${#sums[@]}" 2
  assert_file "$T/b/db--20260310T020000Z.sqlite.gz"
  assert_file "$T/b/db--20260309T020000Z.sqlite.gz"
}

test_cli_rotate_dry_run_deletes_nothing() {
  _make_db
  local i
  for i in 1 2 3; do
    BKP_NOW=$(epoch "2026-03-0$i 00:00:00") "$BKP" backup --source "sqlite:$T/app.db" \
      --dest "$T/b" --name db --no-rotate >/dev/null
  done
  local out
  out=$("$BKP" rotate --dest "$T/b" --name db --keep-last 1 --keep-daily 0 \
    --keep-weekly 0 --keep-monthly 0 --dry-run)
  assert_contains "$out" 'would delete db--20260302T000000Z.sqlite.gz'
  assert_eq "$(count_archives "$T/b")" 3
}

test_cli_rotate_refuses_zero_policy() {
  mkdir -p "$T/b"
  assert_fails "$BKP" rotate --dest "$T/b" --name db --keep-last 0 --keep-daily 0 \
    --keep-weekly 0 --keep-monthly 0 --keep-yearly 0
  assert_contains "$ERR" 'all-zero'
}

test_cli_rotation_only_touches_its_own_set() {
  _make_db
  _make_tree
  local i
  for i in 1 2 3; do
    BKP_NOW=$(epoch "2026-03-0$i 00:00:00") "$BKP" backup --source "dir:$T/src" \
      --dest "$T/b" --name web --no-rotate >/dev/null
  done
  BKP_NOW=$(epoch '2026-03-04 00:00:00') "$BKP" backup --source "sqlite:$T/app.db" \
    --dest "$T/b" --name db --keep-last 1 --keep-daily 0 --keep-weekly 0 --keep-monthly 0 >/dev/null
  assert_eq "$(count_archives "$T/b")" 4
}

test_cli_point_in_time_restore_with_at() {
  _make_db
  BKP_NOW=$(epoch '2026-03-01 00:00:00') "$BKP" backup --source "sqlite:$T/app.db" --dest "$T/b" --name db >/dev/null
  sqlite3 "$T/app.db" "INSERT INTO notes(body) VALUES ('third');"
  BKP_NOW=$(epoch '2026-03-02 00:00:00') "$BKP" backup --source "sqlite:$T/app.db" --dest "$T/b" --name db >/dev/null

  "$BKP" restore --dest "$T/b" --name db --at 20260301T120000Z --target "$T/old.db"
  assert_eq "$(sqlite3 "$T/old.db" 'SELECT count(*) FROM notes;')" 2
  "$BKP" restore --dest "$T/b" --name db --target "$T/new.db"
  assert_eq "$(sqlite3 "$T/new.db" 'SELECT count(*) FROM notes;')" 3
  assert_fails "$BKP" restore --dest "$T/b" --name db --at 20250101T000000Z --target "$T/x.db"
}

test_cli_list_shows_archives() {
  _make_tree
  BKP_NOW=$(epoch '2026-03-01 00:00:00') "$BKP" backup --source "dir:$T/src" --dest "$T/b" --name web >/dev/null
  local out
  out=$("$BKP" list --dest "$T/b" 2>/dev/null)
  assert_contains "$out" 'web'
  assert_contains "$out" '20260301T000000Z'
  assert_contains "$out" 'present'
}

test_cli_rejects_tar_slip_archive() {
  # Hand-craft a malicious archive whose member escapes the restore dir.
  # (GNU tar strips "../" when creating, so build it with Python's tarfile.)
  mkdir -p "$T/b"
  local name="bad--20260301T000000Z.dir.tar.gz"
  python3 - "$T/b/$name" <<'PY'
import io, sys, tarfile
with tarfile.open(sys.argv[1], "w:gz") as tf:
    data = b"pwned\n"
    info = tarfile.TarInfo("../payload")
    info.size = len(data)
    tf.addfile(info, io.BytesIO(data))
PY
  (cd "$T/b" && sha256sum "$name" >"$name.sha256")
  assert_fails "$BKP" restore --dest "$T/b" --name bad --target "$T/out"
  assert_contains "$ERR" 'unsafe path'
  assert_no_file "$T/payload"
}

test_cli_rejects_bad_names_and_sources() {
  _make_tree
  assert_fails "$BKP" backup --source "dir:$T/src" --dest "$T/b" --name 'a--b'
  assert_fails "$BKP" backup --source "dir:$T/src" --dest "$T/b" --name '../etc'
  assert_fails "$BKP" backup --source "ftp:$T/src" --dest "$T/b"
  assert_fails "$BKP" backup --source "dir:$T/nope" --dest "$T/b"
  assert_fails "$BKP" backup --source "dir:$T/src" --dest "$T/b" --keep-last -1
}

test_cli_config_file_supplies_defaults() {
  _make_tree
  cat >"$T/bkp.conf" <<EOF
# comment line
source = ignored-because-of-spaces
EOF
  assert_fails "$BKP" backup --config "$T/bkp.conf"
  cat >"$T/bkp.conf" <<EOF
# example config
source=dir:$T/src
dest=$T/b
name=fromconf   # trailing comment
keep_last=5
EOF
  local archive
  archive=$("$BKP" backup --config "$T/bkp.conf")
  assert_contains "${archive##*/}" 'fromconf--'
  # Command-line flags win over the config file.
  archive=$(BKP_NOW=$(epoch '2030-01-01 00:00:00') "$BKP" backup --config "$T/bkp.conf" --name override)
  assert_contains "${archive##*/}" 'override--'
}

test_cli_config_cannot_execute_code() {
  cat >"$T/evil.conf" <<EOF
name=\$(touch $T/owned)
EOF
  "$BKP" list --config "$T/evil.conf" --dest "$T" >/dev/null 2>&1 || true
  assert_no_file "$T/owned"
}

test_cli_concurrent_runs_are_locked() {
  _make_tree
  mkdir -p "$T/b"
  # Hold the lock from another process, then try to back up.
  exec 8>"$T/b/.bkp.lock"
  flock -n 8
  assert_fails "$BKP" backup --source "dir:$T/src" --dest "$T/b" --name s
  assert_contains "$ERR" 'another bkp process'
  exec 8>&-
  "$BKP" backup --source "dir:$T/src" --dest "$T/b" --name s >/dev/null
}

test_cli_schedule_prints_cron_line() {
  local out
  out=$("$BKP" schedule --cron '15 2 * * *' --log /var/log/bkp.log -- \
    --source 'dir:/srv/my site' --dest /backups --name site)
  assert_contains "$out" '15 2 * * * '
  assert_contains "$out" 'backup --source dir:/srv/my\ site'
  assert_contains "$out" '>>/var/log/bkp.log 2>&1'
  assert_contains "$out" '# bkp:site'
}

test_cli_schedule_install_is_idempotent() {
  # A fake `crontab` that stores the table in a file.
  cat >"$T/fakecrontab" <<EOF
#!/usr/bin/env bash
if [[ \$1 == -l ]]; then cat "$T/table" 2>/dev/null; else cat >"$T/table"; fi
EOF
  chmod +x "$T/fakecrontab"
  echo '0 0 * * * echo unrelated' >"$T/table"
  local i
  for i in 1 2; do
    BKP_CRONTAB="$T/fakecrontab" "$BKP" schedule --cron "0 $i * * *" --install -- \
      --source dir:/srv --dest /b --name site
  done
  assert_eq "$(grep -c 'bkp:site' "$T/table")" 1
  assert_contains "$(cat "$T/table")" '0 2 * * *'
  assert_contains "$(cat "$T/table")" 'echo unrelated'
}

test_cli_schedule_validates_cron() {
  assert_fails "$BKP" schedule --cron '* * *' -- --name x
  assert_fails "$BKP" schedule --cron '0 2 * * mon;rm' -- --name x
  assert_fails "$BKP" schedule --cron '0 2 * * *' -- --source dir:/x --dest /b
}
