"""The hub's notebook pane: a second cast showing the notebook as the agent changes it, on the published clock.

The gated jpterm (recorder/clients/cursor-cli/jpterm.tmpl) logs every `write` and `execute` to
~/.cache/jpterm-trace: when each started and ended, the notebook file before the first change, and the file after
each one. Capture copies that into <take>/notebook-trace, and the driver writes the wall-clock time of cast t=0 to
<take>/clock.json. Each state is rendered with euporie-preview; an executing cell shows as running ([*]) from when
its command started until its outputs were saved.

    notebookPane: { notebook: hunt.ipynb, cast: artifacts/notebook.cast, cols: 100 }   # in scenario.yaml

Writes the cast (one full-screen frame per state) and <cast>.json beside it: the rows, and for each frame its time,
the cell it changed, whether that cell is running, and `focus`, the line the pane scrolls to: the cell's heading while
it runs, then its first output.
"""

import copy
import fcntl
import json
import os
import pty
import re
import struct
import subprocess
import termios
from collections.abc import Callable
from pathlib import Path

from . import sanitize

ANSI = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07]*\x07")
PROMPT = re.compile(r"^\s*\[(\*|\d+| )\]")
HEADING_ROWS = 7     # a step's Markdown heading box above its code cell


def render(notebook: Path, cols: int, euporie: Path) -> str:
    """The notebook as ANSI text, `cols` wide.

    euporie-preview sizes its page from the terminal on stderr (80 columns when there is none), so stderr gets a
    pseudo-terminal of the wanted width while stdout stays a pipe."""
    env = {**os.environ, "TERM": "xterm-256color", "COLORTERM": "truecolor"}
    term, tty = pty.openpty()
    fcntl.ioctl(tty, termios.TIOCSWINSZ, struct.pack("HHHH", 50, cols, 0, 0))
    try:
        result = subprocess.run([str(euporie), "--color-depth", "24", "--color-scheme", "dark", "--graphics", "none",
                                 "--max-notebook-width", str(cols), str(notebook)],
                                stdout=subprocess.PIPE, stderr=tty, stdin=subprocess.DEVNULL, text=True, env=env,
                                timeout=120)
    finally:
        os.close(tty)
        os.close(term)
    if result.returncode:
        raise SystemExit(f"euporie-preview failed on {notebook.name} with exit code {result.returncode}")
    return result.stdout


def _focus(lines: list[str], cell: dict | None, running: bool) -> int:
    if not cell:
        return 0
    plain = [ANSI.sub("", line) for line in lines]
    first = next((s for s in "".join(cell.get("source", "")).split("\n") if s.strip()), "")[:40]
    top = next((i for i, line in enumerate(plain) if first and first in line), None)
    if top is None:
        return 0
    if running or not cell.get("outputs"):
        return max(0, top - HEADING_ROWS)
    # The next prompt after the code is the output's; with no outputs it would be the next cell's.
    out = next((i for i in range(top + 1, len(plain)) if PROMPT.match(plain[i])), top)
    return max(0, out - 1)


def _cell(notebook: dict, cell_id: str) -> dict | None:
    return next((c for c in notebook["cells"] if c.get("id") == cell_id), None)


def build(scenario: dict, run: Path, scenario_dir: Path, retime: Callable[[float], float]) -> None:
    pane = scenario.get("notebookPane")
    if not pane:
        return
    trace_dir, clock = run / "notebook-trace", run / "clock.json"
    if not (trace_dir / "trace.jsonl").exists() or not clock.exists():
        print("notebook pane: no jpterm trace or clock in the take; skipped")
        return
    t0 = json.loads(clock.read_text())["t0"]
    euporie = Path(scenario["recording"]["home"]) / "nb/bin/euporie-preview"
    cols = pane.get("cols", 100)

    states: list[tuple[float, dict, str | None, bool]] = []
    current = json.loads((trace_dir / "initial.ipynb").read_text())
    states.append((0.0, current, None, False))
    for op in map(json.loads, (trace_dir / "trace.jsonl").read_text().splitlines()):
        if not op["notebook"]:
            continue
        start, end = retime(op["start"] - t0), retime(op["end"] - t0)
        after = json.loads((trace_dir / op["notebook"]).read_text())
        if op["op"] == "execute" and end > start and _cell(current, op["cell"]):
            running = copy.deepcopy(current)
            cell = _cell(running, op["cell"])
            cell.update(execution_count="*", outputs=[])
            states.append((start, running, op["cell"], True))
        states.append((end, after, op["cell"], False))
        current = after

    work = run / "notebook-pane"
    work.mkdir(exist_ok=True)
    frames, texts = [], []
    for i, (t, notebook, cell_id, running) in enumerate(states):
        path = work / f"{i:03d}.ipynb"
        path.write_text(json.dumps(notebook))
        lines = render(path, cols, euporie).rstrip("\n").split("\n")
        texts.append(lines)
        frames.append({"t": round(t, 1), "focus": _focus(lines, _cell(notebook, cell_id) if cell_id else None, running),
                       "cell": cell_id, "running": running})

    reps = sanitize.find_replacements("\n".join("\n".join(lines) for lines in texts))
    rows = max(len(lines) for lines in texts) + 1
    header = {"version": 2, "width": cols, "height": rows, "title": pane["notebook"], "env": {"TERM": "xterm-256color"}}
    events = [[frame["t"], "o", sanitize.apply("\x1b[H\x1b[2J" + "\r\n".join(lines) + "\x1b[?25l", reps)]
              for frame, lines in zip(frames, texts)]
    dest = scenario_dir / pane["cast"]
    dest.write_text(json.dumps(header) + "\n" + "\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n")
    dest.with_suffix(".json").write_text(json.dumps({"rows": rows, "cols": cols, "frames": frames}, indent=1) + "\n")
    leftovers = sanitize.leftovers("".join(e[2] for e in events))
    print(f"notebook pane: {len(frames)} frames, {rows} rows; leftover identifiers {leftovers or 'none'}")
    for frame, (_, _, cell_id, running) in zip(frames, states):
        print(f"  {frame['t']:6.1f}  {cell_id or 'staged'}{' running' if running else ''}  focus line {frame['focus']}")
