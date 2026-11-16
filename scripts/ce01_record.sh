#!/usr/bin/env bash
# Records one approved take of a demo. The beats live in the scenario, not here.
# Usage: scripts/ce01_record.sh <take-name>            records CE-01
#        SCENARIO=scenarios/ce-08-saved-search scripts/ce01_record.sh take-1
# MODEL=claude-opus-5-5-low-fast overrides the CLI default (Auto Balance).
set -euo pipefail
cd "$(dirname "$0")/.."
exec .captures/venv/bin/python -m pipeline.capture "${SCENARIO:-scenarios/ce-01-dashboard}" "${1:?take name}"
