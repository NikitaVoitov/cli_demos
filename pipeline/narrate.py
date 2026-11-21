"""Turn a scenario's narration lines into one audio track and captions on the published cast clock.

  .captures/venv/bin/python -m pipeline.narrate scenarios/<id>              # synthesize, check fit, write
  .captures/venv/bin/python -m pipeline.narrate scenarios/<id> --estimate   # check fit from word counts, no API calls
  .captures/venv/bin/python -m pipeline.narrate scenarios/<id> --check      # fail if audio/captions are stale, no API calls

Each line in `scenario.yaml` `narration.lines` starts at a chapter (`chapter: <id>` or `chapter: gate`, or a `gates` id,
plus an optional `offset`) or at an absolute `t`. Clips come from the ElevenLabs CLI with the voice in recorder/voice.yaml
(a scenario can override it) and are cached in .captures/<id>/narration/ by a hash of the spoken text, voice, and
model, so editing one line only re-synthesizes that line.

A track is written only when every line fits: lines don't overlap, none runs past the end of the cast, none is
still playing when the player pauses at a gate, and no stretch of silence is longer than `maxSilence`
(recorder/voice.yaml, overridable in `narration`). Otherwise nothing is written and the report says how many words
to cut or how far to move each line, and lists the transcript entries that happen during each long silence. Outputs are `narration.audio` (one mono MP3 as long as the cast, for
the player's audioUrl) and `narration.captions` (WebVTT, one cue per line, the cue id is the line id).
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
VOICE = ROOT / "recorder/voice.yaml"
GAP = 0.3            # silence kept between two lines and before the gate
SOURCE_FORMAT = "mp3_44100_128"


def load(scenario_dir: Path) -> tuple[dict, dict, dict]:
    scenario = yaml.safe_load((scenario_dir / "scenario.yaml").read_text())
    narration = scenario.get("narration")
    if not narration or not narration.get("lines"):
        raise SystemExit(f"{scenario['id']}: scenario.yaml has no narration.lines")
    house = yaml.safe_load(VOICE.read_text())
    override = narration.get("voice") or {}
    voice = {**house["voice"], **override, "settings": {**house["voice"]["settings"], **override.get("settings", {})}}
    return scenario, narration, {**house, "voice": voice}


def gate_list(scenario: dict) -> list[dict]:
    """The approvals in time order: `gate` is one (id `gate`), `gates` lists several (a notebook's approved cells)."""
    if scenario.get("gate") and scenario.get("gates"):
        raise SystemExit(f"{scenario['id']}: use either gate or gates, not both")
    gates = scenario.get("gates") or ([{"id": "gate", **scenario["gate"]}] if scenario.get("gate") else [])
    return sorted(gates, key=lambda g: g["t"])


def resolve_starts(scenario: dict, lines: list[dict]) -> list[float]:
    anchors = {c["id"]: c["t"] for c in scenario.get("chapters", [])}
    for gate in gate_list(scenario):
        anchors[gate["id"]] = gate["t"]
    starts = []
    for line in lines:
        if "t" in line:
            starts.append(round(float(line["t"]), 2))
        elif line.get("chapter") in anchors:
            starts.append(round(anchors[line["chapter"]] + float(line.get("offset", 0)), 2))
        else:
            raise SystemExit(f"line {line.get('id')!r}: needs `t` or a `chapter` from {sorted(anchors)}")
    return starts


def spoken(text: str, pronounce: dict[str, str]) -> str:
    for written, said in pronounce.items():
        text = re.sub(rf"(?<![\w-]){re.escape(written)}(?![\w-])", said, text)
    return " ".join(text.split())


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(out.stdout.strip())


def synthesize(text: str, voice: dict, cache: Path, previous: str | None, following: str | None) -> Path:
    key = hashlib.sha256(json.dumps([text, voice["id"], voice["model"], voice["settings"]]).encode()).hexdigest()[:16]
    clip = cache / f"{key}.mp3"
    if clip.exists():
        return clip
    cmd = [
        "elevenlabs", "text-to-speech", "convert", "--format", "json",
        "--text", text, "--voice-id", voice["id"], "--model-id", voice["model"],
        "--output-format", SOURCE_FORMAT, "--voice-settings", json.dumps(voice["settings"]),
        "-o", str(clip),
    ]
    # Neighboring text keeps intonation continuous across separately synthesized clips.
    if previous:
        cmd += ["--previous-text", previous]
    if following:
        cmd += ["--next-text", following]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not clip.exists():
        clip.unlink(missing_ok=True)
        raise SystemExit(f"elevenlabs failed for {text[:40]!r}:\n{result.stdout}{result.stderr}")
    return clip


def fit_problems(lines, starts, lengths, cast_end: float, gate_ts: list[float], wps: float) -> dict[str, str]:
    problems: dict[str, str] = {}

    def cut(over: float) -> str:
        return f"cut about {max(1, round(over * wps + 0.5))} words or start {over:.1f} s earlier"

    order = sorted(range(len(lines)), key=lambda i: starts[i])
    for pos, i in enumerate(order):
        end = starts[i] + lengths[i]
        limits = [(cast_end, "the end of the cast")]
        if pos + 1 < len(order):
            j = order[pos + 1]
            limits.append((starts[j] - GAP, f"line {lines[j]['id']!r}"))
        upcoming = [g for g in gate_ts if starts[i] < g]
        if upcoming:
            limits.append((min(upcoming) - GAP, "the gate, where the player pauses"))
        limit, what = min(limits)
        if starts[i] < 0:
            problems[lines[i]["id"]] = "starts before the cast does"
        elif end > limit + 1e-6:
            problems[lines[i]["id"]] = f"runs {end - limit:.1f} s into {what}: {cut(end - limit)}"
    return problems


def describe(entry: dict) -> str:
    kind = entry["kind"]
    if kind in ("user", "agent"):
        what = " ".join(entry["text"].split())[:70]
    elif kind == "mcp":
        what = entry["tool"]
    elif kind in ("file", "skill"):
        what = entry["name"]
    else:
        what = " ".join(entry["command"].split())[:60]
    return f"{entry['t']:.1f} {kind}: {what}"


def silence_problems(lines, starts, lengths, cast_end: float, gate_ts: list[float], max_silence: float,
                     events: list[dict]) -> dict[str, str]:
    """Silent stretches longer than max_silence, attributed to the line before them (or the first line).

    Each gate splits a stretch in two, because the player sits paused there, not silent. Each problem lists what
    the transcript shows happening during the silence, which is what the missing narration should cover.
    """
    order = sorted(range(len(lines)), key=lambda i: starts[i])
    spans = [(None, 0.0, starts[order[0]])]
    spans += [(i, starts[i] + lengths[i], starts[j]) for i, j in zip(order, order[1:])]
    spans.append((order[-1], starts[order[-1]] + lengths[order[-1]], cast_end))
    for gate_t in gate_ts:
        spans = [part for owner, a, b in spans
                 for part in ([(owner, a, gate_t), (owner, gate_t, b)] if a < gate_t < b else [(owner, a, b)])]
    problems: dict[str, str] = {}
    for owner, a, b in spans:
        if b - a <= max_silence + 1e-6:
            continue
        during = [describe(e) for e in events if a - 0.5 <= e["t"] < b]
        key = lines[owner if owner is not None else order[0]]["id"]
        where = "before it" if owner is None else "after it"
        note = f"{b - a:.1f} s of silence {where} ({a:.1f}-{b:.1f}); narrate what happens or what it's for"
        note += ":\n      " + "\n      ".join(during) if during else " (no transcript entries: say what to watch for)"
        problems[key] = f"{problems[key]}; {note}" if key in problems else note
    return problems


def vtt_time(t: float) -> str:
    ms = round(t * 1000)
    return f"{ms // 3_600_000:02d}:{ms // 60_000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}"


def write_captions(path: Path, voice: dict, lines, starts, lengths) -> None:
    out = ["WEBVTT", "", f"NOTE Narration by an AI voice: {voice['name']} ({voice['id']}), {voice['model']}.", ""]
    for line, start, length in sorted(zip(lines, starts, lengths), key=lambda row: row[1]):
        out += [line["id"], f"{vtt_time(start)} --> {vtt_time(start + length)}", " ".join(line["text"].split()), ""]
    path.write_text("\n".join(out))


def mix(path: Path, clips: list[Path], starts: list[float], total: float) -> None:
    inputs, chains = [], []
    for i, (clip, start) in enumerate(zip(clips, starts)):
        inputs += ["-i", str(clip)]
        ms = round(start * 1000)
        chains.append(f"[{i}:a]aformat=channel_layouts=mono,adelay={ms}:all=1[a{i}]")
    labels = "".join(f"[a{i}]" for i in range(len(clips)))
    mixed = f"{labels}amix=inputs={len(clips)}:normalize=0:dropout_transition=0" if len(clips) > 1 else labels + "anull"
    # Pad to the cast's length so every seek position exists in the audio.
    graph = ";".join(chains) + f";{mixed},apad=whole_dur={total},atrim=0:{total}[out]"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs, "-filter_complex", graph,
         "-map", "[out]", "-ac", "1", "-ar", "44100", "-b:a", "64k", str(path)],
        check=True,
    )


