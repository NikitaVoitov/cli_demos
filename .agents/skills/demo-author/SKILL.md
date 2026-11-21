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
3. `python -m pipeline.post scenarios/<id> <take>` retimes and sanitizes into `artifacts/session.cast` and prints each beat's published time. Put chapter and gate times in `scenario.yaml`. Compression cuts most waiting, so a key result can scroll past before narration explains it: add `post.holds` (a regex on screen plus seconds) to freeze on those moments, and rerun post.
4. `python -m pipeline.transcript scenarios/<id> --client <client> --store <store.db>` writes `artifacts/transcript.json`.
5. Narrate (below), if the demo is narrated.
6. `cd apps/hub && npm run build`, then load the demo and play it through.

## Design the demo before recording

These come from owner reviews; skipping them cost SO-07 a full re-record. Details: §0.10 items 19–28.

- **Story first.** Write down the situation, the pain, what gets detected, the decision, and the outcome before writing beats. The About section in `how-it-works.md` tells that story first, then the technology. Aim for 2–3 minutes published.
- **The advertised technique must find the answer.** If the title says ML, seed data where the model flags the culprit. Check the feature's distribution with a search before you fit. A model that misses on purpose is fine only as a theory the agent rules out.
- **Evidence has to be on screen.** Cursor CLI shows an MCP call as a bare tool name; Ctrl+O doesn't expand it, and hints asking the agent to "show evidence" get ignored. Use several short prompts, each with `wait: turn-end`, so each turn ends with an answer (a list, a result table, the key numbers). Put `require: gate` only on the turn that writes.
- **Show the source and the proof, not only the result.** `browser.steps` puts screenshots in the pane before the final one, such as the source records the agent reads and the tool's own UI showing the key result. Copy for each step goes in `content.yaml` `browser.steps.<id>`.
- **Writes outside Splunk get a wrapper.** Copy `recorder/clients/cursor-cli/acli.tmpl`: allow-list commands, answer writes without `--yes` with a short `CONFIRMATION_REQUIRED` line (Cursor truncates long output), and deny the MCP server's write tools in the capture config.
- **SaaS data lives on a personal or demo tenant.** Scripts refuse the corporate host. Add sanitizer rules for the tenant's host, emails, account IDs, and display names before the first post.
- **Interactive logins use real Chrome.** For SSO or passkeys, follow `scripts/jira_web_login.mjs`: launch the installed Chrome with its own profile, attach over CDP, and wait for the session cookie, not a URL.

- **More than one approval:** use `gates:` instead of `gate` in `scenario.yaml` and `gates.<id>` copy in `content.yaml`; IDs can't match chapter IDs, and narration can anchor to any gate ID. Put a per-beat `evidence` on each `wait` that requires a different refusal text. See `scenarios/so-03-notebook-spray-hunt`.
- **n8n demos:** the side pane can be the real n8n canvas instead of screenshots (§0.12). Export the workflow from n8n and run `python -m pipeline.workflow scenarios/<id> <export.json>`; add `workflow: { src, steps }` to `scenario.yaml` (steps by node name, timed by chapter, gate, or seconds) and `workflow: { alt, callouts }` to `content.yaml`. Build the canvas with `.captures/venv/bin/python scripts/n8n_preview_snapshot.py` before `npm run build`; the build fails without it. Check with `apps/hub/scripts/check-workflow-pane.mjs`. A demo can have both: `browser.steps` screenshots and the canvas share the pane, and `workflow.show: { from, until }` (chapter, gate, or seconds) sets when the canvas takes it; the Slack-style final `browser.screenshot` still appears at `browser.showAt` after approval. `workflow.startedBy` (a regex on the shell command) adds the workflow's full, importable JSON to the transcript as an Artifact entry right after that command.
- **Per-take values:** `recording.vars: { NAME: <command> }` runs each command before a take and puts its output wherever `__NAME__` appears in the hints (for example a case ID no earlier take used). The values are saved in the take's `vars.json`.
- **Notebook demos:** `integrations: [notebook]` plus `recording.notebook.gated: [cell ids]` gives a gated `jpterm` (copy `jpterm.tmpl` for other gated tools). Files the agent needs in the workspace go in `fixtures.stage`, because the workspace is emptied first. A different stack uses `recording.stackProfile` and `scripts/stack_profile.py`; run any command against it with `python3 scripts/with_stack.py <profile> <command>` (splunkctl reads `SPLUNKCTL_HOST`/`SPLUNKCTL_TOKEN`, so `~/.splunkctl` stays on CO2).

### Lessons from SO-08 (Agent Launchpad, n8n, Outlook, Slack)

Setup sheets: `scenarios/so-08-phishing-containment/fixtures/LAUNCHPAD_SETUP.md` and `N8N_SETUP.md`.

