#!/usr/bin/env python3
"""Publish the files a SO-05 take produced, for the transcript (scenario.yaml `artifacts.files`).

    python3 scenarios/so-05-sigma-detection-as-code/fixtures/artifacts.py <pull request number>

Run after the take, before the next reset. From the demo repo at the pull request's merge commit (its head if it
wasn't merged): the new detection, its test cases, and its tuning macro; the SigmaHQ rule it was built from; and the
ES correlation search contentctl builds from it (one savedsearches.conf stanza); and the two GitHub Actions workflows
that tested and deployed it. From the pull request's comments: CI's first and last reports. Writes them to artifacts/ under fixed names so the transcript rules never depend on
the file names the agent chose. Reads DAC_DEMO_REPO and GH_TOKEN_DAC_DEMO from .env.
"""

import base64
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent.parent / "artifacts"
VENV_BIN = Path("/Users/Shared/splunk-demo/dac/bin")


def dotenv(key: str) -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"{key} missing from .env")


REPO = dotenv("DAC_DEMO_REPO")
ENV = {**os.environ, "GH_TOKEN": dotenv("GH_TOKEN_DAC_DEMO"), "GH_PROMPT_DISABLED": "1"}


def gh_json(path: str):
    out = subprocess.run(["gh", "api", "--paginate", path], env=ENV, capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def content(path: str, ref: str) -> str:
    return base64.b64decode(gh_json(f"repos/{REPO}/contents/{path}?ref={ref}")["content"]).decode()


def write(name: str, text: str) -> None:
    (OUT / name).write_text(text.rstrip() + "\n")
    print(f"wrote artifacts/{name}")


def main() -> int:
    number = sys.argv[1]
    pr = gh_json(f"repos/{REPO}/pulls/{number}")
    ref = pr.get("merge_commit_sha") if pr.get("merged") else pr["head"]["sha"]
    files = [f["filename"] for f in gh_json(f"repos/{REPO}/pulls/{number}/files") if f["status"] != "removed"]
    detection = next(f for f in files if f.startswith("detections/") and f.endswith(".yml"))
    tests = next(f for f in files if re.match(r"tests/[^/]+\.yml$", f))
    macro = next((f for f in files if re.match(r"macros/.+_filter\.yml$", f)), None)
    OUT.mkdir(exist_ok=True)

    det_text = content(detection, ref)
    det = yaml.safe_load(det_text)
    write("detection.yml", det_text)
    write("tests.yml", content(tests, ref))
    if macro:
        write("filter-macro.yml", content(macro, ref))
    rule = next(f["path"] for f in gh_json(f"repos/{REPO}/git/trees/{ref}?recursive=1")["tree"]
                if f["path"].startswith("sigma/rules/") and f["path"].endswith(".yml")
                and str(yaml.safe_load(content(f["path"], ref)).get("id")) == str(det["id"]))
    write("sigma-rule.yml", content(rule, ref))
    for workflow in ("validate", "deploy"):
        write(f"workflow-{workflow}.yml", content(f".github/workflows/{workflow}.yml", ref))

    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git", "clone", "-q", f"https://x-access-token:{ENV['GH_TOKEN']}@github.com/{REPO}.git", tmp],
                       check=True, capture_output=True)
        # After a reset the merge commit is no longer on main; GitHub still serves it, or the pull request's head.
        if subprocess.run(["git", "-C", tmp, "fetch", "-q", "origin", ref], capture_output=True).returncode:
            subprocess.run(["git", "-C", tmp, "fetch", "-q", "origin", f"pull/{number}/head"], check=True, capture_output=True)
        subprocess.run(["git", "-C", tmp, "checkout", "-q", "FETCH_HEAD"], check=True, capture_output=True)
        subprocess.run([str(VENV_BIN / "contentctl"), "build"], cwd=tmp, check=True, capture_output=True)
        conf = next(Path(tmp, "dist").glob("*/default/savedsearches.conf")).read_text()
        stanza = re.search(rf"^\[[^\]]* - {re.escape(det['name'])} - Rule\]\n(?:.+\n?)+", conf, re.M)
        write("savedsearches.conf", stanza.group(0))

    reports = [c["body"] for c in gh_json(f"repos/{REPO}/issues/{number}/comments") if "## Detection tests" in c["body"]]
    if reports:
        write("ci-report-1.md", reports[0])
        write("ci-report-2.md", reports[-1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
