#!/usr/bin/env python3
"""Put the SO-05 demo repo and Enterprise Security back to the take's starting point, and check them.

    python3 scenarios/so-05-sigma-detection-as-code/fixtures/repo.py reset   # before a take (fixtures.setup)
    python3 scenarios/so-05-sigma-detection-as-code/fixtures/repo.py check   # only the checks

reset: closes open pull requests, deletes every branch but main, moves main to the `baseline` tag, and runs the
`deploy` workflow, which makes the ES app match the baseline (it removes detections no longer in the repo). check:
the two baseline ACME detections are on in ES, no comsvcs detection of ours exists, and ESCU's comsvcs rule is off.

Reads DAC_DEMO_REPO and GH_TOKEN_DAC_DEMO from .env; checks ES with splunkctl (the CO2 stack). Prints names only.
"""

import calendar
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASELINE = {"ACME SOC - HackTool Mimikatz Execution - Rule", "ACME SOC - Potential LSASS Process Dump Via Procdump - Rule"}
ESCU = "ESCU - Dump LSASS via comsvcs DLL - Rule"
APP = "DA-ESS-DaC-Demo"


def dotenv(key: str) -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"{key} missing from .env")


REPO = dotenv("DAC_DEMO_REPO")
ENV = {**os.environ, "GH_TOKEN": dotenv("GH_TOKEN_DAC_DEMO"), "GH_PROMPT_DISABLED": "1"}


def gh(*args: str, check: bool = True) -> str:
    out = subprocess.run(["gh", *args], env=ENV, capture_output=True, text=True)
    if check and out.returncode != 0:
        raise SystemExit(f"gh {' '.join(args[:2])}: {out.stderr.strip()[:200]}")
    return out.stdout.strip()


def reset() -> None:
    for number in gh("pr", "list", "-R", REPO, "--state", "open", "--json", "number", "-q", ".[].number").split():
        gh("pr", "close", number, "-R", REPO, "--delete-branch")
        print(f"closed pull request #{number}")
    for branch in gh("api", f"repos/{REPO}/branches", "-q", ".[].name").split():
        if branch != "main":
            gh("api", "-X", "DELETE", f"repos/{REPO}/git/refs/heads/{branch}")
            print(f"deleted branch {branch}")
    base = gh("api", f"repos/{REPO}/git/ref/tags/baseline", "-q", ".object.sha")
    if gh("api", f"repos/{REPO}/git/ref/heads/main", "-q", ".object.sha") != base:
        gh("api", "-X", "PATCH", f"repos/{REPO}/git/refs/heads/main", "-f", f"sha={base}", "-F", "force=true")
        print("main reset to baseline")
    started = time.time()
    gh("workflow", "run", "deploy", "-R", REPO, "--ref", "main")
    run_id = ""
    for _ in range(30):
        time.sleep(5)
        runs = json.loads(gh("run", "list", "-R", REPO, "--workflow", "deploy", "--limit", "5", "--json",
                             "databaseId,event,createdAt"))
        runs = [r for r in runs if r["event"] == "workflow_dispatch"
                and calendar.timegm(time.strptime(r["createdAt"], "%Y-%m-%dT%H:%M:%SZ")) >= started - 60]
        if runs:
            run_id = str(runs[0]["databaseId"])
            break
    if not run_id:
        raise SystemExit("the deploy workflow did not start")
    if subprocess.run(["gh", "run", "watch", run_id, "-R", REPO, "--exit-status"], env=ENV, capture_output=True).returncode:
        raise SystemExit("the deploy workflow failed; see the repo's Actions tab")
    print("deploy workflow finished: ES matches the baseline")


def search(spl: str) -> list[dict]:
    out = subprocess.run(["splunkctl", "--insecure", "--timeout", "120", "--yes", "search", "export", spl, "--output", "json"],
                         capture_output=True, text=True, timeout=180)
    return json.loads(out.stdout or "[]")


def check() -> int:
    rows = search("| rest /servicesNS/-/-/saved/searches splunk_server=local count=0 "
                  f"| search eai:acl.app={APP} OR title=\"{ESCU}\" | table title disabled")
    state = {r["title"]: r["disabled"] for r in rows}
    ours = {t for t in state if t.startswith("ACME SOC - ")}
    problems = [f"{t} is missing or off" for t in BASELINE if state.get(t) != "0"]
    problems += [f"{t} should not exist yet" for t in ours - BASELINE]
    if state.get(ESCU) != "1":
        problems.append(f"{ESCU} should exist and be off")
    for p in problems:
        print(p)
    print("ES baseline ready" if not problems else "ES is not at the baseline")
    return 1 if problems else 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "reset":
        reset()
        sys.exit(check())
    if cmd == "check":
        sys.exit(check())
    sys.exit(__doc__)
