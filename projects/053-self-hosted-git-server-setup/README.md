# 053 · Self-hosted Git Server Setup

A production-minded Docker Compose stack for running your own Git server:
[Gitea](https://about.gitea.com/) backed by PostgreSQL, with verified,
rotating backups, a one-command restore, and a health check you can hang off
cron. Everything binds to `127.0.0.1` by default, so it is private to your
own machine until you deliberately put a reverse proxy in front.

```
            127.0.0.1:3000 (HTTP/UI/API)    127.0.0.1:2222 (git over SSH)
                        │                          │
                  ┌─────▼──────────────────────────▼─────┐
                  │  gitea  (gitea/gitea:1.22)           │──► volume gitea-data:/data
                  │  healthcheck: GET /api/healthz       │      repos, LFS, avatars, app.ini
                  └─────────────────┬────────────────────┘
                                    │ backend network (not published)
                  ┌─────────────────▼────────────────────┐
                  │  db  (postgres:16-alpine)            │──► volume db-data
                  │  healthcheck: pg_isready             │
                  └──────────────────────────────────────┘

  scripts/backup.sh ──► backups/gitea-backup-YYYYmmdd-HHMMSS.tar.gz (+ .sha256)
                          ├── db.sql.gz        pg_dump --clean --if-exists
                          ├── gitea-dump.zip   gitea dump --skip-db
                          └── metadata.env     versions + timestamp
```

## Features

- **Gitea + Postgres** wired together through `GITEA__section__KEY`
  environment variables — no hand-edited `app.ini`, install wizard locked.
- **Ordered startup**: Gitea waits for Postgres to be *healthy*, not just started.
- **Safe defaults**: registration disabled, ports on localhost only, the
  database never published, required password enforced by Compose
  (`${POSTGRES_PASSWORD:?…}`), log rotation on every container.
- **Backups** (`make backup`): online, consistent, atomic (`.partial` → rename),
  SHA-256 checksummed, and pruned to the newest *N*.
- **Restore** (`make restore`): verifies the checksum first, loads SQL in a
  single transaction with `ON_ERROR_STOP`, swaps the data volume contents,
  restarts Gitea, regenerates git hooks and waits for `/api/healthz`.
- **Health check** for cron/monitoring: is Gitea answering, and is the newest
  backup fresh and intact?
- **Admin bootstrap** (`make admin`) with a random, must-change password.

## Key concepts demonstrated

| Concept | Where |
| --- | --- |
| Declarative infrastructure, service dependency graph with health gating | `docker-compose.yml` (`depends_on: condition: service_healthy`) |
| Stateless containers + persistent named volumes | `gitea-data`, `db-data` |
| 12-factor config via environment, variable interpolation & required vars | `.env.example`, `${VAR:?msg}` |
| Network segmentation / least exposure | private `backend` network, `127.0.0.1` port bindings |
| Consistent online backups (MVCC snapshot via `pg_dump`) | `scripts/backup.sh` |
| Atomic writes (write-then-rename) and integrity checks (SHA-256) | `backup.sh`, `write_checksum`/`verify_checksum` |
| Retention policy as a pure, testable function | `backups_to_prune` in `scripts/lib/common.sh` |
| All-or-nothing restore (single transaction, fail-fast) | `scripts/restore.sh` |
| Parsing untrusted config without `eval`/`source` | `load_env` |
| Test doubles: faking an external CLI to test orchestration logic | `tests/stubs/fake-compose` |
| Defensive Bash: `set -Eeuo pipefail`, traps for cleanup, shellcheck-clean | all scripts |

## Layout

```
docker-compose.yml       the stack
.env.example             all tunables (copy to .env)
Makefile                 make help
scripts/
  backup.sh              take + checksum + prune
  restore.sh             verify + restore + health-wait
  healthcheck.sh         monitoring probe (exit code)
  create-admin.sh        first admin user
  lib/common.sh          shared, unit-tested helpers
config/
  crontab.example        nightly backup + 30-min health probe
  Caddyfile.example      optional HTTPS reverse proxy
tests/
  run.sh                 dependency-free bash test runner (23 tests)
  stubs/fake-compose     test double for `docker compose`
```

## Quick start

Requirements: Docker Engine with the Compose v2 plugin, `make`, `openssl`.

```bash
make env          # .env with a random 48-char DB password (chmod 600)
make up           # pull images and start in the background
make ps           # wait until both services show (healthy)
make admin ADMIN_USER=omar ADMIN_EMAIL=omar@example.com
#   -> prints a one-time random password; change it at first login
open http://localhost:3000
```

Clone over SSH after adding your public key in the UI:

```bash
git clone ssh://git@localhost:2222/omar/my-repo.git
```

## Backups and restore

```bash
make backup                     # -> backups/gitea-backup-20261116-031700.tar.gz
make list-backups
make restore                    # restores the newest (asks you to type 'restore')
scripts/restore.sh gitea-backup-20261110-031700.tar.gz --yes   # non-interactive
make health                     # exit 0 if Gitea is up and last backup is fresh
```

Example run:

```
$ make backup
[03:17:00] dumping database 'gitea'
[03:17:01] dumping repositories and data (gitea dump)
[03:17:04] wrote ./backups/gitea-backup-20261116-031700.tar.gz (18M)
[03:17:04] pruning old backup gitea-backup-20261108-031700.tar.gz
./backups/gitea-backup-20261116-031700.tar.gz
```

Schedule it with `config/crontab.example`. **Copy backups off the machine**
(e.g. `rclone` or `restic` to another disk or host) — a backup on the same
disk does not protect against disk failure. Restore into a scratch copy of
the stack every so often; an untested backup is a hope, not a backup.

If a restore fails while loading SQL, the transaction is rolled back and Gitea
is intentionally left **stopped** so it never serves a half-restored state;
fix the cause and run the restore again.

## Tests

```bash
make test     # 23 tests, ~5 s, no containers or images needed
make lint     # shellcheck (pip install shellcheck-py if missing)
```

The suite swaps `docker compose` for `tests/stubs/fake-compose`, which records
every call and can simulate failures (service down, `pg_dump` error, empty
dump, SQL load failure, unhealthy Gitea). It checks archive contents and
checksums, retention, the exact order of restore operations, that a corrupt
archive is rejected before anything is touched, and `.env` parsing (including
that values are never executed). The compose tests run the real
`docker compose config` to verify the file parses, requires a password, keeps
ports on localhost and gates Gitea on a healthy database.

All 23 tests pass and the scripts are shellcheck-clean. Note: the build
environment for this project could not pull images from Docker Hub, so the
stack was validated with `docker compose config` and the stubbed tests rather
than a live `make up`; run `make up && make backup && make restore` on your
machine for an end-to-end check.

## Possible extensions

- Encrypt archives at rest (`age` or `gpg`) and push them off-site with `restic`.
- Add a Gitea Actions runner (`gitea/act_runner`) service for CI.
- Put Caddy/Traefik in the compose file for automatic HTTPS and add fail2ban for SSH.
- Use SSH passthrough so `git@host:repo` works on port 22 of the host.
- Point-in-time recovery for Postgres with WAL archiving (pgBackRest/WAL-G).
- An end-to-end test that boots the real stack, pushes a repo, backs up,
  wipes the volumes, restores and verifies the commit is back.