def report(lines, starts, lengths, problems: dict[str, str], estimated: bool) -> None:
    unit = "est" if estimated else "len"
    print(f"  {'line':<16}{'start':>7}{'end':>8}{unit:>7}  words")
    for line, start, length in sorted(zip(lines, starts, lengths), key=lambda row: row[1]):
        flag = f"  <- {problems[line['id']]}" if line["id"] in problems else ""
        print(f"  {line['id']:<16}{start:7.1f}{start + length:8.1f}{length:7.1f}  {len(line['text'].split()):>5}{flag}")


def stale_lines(captions: Path, voice: dict, lines, starts) -> list[str]:
    """Lines whose caption cue is missing or differs in text or start, plus a voice change, as a list of reasons."""
    if not captions.exists():
        return [f"{captions.name} is missing"]
    vtt = captions.read_text()
    cues = {}
    for block in vtt.split("\n\n"):
        rows = block.strip().split("\n")
        if len(rows) >= 3 and "-->" in rows[1]:
            h, m, s = rows[1].split("-->")[0].strip().split(":")
            cues[rows[0]] = (int(h) * 3600 + int(m) * 60 + float(s), " ".join(rows[2:]))
    reasons = [f"line {line['id']!r} changed" for line, start in zip(lines, starts)
               if line["id"] not in cues
               or cues[line["id"]][1] != " ".join(line["text"].split())
               or abs(cues[line["id"]][0] - start) > 0.02]
    reasons += [f"cue {cue!r} has no line" for cue in cues.keys() - {line["id"] for line in lines}]
    if f"({voice['id']}), {voice['model']}." not in vtt:
        reasons.append("voice or model changed")
    return reasons


