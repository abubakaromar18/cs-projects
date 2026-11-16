#!/usr/bin/env bash
# Shared helpers for the backup/restore/admin scripts.
# Sourced, not executed. Pure functions here are unit-tested in tests/.

# shellcheck disable=SC2034  # variables are used by the sourcing scripts

# Archive names look like: gitea-backup-20261116-024500.tar.gz
# The fixed-width UTC timestamp means lexical order == chronological order,
# which is what makes pruning a simple sort.
BACKUP_PREFIX="gitea-backup-"
BACKUP_SUFFIX=".tar.gz"

log()  { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; }
die()  { log "ERROR: $*"; exit 1; }

# Project root = parent of scripts/.
project_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd
}

# Load KEY=VALUE pairs from .env without executing it as shell code.
# Values already set in the environment win, so CI/tests can override them.
load_env() {
  local file="$1" line key value
  [[ -f "$file" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ -z "$line" || "$line" == \#* ]] && continue
    [[ "$line" == *=* ]] || continue
    key="${line%%=*}"; value="${line#*=}"
    key="${key//[[:space:]]/}"
    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
    # Strip one layer of matching quotes.
    if [[ "$value" =~ ^\"(.*)\"$ || "$value" =~ ^\'(.*)\'$ ]]; then
      value="${BASH_REMATCH[1]}"
    fi
    if [[ -z "${!key+x}" ]]; then
      export "$key=$value"
    fi
  done < "$file"
}

# The compose command can be overridden (e.g. COMPOSE="docker-compose").
compose() {
  # shellcheck disable=SC2086
  ${COMPOSE:-docker compose} "$@"
}

timestamp() { date -u +%Y%m%d-%H%M%S; }

backup_name() { printf '%s%s%s' "$BACKUP_PREFIX" "$1" "$BACKUP_SUFFIX"; }

# Is $1 a well-formed archive name?
is_backup_name() {
  [[ "$1" =~ ^gitea-backup-[0-9]{8}-[0-9]{6}\.tar\.gz$ ]]
}

# Print backup archives in DIR, oldest first, one per line (basenames).
list_backups() {
  local dir="$1" f
  [[ -d "$dir" ]] || return 0
  for f in "$dir"/"$BACKUP_PREFIX"*"$BACKUP_SUFFIX"; do
    [[ -e "$f" ]] || continue
    f="$(basename "$f")"
    is_backup_name "$f" && printf '%s\n' "$f"
  done | LC_ALL=C sort
}

# Retention policy: keep the newest KEEP archives, print the ones to delete.
# Separated from the deletion itself so it can be tested and dry-run.
backups_to_prune() {
  local dir="$1" keep="$2" total
  [[ "$keep" =~ ^[0-9]+$ ]] || die "BACKUP_KEEP must be a non-negative integer (got '$keep')"
  total=$(list_backups "$dir" | wc -l)
  (( total > keep )) || return 0
  list_backups "$dir" | head -n "$(( total - keep ))"
}

prune_backups() {
  local dir="$1" keep="$2" f
  # A keep of 0 would delete the archive we just made: refuse.
  (( keep >= 1 )) || die "refusing to prune with BACKUP_KEEP=$keep (must be >= 1)"
  while IFS= read -r f; do
    [[ -n "$f" ]] || continue
    log "pruning old backup $f"
    rm -f -- "$dir/$f" "$dir/$f.sha256"
  done < <(backups_to_prune "$dir" "$keep")
}

# Write "<sha256>  <name>" next to the archive (sha256sum -c format).
write_checksum() {
  local archive="$1"
  ( cd "$(dirname "$archive")" && sha256sum "$(basename "$archive")" > "$(basename "$archive").sha256" )
}

verify_checksum() {
  local archive="$1" sum="$1.sha256"
  [[ -f "$sum" ]] || { log "missing checksum file $sum"; return 1; }
  ( cd "$(dirname "$archive")" && sha256sum --quiet -c "$(basename "$sum")" ) >/dev/null 2>&1
}

# Resolve the argument given to restore.sh: a path, a bare name, or "latest".
resolve_backup() {
  local dir="$1" want="$2" latest
  if [[ "$want" == "latest" ]]; then
    latest="$(list_backups "$dir" | tail -n 1)"
    [[ -n "$latest" ]] || return 1
    printf '%s/%s\n' "$dir" "$latest"
  elif [[ -f "$want" ]]; then
    printf '%s\n' "$want"
  elif [[ -f "$dir/$want" ]]; then
    printf '%s/%s\n' "$dir" "$want"
  else
    return 1
  fi
}
