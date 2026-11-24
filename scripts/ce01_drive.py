#!/usr/bin/env python3
"""Session driver for CE-01 captures (a small stand-in for §5.1).

Runs `asciinema rec` inside a PTY it owns, mirrors the screen with pyte, and takes
commands over a Unix socket so a capture can be driven step by step:

  .captures/venv/bin/python scripts/ce01_drive.py serve <run-dir>
  .captures/venv/bin/python scripts/ce01_drive.py send <run-dir> '{"type": "# hello"}' '{"key": "enter"}'

Commands (one JSON object each):
  {"type": "text", "cadence": [0.025, 0.06]}   type characters with human-like delays
  {"key": "enter" | "esc" | "tab" | "ctrl-c" | "ctrl-d" | "ctrl-o" | "up" | "down" | "shift-tab"}
  {"wait": "<regex>", "timeout": 120}          wait until the screen matches
  {"idle": 3, "timeout": 300}                  wait until the screen stops changing for N s
  {"absent": "<regex>", "stable": 3}           wait until the regex has been off screen for N s
  {"mark": "<anchor>"}                         log an anchor on the cast clock
  {"sleep": 1.5}
  {"screen": true}                             return the current screen
  {"quit": true}                               stop serving (the recorded shell must have exited)

The run dir receives session.cast, anchors.jsonl, screen.txt (live), and driver.log.
"""

import fcntl
import json
import os
import pty
import random
import re
import select
import signal
import socket
import struct
import sys
import termios
import threading
import time
from pathlib import Path

import pyte

ROOT = Path(__file__).resolve().parent.parent
COLS, ROWS = (int(n) for n in os.environ.get("DEMO_TERMINAL", "88x28").split("x"))
KEYS = {
    "enter": "\r", "esc": "\x1b", "tab": "\t", "shift-tab": "\x1b[Z",
    "ctrl-c": "\x03", "ctrl-d": "\x04", "ctrl-o": "\x0f", "up": "\x1b[A", "down": "\x1b[B",
    "left": "\x1b[D", "right": "\x1b[C", "backspace": "\x7f",
}


class Screen(pyte.Screen):
    """pyte rejects the private form of the device status query (CSI ? 6 n) that Copilot CLI sends."""

    def report_device_status(self, mode, **_):
        return super().report_device_status(mode)