def narrate(scenario_dir: Path, estimate: bool, check: bool) -> int:
    scenario, narration, house = load(scenario_dir)
    voice, pronounce, wps = house["voice"], house.get("pronounce", {}), house.get("wordsPerSecond", 2.3)
    lines = narration["lines"]
    ids = [line["id"] for line in lines]
    if len(set(ids)) != len(ids):
        raise SystemExit(f"duplicate narration line ids: {ids}")
    starts = resolve_starts(scenario, lines)

    if check:
        captions = scenario_dir / narration.get("captions", "artifacts/narration.vtt")
        audio = scenario_dir / narration.get("audio", "artifacts/narration.mp3")
        reasons = stale_lines(captions, voice, lines, starts) + ([] if audio.exists() else [f"{audio.name} is missing"])
        for reason in reasons:
            print(f"stale: {reason}")
        print(f"{scenario['id']}: narration is current" if not reasons else f"rerun python -m pipeline.narrate scenarios/{scenario['id']}")
        return 1 if reasons else 0

    cast_end = scenario["cast"]["duration"]
    gate_ts = [g["t"] for g in gate_list(scenario)]
    texts = [spoken(line["text"], pronounce) for line in lines]
    max_silence = float(narration.get("maxSilence", house.get("maxSilence", 3.0)))
    transcript = scenario_dir / scenario.get("artifacts", {}).get("transcript", "artifacts/transcript.json")
    events = sorted(
        (e for ch in (json.loads(transcript.read_text())["chapters"] if transcript.exists() else []) for e in ch["entries"]),
        key=lambda e: e["t"],
    )

    def problems_for(lengths: list[float]) -> dict[str, str]:
        found = fit_problems(lines, starts, lengths, cast_end, gate_ts, wps)
        for key, note in silence_problems(lines, starts, lengths, cast_end, gate_ts, max_silence, events).items():
            found[key] = f"{found[key]}; {note}" if key in found else note
        return found

    if estimate:
        lengths = [len(text.split()) / wps for text in texts]
        problems = problems_for(lengths)
        report(lines, starts, lengths, problems, estimated=True)
        print("estimate only; run without --estimate to synthesize" if not problems else f"{len(problems)} line(s) don't fit")
        return 1 if problems else 0

    for tool in ("elevenlabs", "ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise SystemExit(f"{tool} is not on PATH")
    cache = ROOT / ".captures" / scenario["id"] / "narration"
    cache.mkdir(parents=True, exist_ok=True)
    order = sorted(range(len(lines)), key=lambda i: starts[i])
    clips: list[Path] = [Path()] * len(lines)
    for pos, i in enumerate(order):
        previous = texts[order[pos - 1]] if pos > 0 else None
        following = texts[order[pos + 1]] if pos + 1 < len(order) else None
        clips[i] = synthesize(texts[i], voice, cache, previous, following)
    lengths = [round(duration(clip), 2) for clip in clips]

    problems = problems_for(lengths)
    report(lines, starts, lengths, problems, estimated=False)
    if problems:
        print(f"{len(problems)} line(s) don't fit; nothing written. Edit narration.lines and rerun.")
        return 1

    audio = scenario_dir / narration.get("audio", "artifacts/narration.mp3")
    captions = scenario_dir / narration.get("captions", "artifacts/narration.vtt")
    audio.parent.mkdir(parents=True, exist_ok=True)
    mix(audio, clips, starts, cast_end)
    write_captions(captions, voice, lines, starts, lengths)
    spoken_s = sum(lengths)
    print(f"wrote {audio.relative_to(ROOT)} ({audio.stat().st_size // 1024} KB, {duration(audio):.1f} s) and "
          f"{captions.relative_to(ROOT)}; speech covers {spoken_s:.0f} s of {cast_end:.0f} s")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scenario")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--estimate", action="store_true", help="check fit from word counts without calling ElevenLabs")
    mode.add_argument("--check", action="store_true", help="fail if the audio and captions are older than the lines")
    args = parser.parse_args()
    sys.exit(narrate((ROOT / args.scenario).resolve(), args.estimate, args.check))
