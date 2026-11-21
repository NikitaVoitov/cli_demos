#!/usr/bin/env python3
"""Run a command with splunkctl pointed at a stack profile instead of ~/.splunkctl/config.yaml.

    python3 scripts/with_stack.py mdl splunkctl --insecure index list
    python3 scripts/with_stack.py mdl python3 scripts/seed_phishing.py --check

The profile comes from `python3 scripts/stack_profile.py init <name>`. splunkctl reads SPLUNKCTL_HOST and
SPLUNKCTL_TOKEN before its config file, so ~/.splunkctl stays on the default stack. Values are never printed.
"""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    name, command = sys.argv[1], sys.argv[2:]
    config = ROOT / ".captures/ce01/stacks" / name / "splunkctl.yaml"
    if not config.exists():
        sys.exit(f"no profile {name}; run: python3 scripts/stack_profile.py init {name}")
    values = dict(re.findall(r"^(host|token):\s*(\S+)", config.read_text(), re.M))
    os.environ.update(SPLUNKCTL_HOST=values["host"], SPLUNKCTL_TOKEN=values["token"])
    os.execvp(command[0], command)


if __name__ == "__main__":
    sys.exit(main())
