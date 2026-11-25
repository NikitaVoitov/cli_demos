"""Record a demo from the beats in its scenario.yaml.

  .captures/venv/bin/python -m pipeline.capture scenarios/<id> <take>
  .captures/venv/bin/python -m pipeline.capture scenarios/<id> --plan     # print the driver commands

Beat types, shared by every demo:
  comment   a shell comment typed before the client starts
  run       a shell command, e.g. launching the client (`agent` or `copilot` gets --model when one is set)
  shell     a command typed in the client's shell mode
  prompt    text typed to the client, then a wait until it starts working
  wait      wait until the client's turn ends; `require: gate` checks the cast shows the refusal (recording.gateEvidence,
            or the beat's own `evidence`, which a demo with several gates sets per gate)
  leave     quit the client and stay in the recorded shell, e.g. to show a file with a tool the client's shell mode
            can't render (Copilot CLI's `!` prints color codes as text)
  exit      leave the client and end the recording

Before the beats: fixture setup commands, a fresh Splunk Web login, and the capture home. Optional recording keys:
  skills: [name, ...]         Splunk Agent Skills (splunk/splunk-agent-skills) to load into the client, besides the default
  stackProfile: <name>        capture against another stack (scripts/stack_profile.py builds .captures/ce01/stacks/<name>)
  integrations: [jira]        Jira tools (acli, Atlassian MCP)
  integrations: [notebook]    the gated jpterm and euporie-preview; `notebook.gated` lists the held cell IDs
  fixtures.stage: [commands]  run after the workspace is cleaned and the hints are written, to put files in it
  keep: [file, ...]           workspace files to copy into the take (<take>/workspace/) when it ends, such as an
                              executed notebook; pipeline.post publishes them to artifacts/
After them: the client's session store is copied into the take, which is what the transcript is built from.

The client is `client.name` in scenario.yaml: cursor-cli (Cursor CLI, the default) or copilot-cli (GitHub Copilot CLI).
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import yaml

from .clients import copilot_cli, cursor_cli

ROOT = Path(__file__).resolve().parent.parent
PY = ROOT / ".captures/venv/bin/python"
HINTS = ROOT / "recorder/hints"
CLIENTS = {"cursor-cli": cursor_cli, "copilot-cli": copilot_cli}
LAUNCHERS = ("agent", "copilot")


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


def client_of(scenario: dict) -> str:
    name = scenario.get("client", {}).get("name", "cursor-cli")
    if name not in CLIENTS:
        raise SystemExit(f"client.name {name!r} is not one of {sorted(CLIENTS)}")
    return name


def beat_commands(beat: dict, model: str, adapter=cursor_cli) -> list[dict]:
    mark = [{"mark": beat["mark"]}] if "mark" in beat else []
    if "comment" in beat:
        body = [{"type": f"# {beat['comment']}"}, {"sleep": 0.5}, {"key": "enter"}, {"sleep": 1}]
    elif "run" in beat:
        command = beat["run"]
        if command in LAUNCHERS and model:
            command = f"{command} --model {model}"
        body = [{"type": command}, {"sleep": 0.4}, {"key": "enter"},
                {"wait": beat["waitFor"], "timeout": beat.get("timeout", 90)}]
        body.append({"sleep": 1.5})
    elif "shell" in beat:
        body = [{"type": "!"}, {"sleep": 0.6}, {"type": beat["shell"]}, {"sleep": 0.5}, {"key": "enter"},
                {"wait": beat["waitFor"], "timeout": beat.get("timeout", 40)}, {"sleep": 2.5}]
    elif "prompt" in beat:
        body = [{"type": beat["prompt"].strip(), "cadence": [0.02, 0.045]}, {"sleep": 0.8}, {"key": "enter"},
                {"wait": adapter.TURN_STARTED, "timeout": 30}]
    elif "wait" in beat:
        body = [{"absent": adapter.TURN_STARTED, "stable": 4, "timeout": beat.get("timeout", 900)}, {"sleep": 3}]
    elif beat.get("leave"):
        body = [{"key": "ctrl-c"}, {"sleep": 0.8}, {"key": "ctrl-c"}, {"wait": "payments \\$", "timeout": 20},
                {"sleep": 1.5}]
    elif beat.get("exit"):
        body = [{"key": "ctrl-c"}, {"sleep": 0.8}, {"key": "ctrl-c"}, {"wait": "payments \\$", "timeout": 20},
                {"sleep": 1.5}, {"type": "exit"}, {"key": "enter"}, {"sleep": 1.5}]
    else:
        raise SystemExit(f"beat needs one of comment, run, shell, prompt, wait, leave, exit: {beat}")
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


def prepare(recording: dict, home: Path, client: str = "cursor-cli") -> dict[str, str]:
    stop_stray_clients(home)
    # ce01_capture.py builds the capture home for this client.
    os.environ["CAPTURE_CLIENT"] = client
    # Every script below reads CAPTURE_STACK, so a demo on another stack never touches the CO2 stack's secrets.
    if recording.get("stackProfile"):
        os.environ["CAPTURE_STACK"] = recording["stackProfile"]
    else:
        os.environ.pop("CAPTURE_STACK", None)
    # Splunk Agent Skills the recorded client loads, on top of the default one (setup installs them).
    os.environ["CAPTURE_SKILLS"] = ",".join(recording.get("skills", []))
    for command in recording.get("fixtures", {}).get("setup", []):
        subprocess.run(command, shell=True, check=True, cwd=ROOT)
    # Per-take values, such as a case ID no earlier take used: each command prints one value for __NAME__ in hints.
    values = {name: subprocess.run(command, shell=True, check=True, cwd=ROOT, capture_output=True, text=True).stdout.strip()
              for name, command in recording.get("vars", {}).items()}
    for name, value in values.items():
        print(f"{name} = {value}")
    # A demo with no Splunk Web screenshots on an SSO stack opts out; playwright-cli then starts logged out.
    if recording.get("splunkWebLogin", True):
        subprocess.run(["node", str(ROOT / "scripts/splunk_web_login.mjs")], check=True, cwd=ROOT / "apps/hub")
    # setup rewrites the workspace instructions from the base template, so hints are appended after it.
    subprocess.run([sys.executable, str(ROOT / "scripts/ce01_capture.py"), "setup"], check=True, cwd=ROOT)
    for integration in ("jira", "n8n", "outlook", "search-reads"):
        if integration in recording.get("integrations", []):
            subprocess.run([sys.executable, str(ROOT / "scripts/ce01_capture.py"), integration], check=True, cwd=ROOT)
    if "notebook" in recording.get("integrations", []):
        gated = ",".join(recording["notebook"]["gated"])
        subprocess.run([sys.executable, str(ROOT / "scripts/ce01_capture.py"), "notebook", gated], check=True, cwd=ROOT)
    workspace = home / recording["workspace"]
    for path in workspace.iterdir():
        if path.name != "AGENTS.md":
            shutil.rmtree(path) if path.is_dir() else path.unlink()
    for transcripts in (home / ".cursor/projects").glob("*/agent-transcripts"):
        shutil.rmtree(transcripts, ignore_errors=True)
    # Earlier takes' sessions would otherwise match the same prompt.
    shutil.rmtree(home / ".copilot/session-state", ignore_errors=True)
    shutil.rmtree(home / ".cache/playwright-cli", ignore_errors=True)
    if client == "cursor-cli":
        config = json.loads((home / ".cursor/cli-config.json").read_text())
        if config.get("approvalMode") != "unrestricted":
            # The CLI writes its own approval settings back when it exits; an approval prompt would stall the take.
            raise SystemExit("capture home is not in unrestricted approval mode; rerun setup with no client running")
    elif not (home / "bin/copilot").exists():
        raise SystemExit("capture home has no copilot launcher; setup did not run for copilot-cli")
    hints = [HINTS / f"{name}.md" for name in recording.get("hints", [])]
    missing = [str(h) for h in hints if not h.exists()]
    if missing:
        raise SystemExit(f"unknown hints: {missing}")
    if hints:
        sys.path.insert(0, str(ROOT / "scripts"))
        from ce01_capture import web_host
        host = web_host()
        extra = "\n\n".join(h.read_text().strip() for h in hints).replace("__SPLUNK_WEB_HOST__", host)
        if "jira" in recording.get("integrations", []):
            from ce01_capture import jira_site
            extra = extra.replace("__JIRA_SITE__", jira_site()).replace("__JIRA_PROJECT__", recording["jira"]["project"])
        for name, value in values.items():
            extra = extra.replace(f"__{name}__", value)
        with (workspace / "AGENTS.md").open("a") as fh:
            fh.write("\n\n" + extra + "\n")
    # The workspace was emptied above, so files a demo starts from are put in last.
    for command in recording.get("fixtures", {}).get("stage", []):
        subprocess.run(command, shell=True, check=True, cwd=ROOT)
    return values


def record(scenario_dir: Path, take: str) -> None:
    scenario = yaml.safe_load((scenario_dir / "scenario.yaml").read_text())
    recording = scenario["recording"]
    home = Path(recording["home"])
    client = client_of(scenario)
    adapter = CLIENTS[client]
    run = ROOT / ".captures" / scenario["id"] / take
    model = os.environ.get("MODEL", recording.get("model", ""))
    prompt = next(b["prompt"] for b in recording["beats"] if "prompt" in b)

    values = prepare(recording, home, client)
    run.mkdir(parents=True, exist_ok=True)
    if values:
        (run / "vars.json").write_text(json.dumps(values, indent=2) + "\n")
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
            for cmd in beat_commands(beat, model, adapter):
                send(run, cmd)
            evidence = beat.get("evidence", recording.get("gateEvidence", ""))
            if beat.get("require") == "gate" and evidence not in (run / "session.cast").read_text():
                raise SystemExit(f"the client finished its turn without {evidence!r} on screen; review screen.txt")
        print(f"take recorded: {run / 'session.cast'}")
    finally:
        # Keep the client's session store even when a beat failed, so the take can still be inspected.
        try:
            store = adapter.find_store(home, prompt.strip())
            (run / "session").mkdir(exist_ok=True)
            shutil.copy(store, run / "session" / ("events.jsonl" if client == "copilot-cli" else "store.db"))
        except Exception as error:  # noqa: BLE001 - best effort
            print(f"no session store copied: {error}")
        # The gated jpterm's record of each notebook change (recorder/clients/cursor-cli/jpterm.tmpl), for post.
        trace = home / ".cache/jpterm-trace"
        if trace.is_dir():
            shutil.copytree(trace, run / "notebook-trace", dirs_exist_ok=True)
        # Files the agent left in the workspace that the demo publishes, before teardown or the next take clears them.
        for name in recording.get("keep", []):
            src = home / recording["workspace"] / name
            if src.exists():
                (run / "workspace").mkdir(exist_ok=True)
                shutil.copy(src, run / "workspace" / name)
            else:
                print(f"keep: {name} is not in the workspace")
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
    client = client_of(scenario)
    print(f"client: {client}")
    print(f"stack profile: {recording.get('stackProfile', '(shared CO2 stack)')}")
    print(f"setup: {recording.get('fixtures', {}).get('setup', [])}")
    print(f"stage: {recording.get('fixtures', {}).get('stage', [])}")
    print(f"hints: {recording.get('hints', [])}")
    print(f"vars: {recording.get('vars', {})}")
    for beat in recording["beats"]:
        print(f"-- {list(beat)[:2]}")
        for cmd in beat_commands(beat, os.environ.get("MODEL", ""), CLIENTS[client]):
            print("   ", json.dumps(cmd)[:150])


if __name__ == "__main__":
    scenario_dir = (ROOT / sys.argv[1]).resolve()
    if len(sys.argv) == 3 and sys.argv[2] == "--plan":
        plan(scenario_dir)
    elif len(sys.argv) == 3:
        record(scenario_dir, sys.argv[2])
    else:
        raise SystemExit(__doc__)
