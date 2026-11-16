"""Retime and sanitize a raw take into the scenario's published cast.

  .captures/venv/bin/python -m pipeline.post scenarios/<id> <take>

Writes <scenario>/artifacts/session.cast and prints each beat's time on the published clock, which is what
scenario.yaml chapters and the gate point at. The screen is replayed through pyte, so stretches where only a
spinner, token count, or timer moves are squeezed while every real change keeps its pace. Replacements keep
their original length so the client's boxes and columns stay aligned (§6.3).
"""

import json
import re
import sys
from pathlib import Path

import pyte
import yaml

from . import sanitize

ROOT = Path(__file__).resolve().parent.parent
MAX_GAP = 1.0        # longest pause kept between two meaningful screen changes
STATIC_SPAN = 0.8    # longest stretch kept where only the spinner, counters, or timers move
NOISE = [
    re.compile(r"[\u2800-\u28ff]"),
    re.compile(r"[\d.,]+k? tokens"),
    re.compile(r"\b\d+(\.\d+)?(ms|s|m)\b"),
    re.compile(r"\d+(\.\d+)?%"),
]


def normalized(screen: pyte.Screen) -> str:
    text = "\n".join(screen.display)
    for rx in NOISE:
        text = rx.sub("", text)
    return text


def post(scenario_dir: Path, take: str) -> None:
    scenario = yaml.safe_load((scenario_dir / "scenario.yaml").read_text())
    run = ROOT / ".captures" / scenario["id"] / take
    lines = (run / "session.cast").read_text().splitlines()
    header = json.loads(lines[0])
    events = [json.loads(line) for line in lines[1:]]
    anchors = [json.loads(line) for line in (run / "anchors.jsonl").read_text().splitlines()]
    reps = sanitize.find_replacements("".join(e[2] for e in events))

    screen = pyte.Screen(header["width"], header["height"])
    stream = pyte.Stream(screen)
    last_seen = normalized(screen)
    mapping, out, t_new, prev_t, budget = [], [], 0.0, 0.0, STATIC_SPAN
    for t, kind, data in events:
        gap = t - prev_t
        stream.feed(data)
        now_seen = normalized(screen)
        if now_seen == last_seen:
            step = min(gap, MAX_GAP, budget)
            budget -= step
        else:
            step = min(gap, MAX_GAP)
            budget = STATIC_SPAN
            last_seen = now_seen
        t_new += step
        prev_t = t
        mapping.append((t, t_new))
        out.append([round(t_new, 6), kind, sanitize.apply(data, reps)])

    def retime(t_old: float) -> float:
        best = 0.0
        for old, new in mapping:
            if old > t_old:
                break
            best = new
        return round(best, 1)

    header.update({"command": "zsh"})
    header.pop("idle_time_limit", None)
    dest = scenario_dir / scenario.get("cast", {}).get("src", "artifacts/session.cast")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(header) + "\n" + "\n".join(json.dumps(e, ensure_ascii=False) for e in out) + "\n")

    print(f"raw {events[-1][0]:.1f}s -> published {out[-1][0]:.1f}s, {len(out)} events, {len(reps)} replacements")
    print("leftover identifiers:", sanitize.leftovers("".join(e[2] for e in out)) or "none")
    for a in anchors:
        print(f"  {a['anchor']:<14} raw {a['t']:7.1f}  ->  {retime(a['t']):6.1f}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    post((ROOT / sys.argv[1]).resolve(), sys.argv[2])