class Driver:
    def __init__(self, run: Path):
        self.run = run
        self.screen = Screen(COLS, ROWS)
        self.stream = pyte.ByteStream(self.screen)
        self.lock = threading.Lock()
        self.changed = time.time()
        self.alive = True
        self.t0 = 0.0

    def start(self) -> None:
        pid, fd = pty.fork()
        if pid == 0:
            os.environ.update(TERM="xterm-256color", COLORTERM="truecolor")
            os.execvp("asciinema", [
                "asciinema", "rec", "-q", "--overwrite", "-f", "asciicast-v2",
                "--window-size", f"{COLS}x{ROWS}", "--capture-env", "TERM,COLORTERM",
                "-c", f"python3 {ROOT}/scripts/ce01_capture.py shell",
                str(self.run / "session.cast"),
            ])
        self.t0 = time.time()
        self.pid, self.fd = pid, fd
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))
        threading.Thread(target=self.pump, daemon=True).start()

    def pump(self) -> None:
        while self.alive:
            r, _, _ = select.select([self.fd], [], [], 0.5)
            if not r:
                continue
            try:
                data = os.read(self.fd, 65536)
            except OSError:
                break
            if not data:
                break
            with self.lock:
                self.stream.feed(data)
                self.changed = time.time()
                (self.run / "screen.txt").write_text(self.text())
        self.alive = False

    def text(self) -> str:
        return "\n".join(line.rstrip() for line in self.screen.display)

    def now(self) -> float:
        return round(time.time() - self.t0, 3)

    def log(self, msg: str) -> None:
        with (self.run / "driver.log").open("a") as f:
            f.write(f"{self.now():9.3f} {msg}\n")

    def write(self, s: str) -> None:
        os.write(self.fd, s.encode())

    def handle(self, cmd: dict) -> dict:
        if not self.alive and ("type" in cmd or "key" in cmd):
            return {"ok": False, "t": self.now(), "error": "recorded session has ended"}
        if "type" in cmd:
            lo, hi = cmd.get("cadence", [0.025, 0.06])
            for ch in cmd["type"]:
                self.write(ch)
                time.sleep(random.uniform(lo, hi) * (3 if ch in " ,." else 1))
            return {"ok": True, "t": self.now()}
        if "key" in cmd:
            self.write(KEYS[cmd["key"]])
            return {"ok": True, "t": self.now()}
        if "wait" in cmd:
            rx, deadline = re.compile(cmd["wait"], re.S), time.time() + cmd.get("timeout", 120)
            while time.time() < deadline and self.alive:
                with self.lock:
                    m = rx.search(self.text())
                if m:
                    return {"ok": True, "t": self.now(), "match": m.group(0)[:200]}
                time.sleep(0.2)
            return {"ok": False, "t": self.now(), "error": "timeout", "screen": self.text()}
        if "absent" in cmd:
            rx, deadline = re.compile(cmd["absent"], re.S), time.time() + cmd.get("timeout", 600)
            stable, since = cmd.get("stable", 3), None
            while time.time() < deadline and self.alive:
                with self.lock:
                    present = bool(rx.search(self.text()))
                since = None if present else (since or time.time())
                if since and time.time() - since >= stable:
                    return {"ok": True, "t": self.now()}
                time.sleep(0.2)
            return {"ok": False, "t": self.now(), "error": "timeout", "screen": self.text()}
        if "idle" in cmd:
            deadline = time.time() + cmd.get("timeout", 300)
            while time.time() < deadline and self.alive:
                if time.time() - self.changed >= cmd["idle"]:
                    return {"ok": True, "t": self.now()}
                time.sleep(0.2)
            return {"ok": False, "t": self.now(), "error": "timeout"}
        if "mark" in cmd:
            entry = {"anchor": cmd["mark"], "t": self.now()}
            with (self.run / "anchors.jsonl").open("a") as f:
                f.write(json.dumps(entry) + "\n")
            return {"ok": True, **entry}
        if "sleep" in cmd:
            time.sleep(cmd["sleep"])
            return {"ok": True, "t": self.now()}
        if "screen" in cmd:
            with self.lock:
                return {"ok": True, "t": self.now(), "screen": self.text()}
        return {"ok": False, "error": f"unknown command {cmd}"}


def serve(run: Path) -> None:
    run.mkdir(parents=True, exist_ok=True)
    for name in ("anchors.jsonl", "driver.log"):
        (run / name).unlink(missing_ok=True)
    sock_path = run / "ctl.sock"
    sock_path.unlink(missing_ok=True)
    d = Driver(run)
    d.start()
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(sock_path))
    srv.listen(1)
    print(f"driver serving {sock_path}", flush=True)
    while True:
        conn, _ = srv.accept()
        with conn:
            cmd = json.loads(conn.makefile().readline())
            if cmd.get("quit"):
                conn.sendall(b'{"ok": true}\n')
                break
            res = d.handle(cmd)
            d.log(f"{json.dumps(cmd)[:160]} -> {json.dumps({k: v for k, v in res.items() if k != 'screen'})}")
            conn.sendall((json.dumps(res) + "\n").encode())
    d.alive = False
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            if os.waitpid(d.pid, os.WNOHANG) != (0, 0):
                break
        except ChildProcessError:
            break
        time.sleep(0.2)
    else:
        os.kill(d.pid, signal.SIGHUP)
        os.waitpid(d.pid, 0)
    sock_path.unlink(missing_ok=True)


def send(run: Path, cmds: list[str]) -> None:
    for raw in cmds:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(str(run / "ctl.sock"))
        s.sendall((raw.strip() + "\n").encode())
        res = json.loads(s.makefile().readline())
        s.close()
        screen = res.pop("screen", None)
        print(json.dumps(res))
        if screen is not None:
            print(screen)
        if not res.get("ok"):
            sys.exit(1)


if __name__ == "__main__":
    mode, run = sys.argv[1], (ROOT / sys.argv[2]).resolve()
    serve(run) if mode == "serve" else send(run, sys.argv[3:])
