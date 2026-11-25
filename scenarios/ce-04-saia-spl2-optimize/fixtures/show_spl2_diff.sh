#!/usr/bin/env bash
set -euo pipefail

clear
if icdiff --cols=110 --whole-file --line-numbers \
    --label='Before SAIA' --label='After SAIA' \
    login_failure_rate.spl2 optimized_login_failure_rate.spl2; then
  status=0
else
  status=$?
fi
# icdiff returns 1 for an ordinary difference, not just for errors.
if (( status > 1 )); then
  printf 'icdiff failed (exit %s)\n' "$status" >&2
  exit "$status"
fi
printf '\nSPL2 comparison complete\n'
