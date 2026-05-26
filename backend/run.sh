#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-8080}"

if [[ ! -f .venv/bin/python ]]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

.venv/bin/python -m pip install -r requirements.txt

echo "Starting SkillProof API at http://127.0.0.1:${PORT}"
echo "Docs: http://127.0.0.1:${PORT}/docs"
exec .venv/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port "${PORT}"
