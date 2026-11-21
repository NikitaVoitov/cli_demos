#!/usr/bin/env python3
"""Print the next free SO-08 case ID: PH-1042 on a fresh stack, then one above the highest case in demo_soc.

    python3 scripts/so08_case.py

Each take's containment writes containment:audit records for its case and the index can't be emptied, so a retake
needs a case no earlier take used. pipeline.capture runs this before a take (`recording.vars`).
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIRST = 1042
SPL = ('search index=demo_soc sourcetype=containment:audit case_id=PH-* | rex field=case_id "^PH-(?<n>\\d+)$" '
       '| stats max(n) AS n')

out = subprocess.run([sys.executable, str(ROOT / "scripts/with_stack.py"), "mdl", "splunkctl", "--yes", "-o", "json",
                      "search", SPL], capture_output=True, text=True, check=True).stdout
rows = json.loads(out or "[]")
highest = int(float(rows[0]["n"])) if rows and rows[0].get("n") not in (None, "") else FIRST - 1
print(f"PH-{max(highest + 1, FIRST)}")
