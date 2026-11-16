"""Build a scenario's transcript.json from a client session log and the published cast.

  python -m pipeline.transcript scenarios/ce-01-dashboard --client cursor-cli --store <store.db>

Entries come from the session log, so commands, MCP arguments, and tool results are complete
even where the client's TUI collapsed them. Times come from the published cast: each entry is
placed where its text first appears on screen after the previous entry.
"""

import argparse
import json
import re
from bisect import bisect_right
from pathlib import Path

import yaml

from . import sanitize
from .clients import Event, cursor_cli

ADAPTERS = {"cursor-cli": cursor_cli}
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07|\x1b[()][A-Z0-9]")
MAX_ROWS = 8


def _plain(text: str) -> str:
    """Drop the markdown that TUIs render away, so the text matches what was on screen."""
    return re.sub(r"`([^`]+)`|\*\*([^*]+)\*\*", lambda m: m.group(1) or m.group(2), text)


def _squash(text: str) -> str:
    return re.sub(r"[\s`*▎…]+", "", text)


class CastClock:
    """Finds when text first appears in a cast, searching forward only."""

    def __init__(self, cast: Path):
        lines = cast.read_text().splitlines()[1:]
        self.times, self.offsets, parts, pos = [], [], [], 0
        for line in lines:
            t, _, data = json.loads(line)
            chunk = _squash(ANSI.sub("", data))
            self.times.append(t)
            self.offsets.append(pos)
            parts.append(chunk)
            pos += len(chunk)
        self.stream = "".join(parts)
        self.cursor = 0
        self.last = 0.0

    def at(self, needle: str) -> float:
        key = _squash(needle)[:32]
        hit = self.stream.find(key, self.cursor) if key else -1
        if hit >= 0:
            self.cursor = hit
            self.last = round(self.times[bisect_right(self.offsets, hit) - 1], 1)
        return self.last


def _compact_json(text: str) -> str:
    try:
        data = json.loads(text)
    except ValueError:
        return text
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        rows = data["results"]
        shown = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows[:MAX_ROWS])
        more = f"\n… {len(rows) - MAX_ROWS} more rows" if len(rows) > MAX_ROWS else ""
        return f"{len(rows)} rows\n{shown}{more}"
    return json.dumps(data, indent=2, ensure_ascii=False)


def _skill_name(path: str, output: str) -> str:
    front = re.search(r"^name:\s*['\"]?([\w-]+)", output, re.M)
    return front.group(1) if front else Path(path).parent.name


def build_entries(events: list[Event], adapter, scenario: dict, clock: CastClock) -> list[dict]:
    dashboard = Path((scenario.get("artifacts") or {}).get("dashboard", "")).name
    entries: list[dict] = []
    skills_seen: set[str] = set()
    last_browser: dict | None = None
    for event in events:
        if event.kind in ("user", "agent"):
            # Keep the markdown; the hub renders it. Timing matches the plain text the TUI drew.
            entries.append({"kind": event.kind, "t": clock.at(_plain(event.text)), "text": event.text.strip()})
            continue
        action, data = adapter.normalize_call(event)
        if action == "shell":
            command, out = data["command"], data["output"]
            kind = "browser" if command.startswith("playwright-cli") else "shell"
            entry = {"kind": kind, "t": clock.at(command), "command": command,
                     "result": out["text"] or f"(no output) exit {out['exit']}"}
            if kind == "shell" and out["exit"] not in (0, None) and "requires confirmation" in out["text"]:
                entry["blocked"] = True
            if event.by_user:
                entry["by"] = "user"
            entries.append(entry)
            last_browser = entry if kind == "browser" else None
        elif action == "mcp":
            entries.append({"kind": "mcp", "t": clock.at(f"{data['server']} {data['tool']}"), "tool": data["tool"],
                            "args": data["args"], "result": _compact_json(data["output"])})
            last_browser = None
        elif action == "read" and data["path"].endswith("SKILL.md"):
            name = _skill_name(data["path"], data["output"])
            if name not in skills_seen:
                skills_seen.add(name)
                entries.append({"kind": "skill", "t": clock.at(name), "name": name})
        elif action == "read" and last_browser and Path(data["path"]).name in last_browser["command"]:
            last_browser["result"] += f"\n\n── {Path(data['path']).name} ──\n{data['output'].strip()}"
        elif action == "write":
            name = Path(data["path"]).name
            entry = {"kind": "file", "t": clock.at(f"Edited {name}"), "name": name}
            if name == dashboard:
                entry.update(tag="Dashboard Studio", artifact="dashboard")
            entries.append(entry)
    return entries


def _summary(entries: list[dict]) -> str:
    labels = [("skill", "skill"), ("mcp", "MCP call"), ("shell", "shell command"), ("browser", "browser command"), ("file", "file")]
    parts = []
    for kind, label in labels:
        n = sum(1 for e in entries if e["kind"] == kind)
        if n:
            parts.append(f"{n} {label}{'' if n == 1 else 's'}")
    return " · ".join(parts) or "Your prompt"


def group(entries: list[dict], scenario: dict) -> list[dict]:
    chapters = sorted(scenario["chapters"], key=lambda c: c["t"])
    starts = [c["t"] for c in chapters]
    gate_t = (scenario.get("gate") or {}).get("t")
    out = [{"id": c["id"], "entries": []} for c in chapters]
    for entry in entries:
        out[max(bisect_right(starts, entry["t"]) - 1, 0)]["entries"].append(entry)
    for chapter, start, end in zip(out, starts, starts[1:] + [float("inf")]):
        chapter["summary"] = _summary(chapter["entries"])
        if gate_t is not None and start <= gate_t < end:
            chapter["gate"] = True
            chapter["summary"] = "The write stopped at CONFIRMATION_REQUIRED until you approved"
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("scenario", type=Path)
    p.add_argument("--client", default="cursor-cli", choices=sorted(ADAPTERS))
    p.add_argument("--store", type=Path, required=True)
    args = p.parse_args()

    scenario = yaml.safe_load((args.scenario / "scenario.yaml").read_text())
    adapter = ADAPTERS[args.client]
    events = adapter.load_session(args.store)
    cast = args.scenario / scenario["cast"]["src"]
    entries = build_entries(events, adapter, scenario, CastClock(cast))

    transcript = {"placeholder": False, "source": f"{args.client} session log", "chapters": group(entries, scenario)}
    raw = json.dumps(transcript, ensure_ascii=False, indent=2)
    clean = sanitize.apply(raw, sanitize.find_replacements(raw))
    out = args.scenario / scenario["artifacts"]["transcript"]
    out.write_text(clean + "\n")

    counts = {c["id"]: len(c["entries"]) for c in transcript["chapters"]}
    print(f"wrote {out} · entries per chapter {counts} · leftovers {sanitize.leftovers(clean) or 'none'}")


if __name__ == "__main__":
    main()
