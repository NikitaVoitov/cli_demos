#!/usr/bin/env bash
# Puts what the notebook hunt starts from into the capture home. Runs after the workspace was emptied, so a stale
# kernel or output from an earlier take cannot leak in. Secrets are copied with 0600 permissions and never printed.
#   stage.sh                         the notebook reads the lake
#   stage.sh fixture YYYY-MM-DD      the notebook reads the same story built in memory, anchored to the day the stack
#                                    was seeded so it matches the hot index; for when the lake is unavailable
set -euo pipefail
MODE="${1:-live}"
SEED_DAY="${2:-}"
[ "$MODE" = live ] || { [ "$MODE" = fixture ] && [ -n "$SEED_DAY" ]; } || { echo "usage: stage.sh [fixture YYYY-MM-DD]" >&2; exit 2; }
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
LAKE_MODE=$MODE
LAKE_FIXTURE_DAY=$SEED_DAY
LAKE_REST_URL=$(tok "$SPLUNK_REST_URL_MDL")
LAKE_REST_TOKEN=$(tok "$SPLUNK_REST_TOKEN_MDL")
LAKE_RAW_DATASET=demo_auth_raw
LAKE_SHARE_PROFILE=$H/.config/lake.share
LAKE_SHARE_TABLE=$(tok "$SPLUNK_SHARE_TABLE_MDL")
LAKE_VERIFY=0
ENV

umask 022
cp "$FX/lake.py" "$FX/show.py" "$FX/threat_intel.csv" "$FX/privileged_users.csv" "$WS/"
[ "$MODE" = fixture ] && cp "$ROOT/scripts/auth_hunt_data.py" "$WS/"
# The jpterm wrapper's record of each change, for the notebook pane; capture copies it into the take.
rm -rf "$H/.cache/jpterm-trace"
/usr/bin/python3 "$FX/build_notebook.py" "$WS"
echo "staged: hunt.ipynb, lake.py, show.py, and two lookup files in the workspace (lake: $MODE)"
