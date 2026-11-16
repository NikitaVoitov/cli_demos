#!/usr/bin/env python3
"""Write a clearly labeled placeholder CE-01 cast, timed to scenario.yaml, until the real capture exists.

    python3 scripts/make_placeholder_cast.py
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "scenarios" / "ce-01-dashboard" / "artifacts" / "session.cast"

# Roles: user input cyan, agent prose default, tool names bold, tool arguments blue, outputs dim, blocked write amber.
G, D, W, A, M, R, B = "\x1b[32m", "\x1b[2m", "\x1b[1;97m", "\x1b[33m", "\x1b[35m", "\x1b[0m", "\x1b[1m"
U, ARG = "\x1b[36m", "\x1b[34m"
PROMPT = f"{M}splunk-demo{R} \x1b[34m~/payments{R} $ "

events: list[tuple[float, str]] = []


def out(t: float, text: str) -> None:
    events.append((round(t, 3), text))


def typed(t: float, text: str, cps: float = 28) -> float:
    for i, ch in enumerate(text):
        out(t + i / cps, ch)
    return t + len(text) / cps


def line(t: float, text: str) -> None:
    out(t, text + "\r\n")


t = 0.3
out(0.0, PROMPT)
t = typed(t, f"# Placeholder recording: replaced by the real Cursor CLI capture")
line(t, "")
out(t + 0.2, PROMPT)
t = typed(t + 0.5, "cursor-agent")
line(t, "")
line(t + 0.6, f"{B}Cursor Agent{R} {D}· splunk-demo/payments{R}")
line(t + 0.7, "")
out(t + 1.0, f"{D}>{R} {U}")
t = typed(t + 1.1, "Build a checkout latency dashboard from the payments data and check that it renders. Ask before deploying.", 90)
line(t, R)
line(t + 0.1, "")

def tool(t: float, name: str, args: str, via: str = "") -> None:
    origin = f" {D}({via}){R}" if via else ""
    line(t, f"{G}●{R} {W}{name}{R}{origin} {ARG}{args}{R}")


def said(t: float, *lines: str) -> None:
    for i, text in enumerate(lines):
        line(t + i * 0.1, ("● " if i == 0 else "  ") + text)


tool(6.2, "splunk_get_sourcetypes", "index=payments", "splunk-mcp")
line(6.9, f"  {D}└ checkout: 184,220 events · latency_ms, status, region{R}")
line(7.0, "")
said(9.4, "checkout has latency and status fields, so I can chart p95 latency and the 5xx rate.",
     "Checking the numbers before building panels.")
line(9.6, "")
tool(11.0, "Shell", "splunkctl --yes search export 'index=payments sourcetype=checkout | timechart p95(latency_ms)'")
line(13.9, f"  {D}└ 24 rows{R}")
line(14.0, "")
tool(16.8, "Shell", "splunkctl --yes search export '… | stats count(eval(status>=500)) AS errors count AS total'")
line(19.2, f"  {D}└ errors 737 · total 184220 · rate 0.4{R}")
line(19.3, "")
tool(22.5, "Write", "checkout_latency.json")
line(23.1, f"  {D}└ Wrote dashboard definition with 4 panels{R}")
line(23.2, "")
tool(27.6, "Shell", "splunkctl dashboard add demo_checkout_latency --file checkout_latency.json --app search")
line(28.4, f"  {A}└ {{\"error\":\"write operation for \\\"splunkctl dashboard add\\\" requires confirmation;{R}")
line(28.4, f"    {A}rerun with --yes after user approval\",\"code\":\"CONFIRMATION_REQUIRED\"}}{R}")
line(28.5, "")
said(30.1, "The dashboard is ready. Deploy demo_checkout_latency to the search app?")
line(30.2, "")
out(30.4, f"{D}>{R} {U}")
t = typed(33.6, "Approved. Deploy it once.", 18)
line(t + 0.2, R)
line(t + 0.3, "")
tool(36.8, "Shell", "splunkctl --yes dashboard add demo_checkout_latency --file checkout_latency.json --app search")
line(38.0, f"  {D}└ created{R}")
line(38.1, "")
tool(44.0, "browser_navigate", "…/app/search/demo_checkout_latency", "playwright")
line(46.4, f"  {D}└ Page loaded{R}")
line(46.5, "")
tool(49.2, "browser_take_screenshot", "", "playwright")
line(50.6, f"  {D}└ 4 panels visible{R}")
line(50.7, "")
said(53.0, "Dashboard renders: 4 panels, no errors.")
line(53.1, "")
out(55.0, f"{D}>{R} ")
out(58.4, "")

header = {
    "version": 2,
    "width": 88,
    "height": 28,
    "timestamp": 1794830400,
    "env": {"SHELL": "/bin/zsh", "TERM": "xterm-256color"},
    "title": "CE-01 placeholder",
}
OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w") as f:
    f.write(json.dumps(header) + "\n")
    for ts, text in sorted(events, key=lambda e: e[0]):
        f.write(json.dumps([ts, "o", text]) + "\n")
print(f"wrote {OUT} ({len(events)} events, {events[-1][0]} s)")