- **Agent Launchpad agents run too long for MCP.** A `| aiagent` search takes about a minute; Cursor CLI's MCP call times out first, so the agent runs through splunkctl (`integrations: [search-reads]` confirms searches without write commands; other writes still stop). Calling it over MCP also needs `aiagent` on the MCP Server's Allowed SPL commands. Agent creation fails on a stack without an SCS token for AI Toolkit (CO2: "SCS Token not found"); use MDL.
- **Hand the Launchpad agent its searches.** A free-form agent took 4–5 model turns, searched subjects with the wrong dash, used the wrong user format, and ran 200 s. One ready-made search per task in its system prompt (`multisearch` for triage) gave one tool call, about 60 s, and the same answer every take. Format times inside the SPL. Spell out conclusions ("complete only if both counts are 0").
- **Model settings.** Anthropic and GPT-5 reject a non-default temperature: keep 1. AI Toolkit LLM connections can be created over REST (`POST /servicesNS/<user>/Splunk_ML_Toolkit/mltk/aicommander` with `action: test_connection`, then `create`); don't make one the default on a shared stack.
- **n8n.** Build with the n8n MCP (Workflow SDK, `validate_workflow`, `update_workflow`) and republish after every change; drafts don't serve the production webhook. `renameNode` doesn't rewrite `$('Old name')` references in expressions. A multi-event HEC body must go as `rawContentType: text/plain` (as JSON, n8n re-encodes it as one string). Turn off the Slack node's `includeLinkToWorkflow`, which puts the instance hostname in the message.
- **Slack notices come from a bot.** n8n's one-click Slack OAuth posts with your user token, so the notice comes from you and Slack doesn't notify you. Create a bot app from a manifest with `chat:write` and `chat:write.public` (posts to public channels without an invite) and use an Access Token credential with its `xoxb-` token (not the `xapp-` app-level token).
- **Outlook in the capture home.** The Outlook plugin's MCP server is Cursor-hosted; Cursor CLI loads it only with `--plugin-dir` (the `outlook` step adds an `agent` shim) and needs a one-time `/mcp` > Log in there. An email "from" an employee can't be sent from outlook.com; write an `.eml` (base64 bodies, CRLF; quoted-printable gets mangled) and drag it onto the folder in Outlook for Mac.
- **Screenshots from desktop apps.** The DevTools MCP browser is anonymized (no SSO), and web Outlook shows ads. Capture the app window with `screencapture -x -o -l <window id>` (IDs from `CGWindowListCopyWindowInfo`; Cursor needs Screen Recording permission), crop to the content, and paint over your own name. Simulated clicks need Accessibility permission, so ask the owner to open the right message.
- **Sanitizer cases this demo hit:** addresses the terminal wraps mid-domain (`acme-corp.examp|le`), Microsoft Graph URLs with `%40` addresses and mailbox IDs, and Graph `displayName` folder names (masked only for Atlassian now). Seeded story data uses the `.example` TLD so it stays readable.
- **Takes with real side effects** (records in Splunk, Slack posts) need a fresh key each time: use `recording.vars`. Delete test notices before the screenshot.
- **`.env` values with spaces must be quoted.** Sourcing `.env` in zsh runs the rest of the line as a command and prints it.

## Verify in the hub

- Check state, not wall-clock time. Headless browsers play the narrated player unevenly. Confirm the gate (the Approve button stays until clicked), the pane steps (image alt text), and the ending from the DOM.
- Render an exact moment from `artifacts/session.cast` with pyte when you need to see what the screen shows at a time.

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
- **Narrate the story, not the tool calls.** Each line should move the incident forward (what's wrong, what was found, what it means, what happens next). "Splunk MCP returns the knowledge objects" is a fact without a story.
- **Use the run's real numbers,** rounded for speech ("about 480 milliseconds"), and only ones the transcript shows.
- **Write speakable text.** No flags, paths, or code: "with your go-ahead", not `--yes`. Product names are fine. The caption shows exactly this text.
- **Voice:** follow the Splunk voice guide: conversational, concise, positive, technically credible, and never salesy.
- Open with what the demo does. Close with the outcome in one short sentence.

### Voice and tools

- Keep the house voice in `recorder/voice.yaml` so every demo sounds like one product. Override per scenario only with a reason.
- To audition voices, use `elevenlabs voices search` and `elevenlabs say --voice <id> "…"`, or the ElevenLabs MCP server (`creative_list_voices`, `creative_generate_speech`). Final audio always comes from `pipeline.narrate` through the CLI, so it can be rebuilt.
- `eleven_v4` ignores `speed`; only spelling changes how a term sounds. Speech-to-text can't hear how an acronym was said (it writes back "SOC" either way), but its word timestamps show length. For a disputed term, write a few short clips to `.captures/audition/<id>/`, open the folder for the owner, and use the one they pick.
- A house `pronounce` change touches every demo that uses the term: rerun `pipeline.narrate` for each, then `--check` them all.
- Leave at least 0.4 s between lines; `narrate` rejects a gap of exactly 0.3 s.
- Credentials: `elevenlabs auth login` locally. In CI, pipe the key in with `elevenlabs auth login --with-token` so it never appears on a command line.

## Don't

- Hand-edit anything in `artifacts/`, or put narration text in `content.yaml`.
- Commit anything from `.captures/`, or any token, username, IP, or real stack hostname.
- Push to `main` or write to Sanity.
