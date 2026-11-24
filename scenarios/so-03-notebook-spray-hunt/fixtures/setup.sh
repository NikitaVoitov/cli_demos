#!/usr/bin/env bash
# Pre-flight for the notebook hunt, run before the capture home is rebuilt. It records nothing and changes nothing:
# it refuses to start a take unless the MDL stack profile exists and the stack holds the story.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
PY="$ROOT/.captures/venv/bin/python"

"$PY" "$ROOT/scripts/stack_profile.py" check mdl
# lake.py needs pandas, which the pipeline venv does not carry.
cd "$ROOT" && uv run --quiet --python 3.12 --with pandas --with requests python scripts/seed_auth.py --check
