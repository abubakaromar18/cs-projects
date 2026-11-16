#!/usr/bin/env bash
# Restore the Gitea stack from a backup made by backup.sh.
#
#   scripts/restore.sh <archive | name | latest> [--yes]
#
# DESTRUCTIVE: replaces the current database and Gitea data volume.
# Steps: verify checksum -> extract -> stop gitea -> load SQL into postgres
#        -> replace /data contents from gitea-dump.zip -> start gitea
#        -> regenerate git hooks -> wait for /api/healthz.
set -Eeuo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
ROOT="$(project_root)"
cd "$ROOT"
load_env "$ROOT/.env"

BACKUP_DIR="${BACKUP_DIR:-./backups}"
POSTGRES_USER="${POSTGRES_USER:-gitea}"
POSTGRES_DB="${POSTGRES_DB:-gitea}"
WAIT_SECONDS="${RESTORE_WAIT_SECONDS:-120}"

usage() { sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; }

TARGET="" ASSUME_YES=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--yes) ASSUME_YES=1; shift ;;
    -h|--help) usage; exit 0 ;;
    -*) die "unknown option: $1" ;;
    *) [[ -z "$TARGET" ]] || die "only one archive may be given"; TARGET="$1"; shift ;;
  esac
done
[[ -n "$TARGET" ]] || { usage; exit 2; }

ARCHIVE="$(resolve_backup "$BACKUP_DIR" "$TARGET")" || die "no backup found for '$TARGET' in $BACKUP_DIR"
log "selected $ARCHIVE"

verify_checksum "$ARCHIVE" || die "checksum verification failed for $ARCHIVE - refusing to restore"

STAGE="$(mktemp -d "${TMPDIR:-/tmp}/gitea-restore.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT
tar -C "$STAGE" -xzf "$ARCHIVE"
for f in db.sql.gz gitea-dump.zip metadata.env; do
  [[ -s "$STAGE/$f" ]] || die "archive is missing $f"
done
gzip -t "$STAGE/db.sql.gz" || die "db.sql.gz is corrupt"
log "backup metadata:"; sed 's/^/    /' "$STAGE/metadata.env" >&2

if (( ! ASSUME_YES )); then
  [[ -t 0 ]] || die "refusing to restore non-interactively without --yes"
  read -r -p "This will OVERWRITE the current Gitea database and data. Type 'restore' to continue: " answer
  [[ "$answer" == "restore" ]] || die "aborted"
fi

log "stopping gitea"
compose stop gitea

log "ensuring database is up"
compose up -d db
for ((i = 0; i < WAIT_SECONDS; i++)); do
  compose exec -T db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1 && break
  sleep 1
done
compose exec -T db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1 \
  || die "database did not become ready"

log "loading database dump"
# The dump was taken with --clean --if-exists, so it drops objects first.
# ON_ERROR_STOP + a single transaction makes the load all-or-nothing.
gzip -dc "$STAGE/db.sql.gz" \
  | compose exec -T db psql -q -v ON_ERROR_STOP=1 --single-transaction \
      -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null

log "restoring /data from gitea-dump.zip"
# Runs in a throw-away container that shares the gitea-data volume.
# Layout of a gitea dump: app.ini, custom/, data/, repos/, log/.
compose run --rm --no-deps -T -v "$STAGE:/restore:ro" --entrypoint sh gitea -euc '
  work=$(mktemp -d)
  unzip -q /restore/gitea-dump.zip -d "$work"
  mkdir -p /data/gitea/conf /data/git/repositories
  find /data/gitea -mindepth 1 -maxdepth 1 ! -name conf -exec rm -rf {} +
  find /data/git/repositories -mindepth 1 -maxdepth 1 -exec rm -rf {} +
  cp "$work/app.ini" /data/gitea/conf/app.ini
  [ -d "$work/data" ]   && cp -a "$work/data/." /data/gitea/
  [ -d "$work/custom" ] && cp -a "$work/custom/." /data/gitea/
  [ -d "$work/repos" ]  && cp -a "$work/repos/." /data/git/repositories/
  chown -R git:git /data/gitea /data/git
  rm -rf "$work"
'

log "starting gitea"
compose start gitea

log "waiting for gitea to become healthy"
healthy=0
for ((i = 0; i < WAIT_SECONDS; i++)); do
  if compose exec -T gitea curl -fsS http://localhost:3000/api/healthz >/dev/null 2>&1; then
    healthy=1; break
  fi
  sleep 1
done
(( healthy )) || die "gitea did not report healthy within ${WAIT_SECONDS}s (check: make logs)"

# Server-side hooks embed absolute paths; regenerate them for this install.
compose exec -T -u git gitea gitea admin regenerate hooks >/dev/null

log "restore complete from $(basename "$ARCHIVE")"
