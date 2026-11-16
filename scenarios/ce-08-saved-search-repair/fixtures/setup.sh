#!/usr/bin/env bash
# Leaves the stack with a saved search whose macro has been deleted, the state CE-08 starts from.
# Safe to rerun: it removes both objects first.
set -uo pipefail
s() { splunkctl --insecure --yes "$@"; }

s saved-search remove demo_checkout_errors_by_region >/dev/null 2>&1
s macro remove demo_checkout_5xx >/dev/null 2>&1

set -e
s macro add demo_checkout_5xx --definition 'index=demo_checkout sourcetype=checkout status>=500' >/dev/null
s saved-search add demo_checkout_errors_by_region \
  --search '`demo_checkout_5xx` | stats count AS errors BY region | sort - errors' \
  --param description='Checkout 5xx responses by region' \
  --param dispatch.earliest_time=-24h \
  --param dispatch.latest_time=now >/dev/null
# A teammate cleaned up unused macros and took this one with it.
s macro remove demo_checkout_5xx >/dev/null
echo "fixture ready: demo_checkout_errors_by_region now points at a missing macro"
