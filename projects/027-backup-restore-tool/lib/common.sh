# shellcheck shell=bash
# common.sh - logging, error handling, locking, and timestamp helpers.
#
# Sourced by bin/bkp. Every function here is side-effect free apart from
# writing to stderr / the optional log file, which keeps them easy to test.

# Archive timestamps are always UTC in a fixed-width, lexically sortable form:
#   20261103T024100Z
# Because the format sorts lexically in chronological order, plain `sort`
# is enough to order backups - no date parsing needed for that.
readonly BKP_TS_FORMAT='%Y%m%dT%H%M%SZ'
readonly BKP_TS_REGEX='^[0-9]{8}T[0-9]{6}Z$'

# Exit codes (used by bin/bkp)
# shellcheck disable=SC2034
readonly EX_OK=0
readonly EX_ERR=1
readonly EX_USAGE=2

# log LEVEL MESSAGE... - write a timestamped line to stderr (and BKP_LOG).
log() {
  local level=$1; shift
  local line
  line="$(date -u '+%Y-%m-%dT%H:%M:%SZ') [$level] $*"
  if [[ $level != DEBUG || -n ${BKP_DEBUG:-} ]]; then
    printf '%s\n' "$line" >&2
  fi
  if [[ -n ${BKP_LOG:-} ]]; then
    printf '%s\n' "$line" >>"$BKP_LOG" || true
  fi
}

info()  { log INFO "$@"; }
warn()  { log WARN "$@"; }
debug() { log DEBUG "$@"; }

# die MESSAGE [CODE] - log an error and exit.
die() {
  log ERROR "$1"
  exit "${2:-$EX_ERR}"
}

# require_cmd CMD... - fail early with a helpful message if a tool is missing.
require_cmd() {
  local c
  for c in "$@"; do
    command -v "$c" >/dev/null 2>&1 || die "required command not found: $c"
  done
}

# now_epoch - current time in seconds. BKP_NOW lets tests pin the clock.
now_epoch() {
  if [[ -n ${BKP_NOW:-} ]]; then
    printf '%s\n' "$BKP_NOW"
  else
    date -u +%s
  fi
}

# epoch_to_ts EPOCH - format an epoch as an archive timestamp.
epoch_to_ts() {
  date -u -d "@$1" "+$BKP_TS_FORMAT"
}

# ts_to_epoch TS - parse an archive timestamp back to epoch seconds.
ts_to_epoch() {
  local ts=$1
  [[ $ts =~ $BKP_TS_REGEX ]] || return 1
  date -u -d "${ts:0:4}-${ts:4:2}-${ts:6:2} ${ts:9:2}:${ts:11:2}:${ts:13:2}" +%s
}

# validate_name NAME - backup set names become part of filenames, so keep
# them to a safe character set. "--" is reserved as the field separator.
validate_name() {
  local name=$1
  [[ $name =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || die "invalid name '$name' (use letters, digits, '.', '_', '-')" "$EX_USAGE"
  [[ $name != *--* ]] || die "invalid name '$name' ('--' is reserved as a separator)" "$EX_USAGE"
}

# with_lock DIR CMD... - run CMD while holding an exclusive lock on DIR.
# Prevents two scheduled runs (e.g. a slow backup overlapping the next cron
# tick) from writing or rotating the same destination concurrently.
with_lock() {
  local dir=$1; shift
  if ! command -v flock >/dev/null 2>&1; then
    warn "flock not available; running without a lock"
    "$@"
    return
  fi
  local lockfile="$dir/.bkp.lock"
  (
    exec 9>"$lockfile"
    if ! flock -n 9; then
      die "another bkp process holds $lockfile"
    fi
    "$@"
  )
}

# human_size BYTES - 1536 -> 1.5K
human_size() {
  local b=$1
  if command -v numfmt >/dev/null 2>&1; then
    numfmt --to=iec --suffix=B "$b"
  else
    printf '%sB\n' "$b"
  fi
}
