#!/usr/bin/env python3
"""Check that this machine is ready to author demos in this repo. Prints what is missing and how to fix it.

  python3 scripts/doctor.py            # works on the system Python 3.9+; changes nothing
  python3 scripts/doctor.py --capture  # also require what recording a take needs (macOS)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = Path.home()
# The directories the capture itself searches (scripts/ce01_capture.py TOOL_PATH).
SEARCH = [str(HOME / ".local/bin"), "/opt/homebrew/bin", "/usr/local/bin"]
problems: list[str] = []


def report(ok: bool, label: str, fix: str, required: bool = True) -> None:
    print(f"  {'ok      ' if ok else ('MISSING ' if required else 'optional')} {label}" + ("" if ok else f"\n           -> {fix}"))
    if not ok and required:
        problems.append(label)


def tool(name: str, fix: str, required: bool = True) -> None:
    found = shutil.which(name, path=":".join([*SEARCH, os.environ.get("PATH", "")]))
    report(found is not None, name, fix, required)


def main() -> int:
    capture = "--capture" in sys.argv
    print("Authoring, narration and the hub")
    tool("uv", "brew install uv")
    tool("node", "brew install node   (22 or newer)")
    venv_python = ROOT / ".captures/venv/bin/python"
    modern = False
    if venv_python.exists():
        out = subprocess.run([str(venv_python), "-c", "import sys;print(sys.version_info[:2] >= (3, 12))"],
                             capture_output=True, text=True).stdout.strip()
        modern = out == "True"
    report(modern, ".captures/venv (Python 3.12+)",
           "uv venv --python 3.12 .captures/venv && uv pip install --python .captures/venv/bin/python -r pipeline/requirements.txt")
    report((ROOT / "apps/hub/node_modules").is_dir(), "apps/hub/node_modules", "cd apps/hub && npm ci")
    tool("ffmpeg", "brew install ffmpeg   (provides ffprobe too)")
    tool("elevenlabs", "brew install elevenlabs/tap/elevenlabs, then: elevenlabs auth login")
    tool("gitleaks", "brew install gitleaks")
    report((ROOT / ".agents/skills/demo-author/SKILL.md").exists(), "demo-author skill",
           "git checkout -- .agents/skills/demo-author")
    report((ROOT / ".env").exists(), ".env", "cp .env.example .env, then fill in what your demo needs", capture)

    print("Recording a take (macOS, needs a Splunk stack)" + ("" if capture else "; optional, rerun with --capture"))
    tool("asciinema", "brew install asciinema   (3.x)", capture)
    tool("agent", "curl https://cursor.com/install -fsS | bash, then: agent login   (Cursor CLI)", capture)
    tool("copilot", "brew install --cask copilot-cli   (only for client.name: copilot-cli demos, e.g. SO-03)", False)
    tool("splunkctl", "download a release from https://github.com/splunk/splunkctl/releases into /usr/local/bin", capture)
    tool("playwright-cli", "npm install -g @playwright/cli@latest", capture)
    report((HOME / ".agents/skills/playwright-cli/SKILL.md").exists(), "playwright-cli skill",
           "playwright-cli install --skills agents --global", capture)
    report((HOME / ".splunkctl/config.yaml").exists() or (ROOT / ".captures/ce01/stacks").is_dir(), "a Splunk stack config",
           "splunkctl config set host/token, or build a stack profile (README: Stacks)", capture)
    tool("zellij", "brew install zellij   (only to watch a take)", False)
    tool("docker", "install Docker Desktop   (only for n8n demos: scripts/n8n_preview_snapshot.py)", False)

    print("\nAll set." if not problems else f"\n{len(problems)} to fix: " + ", ".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
