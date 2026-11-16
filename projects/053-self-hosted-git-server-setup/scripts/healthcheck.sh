#!/usr/bin/env bash
# Check that Gitea answers on its published port and that the newest backup
# is recent. Exit 0 = healthy, 1 = problem (suitable for cron/monitoring).
#
#   scripts/healthcheck.sh [--max-backup-age-hours N]
set -Euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
ROOT="$(project_root)"
cd "$ROOT" || exit 1
load_env "$ROOT/.env"

MAX_AGE_H=26   # daily backups + slack
[[ "${1:-}" == "--max-backup-age-hours" ]] && MAX_AGE_H="${2:?value required}"

url="http://${GITEA_BIND:-127.0.0.1}:${GITEA_HTTP_PORT:-3000}/api/healthz"
[[ "${GITEA_BIND:-}" == "0.0.0.0" ]] && url="http://127.0.0.1:${GITEA_HTTP_PORT:-3000}/api/healthz"
status=0

if curl -fsS --max-time 5 "$url" >/dev/null 2>&1; then
  log "OK   gitea responds at $url"
else
  log "FAIL gitea not reachable at $url"; status=1
fi

dir="${BACKUP_DIR:-./backups}"
latest="$(list_backups "$dir" | tail -n1)"
if [[ -z "$latest" ]]; then
  log "WARN no backups found in $dir"; status=1
else
  age_h=$(( ( $(date +%s) - $(stat -c %Y "$dir/$latest") ) / 3600 ))
  if (( age_h > MAX_AGE_H )); then
    log "FAIL newest backup $latest is ${age_h}h old (> ${MAX_AGE_H}h)"; status=1
  elif verify_checksum "$dir/$latest"; then
    log "OK   newest backup $latest (${age_h}h old, checksum valid)"
  else
    log "FAIL newest backup $latest has a bad checksum"; status=1
  fi
fi
exit "$status"
