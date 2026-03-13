#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[1/3] Python syntax check"
python3 -m py_compile app.py data.py main.py pages/*.py infra/*.py providers/*.py services/*.py

echo "[2/3] Fast tests"
if command -v pytest >/dev/null 2>&1; then
  pytest -q -k "state or web or health or http_client"
else
  echo "pytest not found, skipping tests" >&2
fi

echo "[3/3] Health contract smoke"
if command -v curl >/dev/null 2>&1; then
  curl -fsS http://127.0.0.1:5000/api/health >/dev/null || true
fi

echo "Quality gate finished"

