"""Record a demo from the beats in its scenario.yaml.

  .captures/venv/bin/python -m pipeline.capture scenarios/<id> <take>
  .captures/venv/bin/python -m pipeline.capture scenarios/<id> --plan     # print the driver commands

Beat types, shared by every demo:
  comment   a shell comment typed before the client starts
  run       a shell command, e.g. launching the client (`agent` gets --model when one is set)
  shell     a command typed in the client's shell mode
  prompt    text typed to the client, then a wait until it starts working
  wait      wait until the client's turn ends; `require: gate` checks the cast shows the refusal
  exit      leave the client and end the recording

Before the beats: fixture setup commands, a fresh Splunk Web login, and the capture home.
After them: the client's session store is copied into the take, which is what the transcript is built from.
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import yaml

from .clients import cursor_cli

ROOT = Path(__file__).resolve().parent.parent
PY = ROOT / ".captures/venv/bin/python"
HINTS = ROOT / "recorder/hints"
TURN_STARTED = "ctrl\\+c to stop"


def send(run: Path, cmd: dict) -> dict:
    conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    conn.connect(str(run / "ctl.sock"))
    conn.sendall((json.dumps(cmd) + "\n").encode())
    res = json.loads(conn.makefile().readline())
    conn.close()
    shown = {k: v for k, v in res.items() if k != "screen"}
    print(json.dumps(shown), flush=True)
    if not res.get("ok"):
        raise SystemExit(f"driver rejected {cmd}: {shown}")
    return res


def beat_commands(beat: dict, model: str) -> list[dict]:
    mark = [{"mark": beat["mark"]}] if "mark" in beat else []
    if "comment" in beat:
        body = [{"type": f"# {beat['comment']}"}, {"sleep": 0.5}, {"key": "enter"}, {"sleep": 1}]
    elif "run" in beat:
        command = beat["run"]
        if command == "agent" and model:
            command = f"agent --model {model}"
        body = [{"type": command}, {"sleep": 0.4}, {"key": "enter"},
                {"wait": beat["waitFor"], "timeout": beat.get("timeout", 90)}]
        body.append({"sleep": 1.5})
    elif "shell" in beat:
        body = [{"type": "!"}, {"sleep": 0.6}, {"type": beat["shell"]}, {"sleep": 0.5}, {"key": "enter"},
                {"wait": beat["waitFor"], "timeout": beat.get("timeout", 40)}, {"sleep": 2.5}]
    elif "prompt" in beat:
        body = [{"type": beat["prompt"].strip(), "cadence": [0.02, 0.045]}, {"sleep": 0.8}, {"key": "enter"},
                {"wait": TURN_STARTED, "timeout": 30}]
    elif "wait" in beat:
        body = [{"absent": TURN_STARTED, "stable": 4, "timeout": beat.get("timeout", 900)}, {"sleep": 3}]
    elif beat.get("exit"):
        body = [{"key": "ctrl-c"}, {"sleep": 0.8}, {"key": "ctrl-c"}, {"wait": "payments \\$", "timeout": 20},
                {"sleep": 1.5}, {"type": "exit"}, {"key": "enter"}, {"sleep": 1.5}]
    else:
        raise SystemExit(f"beat needs one of comment, run, shell, prompt, wait, exit: {beat}")
    # A wait is marked when it ends, so the anchor sits where the client handed control back.
    return body + mark if "wait" in beat else mark + body


def stop_stray_clients(home: Path) -> None:
    """A client left over from an earlier take rewrites its config when it exits, which would undo setup."""
    out = subprocess.run(["lsof", "-d", "cwd", "-Fpn"], capture_output=True, text=True).stdout
    pid = None
    for line in out.splitlines():
        if line.startswith("p"):
            pid = int(line[1:])
        elif line.startswith("n") and line[1:].startswith(str(home)) and pid and pid != os.getpid():
            subprocess.run(["kill", "-HUP", str(pid)], check=False)
    time.sleep(3)


def prepare(recording: dict, home: Path) -> None:
    stop_stray_clients(home)
    for command in recording.get("fixtures", {}).get("setup", []):
        subprocess.run(command, shell=True, check=True, cwd=ROOT)
    subprocess.run(["node", str(ROOT / "scripts/splunk_web_login.mjs")], check=True, cwd=ROOT / "apps/hub")
    # setup rewrites the workspace instructions from the base template, so hints are appended after it.
    subprocess.run([sys.executable, str(ROOT / "scripts/ce01_capture.py"), "setup"], check=True, cwd=ROOT)
    workspace = home / recording["workspace"]
    for path in workspace.iterdir():
        if path.name != "AGENTS.md":
            shutil.rmtree(path) if path.is_dir() else path.unlink()
    for transcripts in (home / ".cursor/projects").glob("*/agent-transcripts"):
        shutil.rmtree(transcripts, ignore_errors=True)
    shutil.rmtree(home / ".cache/playwright-cli", ignore_errors=True)
    config = json.loads((home / ".cursor/cli-config.json").read_text())
    if config.get("approvalMode") != "unrestricted":
        # The CLI writes its own approval settings back when it exits; an approval prompt would stall the take.
        raise SystemExit("capture home is not in unrestricted approval mode; rerun setup with no client running")
    hints = [HINTS / f"{name}.md" for name in recording.get("hints", [])]
    missing = [str(h) for h in hints if not h.exists()]
    if missing:
        raise SystemExit(f"unknown hints: {missing}")
    if hints:
        host = urlparse((ROOT / ".captures/ce01/secrets/web_base").read_text().strip()).netloc
        extra = "\n\n".join(h.read_text().strip() for h in hints).replace("__SPLUNK_WEB_HOST__", host)
        with (workspace / "AGENTS.md").open("a") as fh:
            fh.write("\n\n" + extra + "\n")


def record(scenario_dir: Path, take: str) -> None:
    scenario = yaml.safe_load((scenario_dir / "scenario.yaml").read_text())
    recording = scenario["recording"]
    home = Path(recording["home"])
    run = ROOT / ".captures" / scenario["id"] / take
    model = os.environ.get("MODEL", recording.get("model", ""))
    prompt = next(b["prompt"] for b in recording["beats"] if "prompt" in b)

    prepare(recording, home)
    run.mkdir(parents=True, exist_ok=True)
    size = scenario.get("terminal", {"cols": 88, "rows": 28})
    env = {**os.environ, "DEMO_TERMINAL": f"{size['cols']}x{size['rows']}"}
    driver = subprocess.Popen([str(PY), str(ROOT / "scripts/ce01_drive.py"), "serve", str(run)], cwd=ROOT, env=env)
    try:
        for _ in range(50):
            if (run / "ctl.sock").exists():
                break
            time.sleep(0.2)
        else:
            raise SystemExit("driver did not start")
        send(run, {"wait": "payments \\$", "timeout": 20})
        send(run, {"sleep": 1.2})
        for beat in recording["beats"]:
            for cmd in beat_commands(beat, model):
                send(run, cmd)
            if beat.get("require") == "gate" and recording["gateEvidence"] not in (run / "session.cast").read_text():
                raise SystemExit("the client finished its turn without splunkctl refusing the write; review screen.txt")
        print(f"take recorded: {run / 'session.cast'}")
    finally:
        # Keep the client's session store even when a beat failed, so the take can still be inspected.
        try:
            store = cursor_cli.find_store(home, prompt.strip())
            (run / "session").mkdir(exist_ok=True)
            shutil.copy(store, run / "session/store.db")
        except Exception as error:  # noqa: BLE001 - best effort
            print(f"no session store copied: {error}")
        send_quit = (run / "ctl.sock").exists()
        if send_quit:
            try:
                send(run, {"quit": True})
            except OSError:
                pass
        subprocess.run(["pkill", "-HUP", "-f", str(run / "session.cast")], check=False)
        try:
            driver.wait(timeout=10)
        except subprocess.TimeoutExpired:
            driver.kill()
        for command in recording.get("fixtures", {}).get("teardown", []):
            subprocess.run(command, shell=True, check=False, cwd=ROOT)


def plan(scenario_dir: Path) -> None:
    scenario = yaml.safe_load((scenario_dir / "scenario.yaml").read_text())
    recording = scenario["recording"]
    print(f"setup: {recording.get('fixtures', {}).get('setup', [])}")
    print(f"hints: {recording.get('hints', [])}")
    for beat in recording["beats"]:
        print(f"-- {list(beat)[:2]}")
        for cmd in beat_commands(beat, os.environ.get("MODEL", "")):
            print("   ", json.dumps(cmd)[:150])


if __name__ == "__main__":
    scenario_dir = (ROOT / sys.argv[1]).resolve()
    if len(sys.argv) == 3 and sys.argv[2] == "--plan":
        plan(scenario_dir)
    elif len(sys.argv) == 3:
        record(scenario_dir, sys.argv[2])
    else:
        raise SystemExit(__doc__)
