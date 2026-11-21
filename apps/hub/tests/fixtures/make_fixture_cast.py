#!/usr/bin/env python3
"""Write the synthetic cast for the workflow-canvas fixture: a short, labeled run with one approval.

    python3 apps/hub/tests/fixtures/make_fixture_cast.py
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "scenarios/wf-canvas-fixture/artifacts/session.cast"
D, B, A, G, R = "\x1b[2m", "\x1b[1m", "\x1b[33m", "\x1b[32m", "\x1b[0m"
PROMPT = f"{D}fixture{R} $ "

LINES = [
    (0.3, f"{PROMPT}# Test fixture for the workflow canvas, not a real capture"),
    (1.5, f"{PROMPT}Triage the new email in the Phishing reports folder."),
    (3.0, f"{B}●{R} Outlook MCP: 1 report  {D}\"Invoice overdue: action required\"{R}"),
    (6.0, f"{B}●{R} Splunk MCP: | aiagent phishing_triage  {D}(Agent Launchpad){R}"),
    (9.0, f"  {D}└ 14 recipients, 3 clicked the link, no payload ran{R}"),
    (11.0, f"{B}●{R} Recommend: purge the email, block the sender domain."),
    (14.0, f"{B}●{R} n8n-contain --case PH-1042"),
    (15.5, f"  {A}└ CONFIRMATION_REQUIRED{R}"),
    (16.5, f"{B}●{R} Containment needs your approval."),
    (18.0, f"{PROMPT}Approved."),
    (20.0, f"{B}●{R} n8n-contain --case PH-1042 --yes"),
    (26.5, f"  {G}└ contained; analyst notified in Slack{R}"),
    (28.0, f"{PROMPT}Slack says it's done. Check in Splunk that it worked."),
    (30.0, f"{B}●{R} Splunk MCP: | aiagent phishing_triage verify  {D}(Agent Launchpad){R}"),
    (32.0, f"  {D}└ 0 mailboxes still hold the email, 0 clicks since containment{R}"),
    (34.0, f"{B}●{R} Contained and verified."),
    (36.0, f"{PROMPT}"),
]

header = {"version": 2, "width": 88, "height": 28, "timestamp": 1795132800, "title": "Workflow canvas fixture"}
OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w") as f:
    f.write(json.dumps(header) + "\n")
    for t, text in LINES:
        f.write(json.dumps([t, "o", text + "\r\n"]) + "\n")
    f.write(json.dumps([38.0, "o", ""]) + "\n")
print(f"wrote {OUT}")
