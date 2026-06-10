#!/usr/bin/env bash
# Backup/restore Qdrant Docker volume (E6-P2)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/deploy/docker-compose.yml}"
PROJECT="${COMPOSE_PROJECT_NAME:-deploy}"
VOLUME="${QDRANT_VOLUME:-${PROJECT}_qdrant_data}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"

usage() {
  echo "Usage: $0 backup [output.tar.gz]"
  echo "       $0 restore <archive.tar.gz>"
  echo "Env: COMPOSE_PROJECT_NAME (default deploy), QDRANT_VOLUME"
}

detect_volume() {
  if docker volume inspect "$VOLUME" >/dev/null 2>&1; then
    echo "$VOLUME"
    return
  fi
  local found
  found="$(docker volume ls -q | grep -E 'qdrant_data$' | head -1 || true)"
  if [[ -n "$found" ]]; then
    echo "$found"
    return
  fi
  echo "ERROR: Qdrant volume not found (tried $VOLUME)" >&2
  exit 1
}

cmd_backup() {
  local vol out
  vol="$(detect_volume)"
  mkdir -p "$BACKUP_DIR"
  out="${1:-$BACKUP_DIR/qdrant-$(date +%Y%m%d-%H%M%S).tar.gz}"
  echo "Backing up volume $vol -> $out"
  docker run --rm \
    -v "${vol}:/data:ro" \
    -v "$(dirname "$out"):/backup" \
    alpine:3.20 \
    tar czf "/backup/$(basename "$out")" -C /data .
  echo "Backup OK: $out"
}

cmd_restore() {
  local vol archive
  archive="${1:?archive path required}"
  if [[ ! -f "$archive" ]]; then
    echo "Archive not found: $archive" >&2
    exit 1
  fi
  vol="$(detect_volume)"
  echo "Restoring $archive -> volume $vol (destructive)"
  docker run --rm \
    -v "${vol}:/data" \
    -v "$(cd "$(dirname "$archive")" && pwd)/$(basename "$archive"):/backup/archive.tar.gz:ro" \
    alpine:3.20 \
    sh -c "rm -rf /data/* /data/..?* 2>/dev/null || true; tar xzf /backup/archive.tar.gz -C /data"
  echo "Restore OK"
}

case "${1:-}" in
  backup) cmd_backup "${2:-}" ;;
  restore) cmd_restore "${2:-}" ;;
  *) usage; exit 1 ;;
esac
