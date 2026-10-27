#!/usr/bin/env bash
# End-to-end check against the real containers.
# Usage: make up && ./scripts/smoke_test.sh   (or just: make smoke)
set -euo pipefail

BASE="http://127.0.0.1:${GATEWAY_PORT:-8080}"
cd "$(dirname "$0")/.."

fail() { echo "FAIL: $*" >&2; exit 1; }

echo "Waiting for the gateway at $BASE ..."
for _ in $(seq 1 30); do
  curl -fsS "$BASE/health" >/dev/null 2>&1 && break
  sleep 1
done
curl -fsS "$BASE/health" | grep -q '"status": "ok"' || fail "stack is not healthy"
echo "health: ok"

before=$(curl -fsS "$BASE/api/stats" | python3 -c 'import json,sys; print(json.load(sys.stdin)["total"])')
id=$(curl -fsS -X POST "$BASE/api/notes" -H 'Content-Type: application/json' \
       -d '{"title":"smoke test","body":"hello from the host"}' \
     | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
echo "created note $id"
curl -fsS "$BASE/api/notes/$id" | grep -q 'smoke test' || fail "note $id not readable"

sleep 1
after=$(curl -fsS "$BASE/api/stats" | python3 -c 'import json,sys; print(json.load(sys.stdin)["total"])')
[ "$after" -gt "$before" ] || fail "stats did not record the event ($before -> $after)"
echo "stats: $before -> $after events"

# Service discovery: containers reach each other by Compose service name.
if docker compose exec -T gateway python -c "import urllib.request; urllib.request.urlopen('http://stats:8000/health', timeout=2)"; then
  echo "gateway -> stats over the backend network: ok"
else
  fail "gateway cannot reach stats by service name"
fi

# The backend network is internal: no route to the internet.
if docker compose exec -T stats python -c "import urllib.request; urllib.request.urlopen('http://example.com', timeout=3)" 2>/dev/null; then
  fail "stats reached the internet, but backend should be internal"
fi
echo "stats has no internet access: ok"

# Volumes outlive containers.
docker compose restart notes >/dev/null
for _ in $(seq 1 30); do
  curl -fsS "$BASE/api/notes/$id" >/dev/null 2>&1 && break
  sleep 1
done
curl -fsS "$BASE/api/notes/$id" | grep -q 'smoke test' || fail "note lost after restarting notes"
echo "note survived a container restart: ok"

curl -fsS -X DELETE "$BASE/api/notes/$id" >/dev/null
echo "ALL SMOKE TESTS PASSED"
