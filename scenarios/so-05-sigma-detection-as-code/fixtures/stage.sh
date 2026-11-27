#!/bin/bash
# SO-05 stage: put the team repo and the T1003.001 attack data in the emptied workspace (~/payments).
# Clones as the capture home, so git uses its .gitconfig and the demo repo's token (scripts/ce01_capture.py github).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
HOME_DIR=/Users/Shared/splunk-demo
WORKSPACE="$HOME_DIR/payments"
REPO="$(sed -n 's/^DAC_DEMO_REPO=//p' "$ROOT/.env" | tr -d "\"'")"
DATA="$ROOT/.captures/cache/attack_data_T1003.001_windows-sysmon.log"

[ -n "$REPO" ] || { echo "DAC_DEMO_REPO missing from .env" >&2; exit 1; }
[ -f "$DATA" ] || { echo "attack data not cached; run python3 scripts/seed_endpoint.py --dry-run" >&2; exit 1; }

HOME="$HOME_DIR" git clone -q "https://github.com/$REPO.git" "$WORKSPACE/acme-detections"
mkdir -p "$WORKSPACE/attack_data"
cp "$DATA" "$WORKSPACE/attack_data/T1003.001-windows-sysmon.log"
echo "staged acme-detections ($(git -C "$WORKSPACE/acme-detections" log --oneline -1 | cut -c1-60)) and the attack data"
