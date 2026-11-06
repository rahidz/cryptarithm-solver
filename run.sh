#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
    uv venv .venv
fi
uv pip install --python .venv/bin/python -r requirements.txt
if [[ ! -d frontend/node_modules ]]; then
    (cd frontend && npm ci)
fi
(cd frontend && npm run build)
exec .venv/bin/python main.py --serve "$@"
