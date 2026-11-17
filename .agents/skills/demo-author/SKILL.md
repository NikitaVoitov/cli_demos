---
name: demo-author
description: Author, narrate, and check a demo in this repo's pipeline (scenarios/<id>/scenario.yaml, content.yaml, captures, ElevenLabs narration). Use when asked to build, record, update, or add voice-over narration to a demo scenario.
---

# Demo author

The pipeline is the same for every demo and every agent. You edit files under `scenarios/<id>/` and run
`python -m pipeline.<step>`; you never hand-write recording content, timing, audio, or captions.
The full design is `docs/demo_pipeline_architecture.md`; §0.10 covers capture and §0.11 covers narration.

## Files and who owns what

| File | Holds | Rule |
|---|---|---|
| `scenario.yaml` | Recording: client, fixtures, beats, chapter IDs and times, gate, artifacts, **narration lines** | Change it and the step that reads it must rerun |
| `content.yaml`, `how-it-works.md` | Text visitors read: title, summary, taxonomy, chapter labels, gate copy | Editable any time; never needs a capture or new audio |
| `artifacts/` | Generated: `session.cast`, `transcript.json`, `narration.mp3`, `narration.vtt`, screenshots | Only pipeline steps write these |
| `recorder/voice.yaml` | House voice, model, speaking rate, pronunciation map | Shared by all demos |

Every chapter ID in `scenario.yaml` needs a label in `content.yaml`, and the reverse.

## Steps

Use `.captures/venv/bin/python` (dependencies in `pipeline/requirements.txt`).

1. Write `scenario.yaml` (beats, fixtures, `recording.hints`) and `content.yaml`. Copy the shape of an existing scenario.
2. `python -m pipeline.capture scenarios/<id> <take>`. A person can watch; the take lands in `.captures/<id>/<take>/`.
3. `python -m pipeline.post scenarios/<id> <take>` retimes and sanitizes into `artifacts/session.cast` and prints each beat's published time. Put chapter and gate times in `scenario.yaml`.
4. `python -m pipeline.transcript scenarios/<id> --client <client> --store <store.db>` writes `artifacts/transcript.json`.
5. Narrate (below), if the demo is narrated.
6. `cd apps/hub && npm run build`, then load the demo and play it through.

## Narration

A narrated demo has a `narration` block in `scenario.yaml`. Text lives there, not in `content.yaml`, because changing a line means new audio:

```yaml
narration:
  audio: artifacts/narration.mp3
  captions: artifacts/narration.vtt
  # voice: { id: ..., model: ..., settings: { speed: 1.05 } }   # only to override recorder/voice.yaml
  lines:
    - { id: intro, chapter: prompt, offset: 0.3, text: "..." }   # start at a chapter, plus an offset
    - { id: gate, t: 79.2, text: "..." }                         # or at an absolute time on the published cast
    - { id: deploy, chapter: gate, offset: 0.8, text: "..." }    # `gate` is an anchor too
```

### Workflow

1. **Read the run.** Chapter and gate times from `scenario.yaml`, and `artifacts/transcript.json` for when each thing happens (every entry has `t` on the published clock). Narration timing comes from these, never from guessing.
2. **Draft lines** with the rules below.
3. **Check the fit for free:** `python -m pipeline.narrate scenarios/<id> --estimate`. Fix every flagged line: cut the words it names, or move it. For a silence it flags, add a line that covers the transcript entries it lists.
4. **Synthesize:** `python -m pipeline.narrate scenarios/<id>`. It uses the ElevenLabs CLI, caches clips by text and voice, and writes nothing unless every real clip fits. Repeat 3–4 until it passes.
5. **Listen through speech-to-text** (you can't hear the clip): `elevenlabs speech-to-text convert --model-id scribe_v1 --file scenarios/<id>/artifacts/narration.mp3 --format json --query text`. If a term comes back wrong, add its spoken form to `pronounce` in `recorder/voice.yaml` and rerun step 4. Captions keep the written form.
6. **Confirm:** `python -m pipeline.narrate scenarios/<id> --check` passes. In the hub, Play starts the sound, captions appear over the terminal in the SDS warning orange (the **Captions** button in its header toggles them; they hide while the player's speaker is muted), and the audio pauses at the gate and resumes on Approve.
7. Commit `scenario.yaml`, `narration.mp3`, and `narration.vtt` together. The hub refuses to load narration whose captions don't match the lines.

### Writing lines

- **Say what the screen can't.** Why a step matters, what the agent learned, what's at stake. Don't read out commands or output the viewer can already see.
- **One idea per line, 8–25 words, under about 10 s.** Present tense. The agent is the subject ("Cursor loads…"); the visitor is "you" at the gate ("waits for your approval").
- **Start a line when its moment appears on screen.** A line may start up to 5 s early to set up an event, but never after the event is over.
- **The gate:** nothing may still be playing when the player pauses there, because the audio stops mid-word. Put one line just before the gate saying why the write stopped. Put one at `chapter: gate, offset: ~0.8` acknowledging the approval.
- **Never go quiet while something is happening.** No silence longer than `maxSilence` (3 s, `recorder/voice.yaml`); `narrate` rejects a track that has one and lists the transcript entries in that gap. Expect speech to cover 75–90% of the cast. Fill a long stretch, such as an agent thinking, a slow search, or a browser check, with one of three things:
  - **What it's doing right now**, read from the transcript entries in the gap ("It also lists the dashboards already in Splunk…").
  - **Why it matters**, the value behind the step ("Every panel starts from a search that already returned real data").
  - **What to expect next** ("Region names in the bar chart prove the last panel has data too").
  Split a long stretch into two lines tied to the events inside it rather than one long sentence.
- **Use the run's real numbers,** rounded for speech ("about 480 milliseconds"), and only ones the transcript shows.
- **Write speakable text.** No flags, paths, or code: "with your go-ahead", not `--yes`. Product names are fine. The caption shows exactly this text.
- **Voice:** follow the Splunk voice guide: conversational, concise, positive, technically credible, and never salesy.
- Open with what the demo does. Close with the outcome in one short sentence.

### Voice and tools

- Keep the house voice in `recorder/voice.yaml` so every demo sounds like one product. Override per scenario only with a reason.
- To audition voices, use `elevenlabs voices search` and `elevenlabs say --voice <id> "…"`, or the ElevenLabs MCP server (`creative_list_voices`, `creative_generate_speech`). Final audio always comes from `pipeline.narrate` through the CLI, so it can be rebuilt.
- Credentials: `elevenlabs auth login` locally. In CI, pipe the key in with `elevenlabs auth login --with-token` so it never appears on a command line.

## Don't

- Hand-edit anything in `artifacts/`, or put narration text in `content.yaml`.
- Commit anything from `.captures/`, or any token, username, IP, or real stack hostname.
- Push to `main` or write to Sanity.
