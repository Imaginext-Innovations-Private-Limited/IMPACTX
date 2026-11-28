#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then python3 -m venv .venv; fi
if [[ ! -f .venv/setup-mysql-v2.ok ]]; then
 .venv/bin/python -m pip install -r requirements-core.txt
 .venv/bin/python -m pip install "chromadb>=1,<2" || echo "Chroma unavailable. Using the local MySQL fallback. See SETUP.md."
 touch .venv/setup-mysql-v2.ok
fi
exec .venv/bin/python run.py "$@"
