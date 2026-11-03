# 027 · Backup & Restore Tool

`bkp` is a small, dependency-light backup tool written in Bash. It takes
scheduled dumps of a directory, a SQLite database or a PostgreSQL database,
stores each one with a SHA-256 checksum, thins old backups out with a
**grandfather-father-son** rotation policy, and restores them safely.

```
bkp backup   --source KIND:TARGET --dest DIR [--name NAME] [RETENTION] [--no-rotate]
bkp list     --dest DIR [--name NAME]
bkp verify   --dest DIR [ARCHIVE...]
bkp restore  --dest DIR --target PATH (--name NAME [--at TIMESTAMP] | ARCHIVE) [--force]
bkp rotate   --dest DIR --name NAME [RETENTION] [--dry-run]
bkp schedule --cron "MIN HOUR DOM MON DOW" [--log FILE] [--install] -- BACKUP-ARGS...
```

| Source              | How it is dumped                                  | Archive name                    |
|---------------------|---------------------------------------------------|---------------------------------|
| `dir:/srv/www`      | `tar` + gzip, paths relative to the root          | `www--20261103T021500Z.dir.tar.gz` |
| `sqlite:/var/app.db`| SQLite online-backup API (`.backup`) + gzip       | `app--20261103T021500Z.sqlite.gz`  |
| `postgres:appdb`    | `pg_dump -Fc` (custom, compressed format)         | `appdb--20261103T021500Z.pg.dump`  |

Retention flags (defaults in brackets): `--keep-last [3]`, `--keep-daily [7]`,
`--keep-weekly [4]`, `--keep-monthly [6]`, `--keep-yearly [0]`.

## CS concepts demonstrated

- **Retention as a pure function.** `lib/rotate.sh` maps a list of archive
  names to the ones to delete. Each GFS rule walks archives newest-first and
  keeps the first one it sees in each new time bucket (day, ISO week, month,
  year); an archive survives if *any* rule keeps it. One backup a day for
  90 days collapses to about a dozen restore points, dense near "now" and
  sparse in the past.
- **Sortable timestamps.** Names use fixed-width UTC timestamps
  (`20261103T021500Z`), so lexical order is chronological order and plain
  `sort` orders backups. The kind is encoded in the extension, so restore needs
  no extra metadata.
- **Atomic writes.** A dump is written to a hidden `.partial` file and moved
  into place with `rename(2)`, which is atomic within a filesystem. A crash
  never leaves a half-written file that looks like a real backup.
- **Crash-consistent database snapshots.** `cp` on a live SQLite file can catch
  a torn write. The online-backup API copies a consistent snapshot. Restores
  run `PRAGMA integrity_check` before the file is renamed into place.
- **Integrity checking.** Each archive has a `.sha256` sidecar. `verify`
  checks it, and `restore` refuses to use an archive that fails the check.
- **Mutual exclusion.** `flock` on `DEST/.bkp.lock` keeps two cron runs from
  writing or rotating the same destination at once.
- **Defensive input handling.** Archives with absolute or `../` member paths
  are rejected ("tar slip"). Config files are parsed as `KEY=VALUE` and never
  `source`d, so they cannot run code. Set names are checked against a whitelist.
  Cron fields are validated, and generated cron lines are `printf %q`-quoted
  with `%` escaped.
- **Idempotent scheduling.** `schedule --install` tags its crontab line with
  `# bkp:NAME` and replaces any earlier line for that set.

## Layout

```
bin/bkp            CLI entry point: argument parsing, commands
lib/common.sh      logging, errors, locking, timestamp helpers
lib/sources.sh     dump/restore for each source kind, tar-slip guard
lib/rotate.sh      grandfather-father-son selection (pure function)
tests/run_tests.sh dependency-free test runner + assertions
tests/test_*.sh    unit tests (rotation) and end-to-end CLI tests
bkp.conf.example   sample config file
```

## Requirements

Bash 4+, GNU coreutils (`date -d`, `sha256sum`, `stat -c`), `tar`, `gzip`,
and `flock` (util-linux). `sqlite3` is needed for SQLite sources, and
`pg_dump`/`pg_restore` for PostgreSQL. On macOS, install `coreutils` and
`util-linux` from Homebrew and put the GNU tools first on your `PATH`.

## Build, run, test

No build step is needed.

```bash
make test        # 30 tests: rotation unit tests + end-to-end CLI tests
make lint        # shellcheck
make install     # copies to ~/.local/share/bkp, links ~/.local/bin/bkp
```

The test runner needs no framework. Each `test_*` function runs in its own
subshell with a fresh temp directory. `BKP_NOW=<epoch>` pins the clock, so
rotation over weeks of backups can be simulated in milliseconds. The
PostgreSQL path is not covered by the automated tests because it needs a
running server. Directories and SQLite are tested end to end.

## Example

```console
$ for d in 01 02 03 04 05; do
>   BKP_NOW=$(date -u -d "2026-11-$d 02:15" +%s) bkp backup \
>     --source sqlite:/tmp/demo/app.db --dest /tmp/demo/b --name app \
>     --keep-last 2 --keep-daily 3 --keep-weekly 0 --keep-monthly 0
> done
[INFO] backing up sqlite:/tmp/demo/app.db -> app--20261101T021500Z.sqlite.gz
[INFO] wrote app--20261101T021500Z.sqlite.gz (204B)
...
[INFO] rotated out app--20261101T021500Z.sqlite.gz
...
[INFO] rotated out app--20261102T021500Z.sqlite.gz

$ bkp list --dest /tmp/demo/b
SET                      TIMESTAMP         KIND          SIZE  CHECKSUM
app                      20261103T021500Z  sqlite        204B  present
app                      20261104T021500Z  sqlite        204B  present
app                      20261105T021500Z  sqlite        204B  present

$ bkp verify --dest /tmp/demo/b
OK      app--20261103T021500Z.sqlite.gz
OK      app--20261104T021500Z.sqlite.gz
OK      app--20261105T021500Z.sqlite.gz

$ bkp restore --dest /tmp/demo/b --name app --at 20261104T120000Z --target /tmp/demo/r.db
[INFO] restoring app--20261104T021500Z.sqlite.gz -> /tmp/demo/r.db
[INFO] restore complete

$ bkp schedule --cron '15 2 * * *' --log /var/log/bkp.log -- \
>   --source sqlite:/var/lib/myapp/app.db --dest /var/backups/myapp --name myapp
15 2 * * * /opt/bkp/bin/bkp backup --source sqlite:/var/lib/myapp/app.db --dest /var/backups/myapp --name myapp >>/var/log/bkp.log 2>&1 # bkp:myapp
```

Add `--install` to write that line into your crontab. Running it again
replaces the old line instead of adding a second one.

## Possible extensions

- Encrypt archives at rest with `age` or `gpg`, and keep the key separate.
- Off-site copies: after a backup, push it to S3 or another host with `rclone`
  or `rsync`, and apply the same rotation remotely.
- Incremental directory backups with `tar --listed-incremental`, or
  content-addressed deduplication.
- Generate a `systemd` timer as an alternative to cron, with `Persistent=true`
  so missed runs catch up.
- Restore drills: on a schedule, restore the latest archive to a scratch
  location and run a health check, so you know your backups really work.
