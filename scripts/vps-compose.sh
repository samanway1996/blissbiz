#!/bin/sh
set -eu
project_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
exec docker compose --project-name blissbiz-vps \
  --env-file "$project_root/deploy/vps.env" \
  -f "$project_root/deploy/compose.vps.yaml" "$@"
