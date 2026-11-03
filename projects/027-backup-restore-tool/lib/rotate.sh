# shellcheck shell=bash
# rotate.sh - Grandfather-Father-Son (GFS) retention.
#
# Given a set of archives, decide which ones to keep:
#
#   keep_last    N  - the N newest archives, unconditionally
#   keep_daily   N  - the newest archive of each of the last N days that have one
#   keep_weekly  N  - ... of each of the last N ISO weeks
#   keep_monthly N  - ... of each of the last N months
#   keep_yearly  N  - ... of each of the last N years
#
# An archive survives if ANY rule keeps it. The rules are evaluated
# independently over the same newest-first list, exactly like
# `restic forget` / `borg prune`. The result is that retention thins out with
# age: lots of recent restore points, a few old ones.
#
# The selection is a pure function: archive names in on stdin, names to delete
# out on stdout. That makes it trivial to unit-test and to run as --dry-run.

# archive_ts NAME - extract the timestamp field from "set--TIMESTAMP.kind.ext".
archive_ts() {
  local base=${1##*/}
  local rest=${base#*--}
  printf '%s\n' "${rest:0:16}"
}

# _bucket RULE TS - map a timestamp to the period bucket used by a rule.
_bucket() {
  local rule=$1 ts=$2
  case $rule in
    daily)   printf '%s\n' "${ts:0:8}" ;;            # YYYYMMDD
    monthly) printf '%s\n' "${ts:0:6}" ;;            # YYYYMM
    yearly)  printf '%s\n' "${ts:0:4}" ;;            # YYYY
    weekly)                                          # ISO year-week, e.g. 2026-W45
      date -u -d "@$(ts_to_epoch "$ts")" +%G-W%V ;;
    *) return 1 ;;
  esac
}

# rotate_select LAST DAILY WEEKLY MONTHLY YEARLY
# stdin : archive basenames (any order)
# stdout: basenames that the policy does NOT keep (newest first)
rotate_select() {
  local keep_last=$1 keep_daily=$2 keep_weekly=$3 keep_monthly=$4 keep_yearly=$5
  local -a archives=()
  local line
  while IFS= read -r line; do
    [[ -n $line ]] && archives+=("$line")
  done

  # Newest first. The timestamp is fixed-width and lexically ordered, so we
  # sort on "TIMESTAMP<TAB>NAME" and strip the key afterwards.
  local -a sorted=()
  if ((${#archives[@]} > 0)); then
    mapfile -t sorted < <(
      for line in "${archives[@]}"; do
        printf '%s\t%s\n' "$(archive_ts "$line")" "$line"
      done | sort -r | cut -f2-
    )
  fi

  declare -A keep=()
  local i
  for ((i = 0; i < ${#sorted[@]} && i < keep_last; i++)); do
    keep[${sorted[i]}]=1
  done

  # For each periodic rule, walk newest -> oldest and keep the first archive
  # we see in each new bucket until we've filled `count` buckets.
  local rule count bucket last_bucket filled ts
  for rule in daily weekly monthly yearly; do
    case $rule in
      daily) count=$keep_daily ;;
      weekly) count=$keep_weekly ;;
      monthly) count=$keep_monthly ;;
      yearly) count=$keep_yearly ;;
    esac
    ((count > 0)) || continue
    last_bucket='' filled=0
    for line in "${sorted[@]}"; do
      ((filled < count)) || break
      ts=$(archive_ts "$line")
      bucket=$(_bucket "$rule" "$ts")
      if [[ $bucket != "$last_bucket" ]]; then
        keep[$line]=1
        last_bucket=$bucket
        filled=$((filled + 1))
      fi
    done
  done

  for line in "${sorted[@]}"; do
    [[ -n ${keep[$line]:-} ]] || printf '%s\n' "$line"
  done
}
