#!/usr/bin/env bash
# Prepares the capture home so `python3 agent.py` can run a splunklib.ai agent, the state EB-03 starts from.
# Safe to rerun. Secrets are copied with 0600 permissions and never printed.
#
# Two facts about SDK 3.0.1 shape this setup (both are disclosed in how-it-works.md):
#  1. splunklib.ai.tools.locate_app() only accepts an SDK installed under $SPLUNK_HOME/etc/apps/<app>/, so the
#     SDK is installed into a throwaway app directory and python3 is wrapped to point SPLUNK_HOME at it.
#  2. The SDK fetches the MCP token with GET /services/mcp_token?username=..., which this stack's MCP Server
#     rejects (HTTP 400: valid resources are key-pair and tokens). sitecustomize.py hands the SDK the stack's
#     existing MCP token instead.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
H=/Users/Shared/splunk-demo
APP="$H/splunk/etc/apps/agent_demo"
LIB="$APP/lib"
PY=/opt/homebrew/bin/python3

mkdir -p "$LIB" "$H/bin" "$H/.config"
if [ ! -f "$LIB/splunklib/ai/agent.py" ]; then
  "$ROOT/.captures/venv/bin/pip" install -q --target "$LIB" "splunk-sdk[google]==3.0.1" >/dev/null
fi

cat > "$LIB/sitecustomize.py" <<'PY'
import logging
import os

# google-genai warns once per process that a tool-calling reply has no text part; it is not an error.
logging.getLogger("google_genai.types").setLevel(logging.ERROR)

if os.environ.get("SPLUNK_MCP_TOKEN"):
    import splunklib.ai.tools as _tools

    _tools._get_mcp_token = lambda username, service: os.environ["SPLUNK_MCP_TOKEN"]
PY

# Real values come from the files the other demos already use.
host=$(sed -nE 's/^host: *//p' ~/.splunkctl/config.yaml | tr -d "\"'")
token=$(sed -nE 's/^token: *//p' ~/.splunkctl/config.yaml | tr -d "\"'")
mcp=$(sed -nE 's/^SPLUNK_MCP_AUTH=//p' ~/.cursor/mcp-secrets/splunk-mcp.env | tr -d "\"'")
mcp=${mcp#Bearer }
project=$(sed -nE 's/^GOOGLE_CLOUD_PROJECT=//p' "$ROOT/.env")
location=$(sed -nE 's/^GOOGLE_CLOUD_LOCATION=//p' "$ROOT/.env")
[ -n "$host" ] && [ -n "$token" ] && [ -n "$mcp" ] && [ -n "$project" ] && [ -n "$location" ]

install -m 600 ~/.config/gcloud/application_default_credentials.json "$H/.config/gcp-adc.json"
umask 077
cat > "$H/.config/eb03.env" <<ENV
SPLUNK_HOST=$host
SPLUNK_TOKEN=$token
SPLUNK_MCP_TOKEN=$mcp
GOOGLE_CLOUD_PROJECT=$project
GOOGLE_CLOUD_LOCATION=$location
GOOGLE_APPLICATION_CREDENTIALS=$H/.config/gcp-adc.json
ENV

cat > "$H/bin/python3" <<WRAP
#!/bin/sh
# Capture-home python3: the Splunk SDK is importable and the stack and model settings are in the environment.
set -a
. "\$HOME/.config/eb03.env"
set +a
SPLUNK_HOME="\$HOME/splunk" PYTHONPATH="\$HOME/splunk/etc/apps/agent_demo/lib" PYTHONWARNINGS=ignore exec $PY "\$@"
WRAP
chmod 755 "$H/bin/python3"
rm -f "$H/payments/agent.py"
echo "fixture ready: python3 in the capture home imports splunklib.ai"
