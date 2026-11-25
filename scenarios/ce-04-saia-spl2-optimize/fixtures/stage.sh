#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cp "$ROOT/scenarios/ce-04-saia-spl2-optimize/fixtures/login_failure_rate.spl2" \
  /Users/Shared/splunk-demo/payments/
cp "$ROOT/.captures/venv/bin/icdiff" /Users/Shared/splunk-demo/bin/icdiff
cp "$ROOT/scenarios/ce-04-saia-spl2-optimize/fixtures/show_spl2_diff.sh" \
  /Users/Shared/splunk-demo/payments/
