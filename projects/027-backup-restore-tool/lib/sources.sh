# shellcheck shell=bash
# sources.sh - how each kind of source is dumped and restored.
#
# A source spec is "KIND:TARGET":
#   dir:/srv/www         a directory tree      -> NAME--TS.dir.tar.gz
#   sqlite:/var/app.db   a SQLite database     -> NAME--TS.sqlite.gz
#   postgres:appdb       a PostgreSQL database -> NAME--TS.pg.dump
#
# The kind is encoded in the archive's file extension, so `restore` knows how
# to undo an archive without any extra metadata file.

# kind_ext KIND - archive extension for a source kind.
kind_ext() {
  case $1 in
    dir) echo 'dir.tar.gz' ;;
    sqlite) echo 'sqlite.gz' ;;
    postgres) echo 'pg.dump' ;;
    *) return 1 ;;
  esac
}

# archive_kind NAME - inverse of kind_ext, based on the filename suffix.
archive_kind() {
  case $1 in
    *.dir.tar.gz) echo dir ;;
    *.sqlite.gz) echo sqlite ;;
    *.pg.dump) echo postgres ;;
    *) return 1 ;;
  esac
}

# parse_source SPEC - sets SRC_KIND and SRC_TARGET, validating both.
parse_source() {
  local spec=$1
  [[ $spec == *:* ]] || die "source must look like KIND:TARGET (got '$spec')" "$EX_USAGE"
  SRC_KIND=${spec%%:*}
  SRC_TARGET=${spec#*:}
  [[ -n $SRC_TARGET ]] || die "empty source target in '$spec'" "$EX_USAGE"
  kind_ext "$SRC_KIND" >/dev/null || die "unknown source kind '$SRC_KIND' (dir, sqlite, postgres)" "$EX_USAGE"
  case $SRC_KIND in
    dir) [[ -d $SRC_TARGET ]] || die "source directory not found: $SRC_TARGET" ;;
    sqlite) [[ -f $SRC_TARGET ]] || die "sqlite database not found: $SRC_TARGET" ;;
    postgres) : ;; # existence is checked by pg_dump itself
  esac
}

# dump_source KIND TARGET OUTFILE - write a backup of TARGET to OUTFILE.
dump_source() {
  local kind=$1 target=$2 out=$3
  case $kind in
    dir)
      require_cmd tar gzip
      # -C makes paths relative to the source root, so a restore can go
      # anywhere. --numeric-owner avoids depending on local user names.
      tar -C "$target" --numeric-owner -czf "$out" .
      ;;
    sqlite)
      require_cmd sqlite3 gzip
      # Copying a live .db file with cp can capture a torn write. The
      # `.backup` command uses SQLite's online-backup API and produces a
      # consistent snapshot even while other processes are writing.
      [[ $out != *"'"* ]] || die "output path may not contain a single quote"
      local snap="$out.snapshot"
      sqlite3 "$target" ".backup '$snap'"
      gzip -c "$snap" >"$out"
      rm -f "$snap"
      ;;
    postgres)
      require_cmd pg_dump
      # Custom format (-Fc) is compressed and lets pg_restore pick objects.
      pg_dump -Fc --no-owner -f "$out" "$target"
      ;;
  esac
}

# check_tar_safe ARCHIVE - refuse archives with absolute or "../" member
# paths. A tampered archive could otherwise write outside the restore
# directory ("tar slip"). GNU tar has its own guards; this is defence in depth
# and also protects users of other tar implementations.
check_tar_safe() {
  local member
  while IFS= read -r member; do
    case $member in
      /* | .. | ../* | */../* | */..)
        die "unsafe path in archive: '$member'" ;;
    esac
  done < <(tar -tzf "$1")
}

# restore_archive KIND ARCHIVE TARGET FORCE
restore_archive() {
  local kind=$1 archive=$2 target=$3 force=$4
  case $kind in
    dir)
      require_cmd tar
      if [[ -e $target && ! -d $target ]]; then
        die "restore target exists and is not a directory: $target"
      fi
      if [[ -d $target && -n $(ls -A "$target") && $force != 1 ]]; then
        die "restore target is not empty: $target (use --force to overwrite)"
      fi
      check_tar_safe "$archive"
      mkdir -p "$target"
      tar -C "$target" --no-same-owner -xzf "$archive"
      ;;
    sqlite)
      require_cmd gzip
      if [[ -e $target && $force != 1 ]]; then
        die "restore target exists: $target (use --force to overwrite)"
      fi
      # Decompress next to the target, check it, then rename into place so a
      # failed restore never leaves a half-written database behind.
      local tmp="$target.restoring.$$"
      gzip -dc "$archive" >"$tmp"
      if command -v sqlite3 >/dev/null 2>&1; then
        local result
        result=$(sqlite3 "$tmp" 'PRAGMA integrity_check;' 2>&1) || true
        if [[ $result != ok ]]; then
          rm -f "$tmp"
          die "restored database failed integrity_check: $result"
        fi
      fi
      mv -f "$tmp" "$target"
      ;;
    postgres)
      require_cmd pg_restore
      local -a args=(--no-owner -d "$target")
      [[ $force == 1 ]] && args+=(--clean --if-exists)
      pg_restore "${args[@]}" "$archive"
      ;;
  esac
}
