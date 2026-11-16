#!/usr/bin/env bash
# Take a consistent backup of the Gitea stack.
#
#   scripts/backup.sh [--keep N] [--dir PATH]
#
# Produces BACKUP_DIR/gitea-backup-<UTC timestamp>.tar.gz containing:
#   db.sql.gz       pg_dump of the Gitea database (plain SQL, --clean)
#   gitea-dump.zip  `gitea dump --skip-db`: repos, LFS, attachments, app.ini
#   metadata.env    versions and timestamp, for humans and restore.sh
# plus a .sha256 sidecar, then prunes so only the newest N archives remain.
#
# Safe to run from cron while Gitea is serving traffic: pg_dump takes an MVCC
# snapshot, and gitea dump reads repositories without locking writers.
set -Eeuo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
ROOT="$(project_root)"
cd "$ROOT"
load_env "$ROOT/.env"

BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_KEEP="${BACKUP_KEEP:-7}"
POSTGRES_USER="${POSTGRES_USER:-gitea}"
POSTGRES_DB="${POSTGRES_DB:-gitea}"

usage() { sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --keep) BACKUP_KEEP="${2:?--keep needs a value}"; shift 2 ;;
    --dir)  BACKUP_DIR="${2:?--dir needs a value}";  shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1 (see --help)" ;;
  esac
done

[[ "$BACKUP_KEEP" =~ ^[1-9][0-9]*$ ]] || die "--keep must be a positive integer"

# Both services must be up; a backup of a stopped DB container would fail late.
for svc in db gitea; do
  [[ -n "$(compose ps --status running -q "$svc" 2>/dev/null)" ]] \
    || die "service '$svc' is not running (start it with: make up)"
done

mkdir -p "$BACKUP_DIR"
STAGE="$(mktemp -d "${TMPDIR:-/tmp}/gitea-backup.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT

TS="$(timestamp)"
NAME="$(backup_name "$TS")"
ARCHIVE="$BACKUP_DIR/$NAME"

log "dumping database '$POSTGRES_DB'"
compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  --clean --if-exists --no-owner --no-privileges \
  | gzip -9 > "$STAGE/db.sql.gz"
# `set -o pipefail` already fails on pg_dump errors; also reject an empty dump.
[[ "$(gzip -dc "$STAGE/db.sql.gz" | head -c 1 | wc -c)" -eq 1 ]] || die "database dump is empty"

log "dumping repositories and data (gitea dump)"
compose exec -T -u git gitea \
  gitea dump --skip-db --type zip -c /data/gitea/conf/app.ini -f - \
  > "$STAGE/gitea-dump.zip"
[[ -s "$STAGE/gitea-dump.zip" ]] || die "gitea dump produced no output"

{
  echo "CREATED_UTC=$TS"
  echo "GITEA_VERSION=$(compose exec -T -u git gitea gitea --version 2>/dev/null | head -n1 | tr -d '\r')"
  echo "POSTGRES_VERSION=$(compose exec -T db postgres --version 2>/dev/null | head -n1 | tr -d '\r')"
  echo "POSTGRES_DB=$POSTGRES_DB"
} > "$STAGE/metadata.env"

# Write to a .partial name then rename, so a crash never leaves a truncated
# archive that looks valid to list_backups/restore.
tar -C "$STAGE" -czf "$ARCHIVE.partial" db.sql.gz gitea-dump.zip metadata.env
mv -f "$ARCHIVE.partial" "$ARCHIVE"
write_checksum "$ARCHIVE"

log "wrote $ARCHIVE ($(du -h "$ARCHIVE" | cut -f1))"
prune_backups "$BACKUP_DIR" "$BACKUP_KEEP"
printf '%s\n' "$ARCHIVE"
