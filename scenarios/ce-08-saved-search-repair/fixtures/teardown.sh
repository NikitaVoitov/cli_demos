#!/usr/bin/env bash
# Removes what the demo created or repaired so the stack is clean for the next take.
s() { splunkctl --insecure --yes "$@"; }
s saved-search remove demo_checkout_errors_by_region >/dev/null 2>&1
s macro remove demo_checkout_5xx >/dev/null 2>&1
exit 0
