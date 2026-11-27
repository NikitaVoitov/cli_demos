#!/usr/bin/env python3
"""Check that every detection built from a Sigma rule still matches it.

    python ci/check_sigma.py

For each detection whose `id` is a rule in sigma/rules, convert the rule with sigma-cli (Splunk backend, CIM data
model) and require its `where` clause, unchanged, in the detection's search. Detections with no Sigma rule are
listed as native SPL. Exits 1 on drift or on a rule sigma-cli can't convert.
"""

import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def norm(s: str) -> str:
    return " ".join(s.split())


def main() -> int:
    rules = {}
    for path in sorted((ROOT / "sigma/rules").rglob("*.yml")):
        rules[str(yaml.safe_load(path.read_text())["id"])] = path

    failures, rows = 0, []
    for path in sorted((ROOT / "detections").rglob("*.yml")):
        det = yaml.safe_load(path.read_text())
        rule = rules.get(str(det["id"]))
        if rule is None:
            rows.append((det["name"], "native SPL", "-"))
            continue
        out = subprocess.run(["sigma", "convert", "-t", "splunk", "-p", "splunk_cim", "-f", "data_model", str(rule)],
                             capture_output=True, text=True)
        match = re.search(r" where (.*) by Processes\.", out.stdout)
        if out.returncode != 0 or not match:
            rows.append((det["name"], "FAIL: sigma-cli could not convert", rule.name))
            failures += 1
        elif norm(match.group(1)) in norm(det["search"]):
            rows.append((det["name"], "ok", rule.name))
        else:
            rows.append((det["name"], "FAIL: search no longer matches the Sigma rule", rule.name))
            failures += 1

    width = max(len(r[0]) for r in rows)
    for name, status, rule in rows:
        print(f"{name:<{width}}  {status}  ({rule})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
