#!/usr/bin/env bash
# Stops the notebook kernel the take left behind and removes the lake credentials from the capture home.
H=/Users/Shared/splunk-demo
pkill -f "ipykernel_launcher.*$H/Library/Jupyter" || true
rm -f "$H/.config/hunt.env" "$H/.config/lake.share"
exit 0
