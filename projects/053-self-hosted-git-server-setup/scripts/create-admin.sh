#!/usr/bin/env bash
# Create the first admin account (registration is disabled by default).
#
#   scripts/create-admin.sh <username> <email>
#
# Gitea generates a random password and prints it once; you must change it
# at first login.
set -Eeuo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
cd "$(project_root)"

[[ $# -eq 2 ]] || { sed -n '2,7p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
user="$1" email="$2"
[[ "$user" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$ ]] || die "invalid username '$user'"
[[ "$email" =~ ^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$ ]] || die "invalid email '$email'"

compose exec -T -u git gitea gitea admin user create \
  --admin --username "$user" --email "$email" \
  --random-password --must-change-password
