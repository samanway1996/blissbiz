#!/bin/sh
# Back up a Compose MySQL service plus a local upload root while application writes are paused.
set -eu
umask 077
if [ "$#" -ne 3 ] || [ "$1" != "--writes-paused" ]; then
  echo "Usage: scripts/backup.sh --writes-paused /absolute/uploads /absolute/new-backup-directory" >&2
  exit 2
fi
upload_root=$2
backup_dir=$3
case "$upload_root:$backup_dir" in /*:/*) ;; *) echo "Use absolute paths." >&2; exit 2 ;; esac
if [ ! -d "$upload_root" ] || [ -e "$backup_dir" ]; then
  echo "Upload root must exist; backup destination must be new." >&2
  exit 2
fi
python3 - "$upload_root" "$backup_dir" <<'PY'
import pathlib
import sys
uploads, backup = (pathlib.Path(value).resolve() for value in sys.argv[1:])
if backup == uploads or uploads in backup.parents:
    raise SystemExit('Backup destination must be outside the upload root.')
PY
mkdir -m 700 "$backup_dir"
docker compose exec -T db sh -c 'MYSQL_PWD="$MYSQL_PASSWORD" mysqldump --single-transaction --no-tablespaces --set-gtid-purged=OFF -u"$MYSQL_USER" "$MYSQL_DATABASE"' > "$backup_dir/database.sql"
tar -czf "$backup_dir/uploads.tar.gz" -C "$upload_root" .
python3 - "$backup_dir" <<'PY'
import hashlib
import pathlib
import sys
root = pathlib.Path(sys.argv[1])
with (root / 'SHA256SUMS').open('w') as output:
    for name in ('database.sql', 'uploads.tar.gz'):
        with (root / name).open('rb') as stream:
            checksum = hashlib.sha256()
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                checksum.update(block)
            digest = checksum.hexdigest()
        output.write(f'{digest}  {name}\n')
PY
echo "Backup completed. Copy the private directory off this VM and verify a restore."
