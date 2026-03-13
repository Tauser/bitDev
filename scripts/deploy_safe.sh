#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <target-dir>" >&2
  echo "Example: $0 /home/tauser/bitdev" >&2
  exit 2
fi

TARGET_DIR="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_ROOT="$TARGET_DIR/backups"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$BACKUP_ROOT/deploy_$STAMP"

FILES=(
  app.py data.py main.py layout.py utils.py
  pages/dashboard.py pages/galeria.py pages/relogio.py pages/bolsa.py pages/agenda.py pages/clima.py pages/impressora.py pages/macro.py
  infra/http_client.py infra/logging_config.py
  services/config_service.py
)

mkdir -p "$BACKUP_DIR"

echo "Creating backup in $BACKUP_DIR"
for f in "${FILES[@]}"; do
  if [[ -f "$TARGET_DIR/$f" ]]; then
    mkdir -p "$BACKUP_DIR/$(dirname "$f")"
    cp -f "$TARGET_DIR/$f" "$BACKUP_DIR/$f"
  fi
done

rollback() {
  echo "Deployment failed. Rolling back..."
  for f in "${FILES[@]}"; do
    if [[ -f "$BACKUP_DIR/$f" ]]; then
      mkdir -p "$TARGET_DIR/$(dirname "$f")"
      cp -f "$BACKUP_DIR/$f" "$TARGET_DIR/$f"
    fi
  done
  sudo systemctl restart crypto.service || true
}

trap rollback ERR

echo "Copying new files"
for f in "${FILES[@]}"; do
  if [[ -f "$ROOT_DIR/$f" ]]; then
    mkdir -p "$TARGET_DIR/$(dirname "$f")"
    cp -f "$ROOT_DIR/$f" "$TARGET_DIR/$f"
  fi
done

echo "Restarting service"
sudo systemctl restart crypto.service
sleep 4

if ! curl -fsS http://127.0.0.1:5000/api/health >/dev/null; then
  echo "Health check failed" >&2
  exit 1
fi

if ! curl -fsS http://127.0.0.1:5000/api/ready >/dev/null; then
  echo "Readiness check failed" >&2
  exit 1
fi

trap - ERR
echo "Deploy successful"
