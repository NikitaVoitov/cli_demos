#!/usr/bin/env bash
# Puts what the notebook hunt starts from into the capture home. Runs after the workspace was emptied, so a stale
# kernel or output from an earlier take cannot leak in. Secrets are copied with 0600 permissions and never printed.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
FX="$ROOT/scenarios/so-03-notebook-spray-hunt/fixtures"
H=/Users/Shared/splunk-demo
WS="$H/payments"

set -a
. "$ROOT/.env"
set +a
tok() { printf %s "$1" | tr -d '"[:space:]'; }
[ -n "${SPLUNK_REST_URL_MDL:-}" ] && [ -n "${SPLUNK_REST_TOKEN_MDL:-}" ] && [ -n "${SPLUNK_SHARE_PROFILE_MDL:-}" ] && [ -n "${SPLUNK_SHARE_TABLE_MDL:-}" ]

umask 077
install -m 600 "$SPLUNK_SHARE_PROFILE_MDL" "$H/.config/lake.share"
cat > "$H/.config/hunt.env" <<ENV
LAKE_MODE=live
LAKE_REST_URL=$(tok "$SPLUNK_REST_URL_MDL")
LAKE_REST_TOKEN=$(tok "$SPLUNK_REST_TOKEN_MDL")
LAKE_RAW_DATASET=demo_auth_raw
LAKE_SHARE_PROFILE=$H/.config/lake.share
LAKE_SHARE_TABLE=$(tok "$SPLUNK_SHARE_TABLE_MDL")
LAKE_VERIFY=0
ENV

umask 022
cp "$FX/lake.py" "$FX/threat_intel.csv" "$FX/privileged_users.csv" "$WS/"
/usr/bin/python3 "$FX/build_notebook.py" "$WS"
echo "staged: hunt.ipynb, lake.py, and two lookup files in the workspace"
