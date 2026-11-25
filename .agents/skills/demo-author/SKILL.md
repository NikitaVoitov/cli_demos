---
name: demo-author
description: Author, narrate, and check a demo in this repo's pipeline (scenarios/<id>/scenario.yaml, content.yaml, captures, ElevenLabs narration). Use when asked to build, record, update, or add voice-over narration to a demo scenario.
---

# Demo author

The pipeline is the same for every demo and every agent. You edit files under `scenarios/<id>/` and run
`python -m pipeline.<step>`; you never hand-write recording content, timing, audio, or captions.
The full design is `docs/demo_pipeline_architecture.md`; §0.10 covers capture and §0.11 covers narration.

## Before you start

- Run `python3 scripts/doctor.py` (add `--capture` to record). It lists missing tools with the fix for each; the root `README.md` has the full setup.
- Pick a use case from `docs/headless_use_case_matrix.md` (its Agent Skills table, §4.5, names the skill each use case stars). The **recorded** client is Cursor CLI (default) or GitHub Copilot CLI (`client.name: copilot-cli`, see below); the agent that **authors** can be any.
- The recorded client loads `search-and-dashboard-troubleshooter`, `splunkctl`, and `playwright-cli` by default. For another Splunk Agent Skill add `recording.skills: [splunk-search]` to `scenario.yaml` (names from `splunk/splunk-agent-skills`); setup reinstalls the client's skills from scratch each take.
- Stack access and tokens come from `.env` (copy `.env.example`) and a stack profile (`recording.stackProfile`); see the README. A scenario with no `captured` artifacts (`source: metadata`) is a planned demo, not a broken one.

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
4. `python -m pipeline.transcript scenarios/<id> --store <session log>` writes `artifacts/transcript.json`. The take keeps the client's log in `.captures/<id>/<take>/session/` (`store.db` for Cursor, `events.jsonl` for Copilot); `--client` defaults to the scenario's.
5. Narrate (below), if the demo is narrated.
6. `cd apps/hub && npm run build` (or `npm run dev`), then load the demo and play it through. On a fresh clone the build stops until the n8n canvas snapshot exists, because SO-08 draws a workflow: run `.captures/venv/bin/python scripts/n8n_preview_snapshot.py` once (needs Docker, about 30 MB, git-ignored).

## Design the demo before recording

These come from owner reviews; skipping them cost SO-07 a full re-record. Details: §0.10 items 19–28.

- **Story first.** Write down the situation, the pain, what gets detected, the decision, and the outcome before writing beats. The About section in `how-it-works.md` tells that story first, then the technology. Aim for 2–3 minutes published; a demo with several approvals (SO-03's notebook hunt has three) can run 3–5 minutes. Don't cut evidence to hit a length.
- **The advertised technique must find the answer.** If the title says ML, seed data where the model flags the culprit. Check the feature's distribution with a search before you fit. A model that misses on purpose is fine only as a theory the agent rules out.
- **Evidence has to be on screen.** Cursor CLI shows an MCP call as a bare tool name, and Copilot CLI collapses shell output; Ctrl+O doesn't expand it, and hints asking the agent to "show evidence" get ignored. Use several short prompts, each with `wait: turn-end`, so each turn ends with an answer (a list, a result table, the key numbers). Put `require: gate` only on the turn that writes.
- **Show the source and the proof, not only the result.** `browser.steps` puts screenshots in the pane before the final one, such as the source records the agent reads and the tool's own UI showing the key result. Copy for each step goes in `content.yaml` `browser.steps.<id>`.
- **Writes outside Splunk get a wrapper.** Copy `recorder/clients/cursor-cli/acli.tmpl`: allow-list commands, answer writes without `--yes` with a short `CONFIRMATION_REQUIRED` line (Cursor truncates long output), and deny the MCP server's write tools in the capture config.
- **SaaS data lives on a personal or demo tenant.** Scripts refuse the corporate host. Add sanitizer rules for the tenant's host, emails, account IDs, and display names before the first post.
- **Interactive logins use real Chrome.** For SSO or passkeys, follow `scripts/jira_web_login.mjs`: launch the installed Chrome with its own profile, attach over CDP, and wait for the session cookie, not a URL.

- **More than one approval:** use `gates:` instead of `gate` in `scenario.yaml` and `gates.<id>` copy in `content.yaml`; IDs can't match chapter IDs, and narration can anchor to any gate ID. Put a per-beat `evidence` on each `wait` that requires a different refusal text. See `scenarios/so-03-notebook-spray-hunt`.
- **n8n demos:** the side pane can be the real n8n canvas instead of screenshots (§0.12). Export the workflow from n8n and run `python -m pipeline.workflow scenarios/<id> <export.json>`; add `workflow: { src, steps }` to `scenario.yaml` (steps by node name, timed by chapter, gate, or seconds) and `workflow: { alt, callouts }` to `content.yaml`. Build the canvas with `.captures/venv/bin/python scripts/n8n_preview_snapshot.py` before `npm run build`; the build fails without it. Check with `apps/hub/scripts/check-workflow-pane.mjs`. A demo can have both: `browser.steps` screenshots and the canvas share the pane, and `workflow.show: { from, until }` (chapter, gate, or seconds) sets when the canvas takes it; the Slack-style final `browser.screenshot` still appears at `browser.showAt` after approval. `workflow.startedBy` (a regex on the shell command) adds the workflow's full, importable JSON to the transcript as an Artifact entry right after that command.
- **Per-take values:** `recording.vars: { NAME: <command> }` runs each command before a take and puts its output wherever `__NAME__` appears in the hints (for example a case ID no earlier take used). The values are saved in the take's `vars.json`.
- **Notebook demos:** follow "Recipe: a Machine Data Lake and Jupyter demo" below. `integrations: [notebook]` plus `recording.notebook.gated: [cell ids]` gives a gated `jpterm` (copy `jpterm.tmpl` for other gated tools). Files the agent needs in the workspace go in `fixtures.stage`, because the workspace is emptied first. A different stack uses `recording.stackProfile` and `scripts/stack_profile.py`; run any command against it with `python3 scripts/with_stack.py <profile> <command>` (splunkctl reads `SPLUNKCTL_HOST`/`SPLUNKCTL_TOKEN`, so `~/.splunkctl` stays on CO2).

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

### Recording with GitHub Copilot CLI

`client: { name: copilot-cli, label: GitHub Copilot }` in `scenario.yaml`, and the launch beat is `{ run: copilot, waitFor: "open sidebar" }`. Everything else (fixtures, hints, gates, post, narration) is the same as for Cursor. Setup and sign-in: README, "Recording with GitHub Copilot CLI".

- **The capture home** gets `~/.copilot/` (skills, `mcp-config.json` with the Splunk MCP bridge, `settings.json` with the banner off and no auto-update) and a `copilot` launcher in `~/bin`. The launcher sets the flags every take runs with: allow all tools, no `ask_user` form (it would wait for an answer and stall the take), no built-in GitHub MCP server, no mouse, and a `--deny-tool` for each line of `~/.config/copilot-deny` (the Splunk MCP write tools). The story's approvals stay the gated wrappers'. The footer still says "Manual Approval"; nothing prompts.
- **Pre-trust the workspace.** Folder trust is in `~/.copilot/config.json` (`trustedFolders`), not `settings.json`; without it the first prompt is a trust dialog. A `TERM_PROGRAM=vscode` in the environment opens a "Set up terminal" dialog; the capture shell doesn't pass it.
- **Driver cues:** ready is `open sidebar` in the footer; a turn runs while the footer shows `ctrl+c interrupt`. Two Ctrl+C presses quit and print a resume line. Startup takes 20–30 s while the Splunk MCP server connects.
- **pyte** rejected Copilot's private device status query (`CSI ? 6 n`); `ce01_drive.py` and the transcript's screen clock patch it.
- **Shell output is collapsed.** A command the agent runs shows as `$ Shell <description> N lines…` with the command under it; a failed one is one line, `✗ Shell <description> Failed with exit code N  <first output line>…`, cut at the terminal width. Use 110 columns, put the cell or object first in a refusal so the per-gate `evidence` (`CONFIRMATION_REQUIRED: cell <id>`) fits, and have the hint ask the agent to quote the refusal line. Output the person runs in shell mode (`!`) is shown in full.
- **Session log:** `~/.copilot/session-state/<id>/events.jsonl` has every message and tool call with full output and exit code; a shell-mode command is `tool.user_requested` (`local_shell`). The capture clears old sessions before a take and copies the log to `session/events.jsonl`.
- **Transcript timing comes from the rendered screen.** Copilot redraws only changed cells, so text never appears whole in the cast's byte stream; the adapter sets `SCREEN_CLOCK` and `pipeline.transcript` replays the cast with pyte.
- **Sign in with the account that has the Copilot seat.** `copilot login` takes whichever GitHub account the browser has open. Use `CAPTURE_CLIENT=copilot-cli python3 scripts/ce01_capture.py login --device-code` and approve the code in a window signed in to the work account. On a corporate network `api.individual.githubcopilot.com` (personal accounts) can be blocked while the business host answers. Before a take, run the capture home's launcher headless with `-p "<a question that needs a Splunk MCP tool>"`: it shows the model the account gets and that the MCP server connects.
- **Settings the capture home pins:** `footer.showAiUsed` and `footer.showQuota` off (the footer would show credit use in every frame), banner off, no auto-update.
- **Leave the client for full-screen or colored output.** Copilot's shell mode (`!`) prints a TUI's escape codes as text, and `euporie-preview` always writes them. End with `{ leave: true }` (quits the client, keeps recording), then a `run` beat in the plain shell, then `{ exit: true }`. The transcript adds commands run after `leave` as "You ran" entries; give the beat a `result:` line, because their output isn't in the client's log.
- **Dry runs without the Copilot service:** `COPILOT_PROVIDER_*`/`COPILOT_MODEL`/`COPILOT_OFFLINE` pass through to the capture shell. A small OpenAI-compatible fake that returns one tool call and one reply checks the whole capture (launch, a gate, shell mode, exit) in a minute; a real BYOK model gives a full rehearsal. `scripts/copilot_fake_model.py --command '<shell command>'` is that fake. Don't publish either.

### Recipe: a Machine Data Lake and Jupyter demo

SO-03 is the template; copy its pieces rather than starting over. In order:

1. **Story and data.** Write a deterministic generator (like `scripts/auth_hunt_data.py`): the same UTC day gives the same events, the answer is planted where the advertised technique finds it, and the hot index window shows only part of it, so the lake is needed.
2. **Stack** (`scenarios/so-03-notebook-spray-hunt/fixtures/MDL_SETUP.md`, about an hour with waits): index, raw table, two HEC tokens, and a one-event landing test (8–10 minutes to land).
3. **Seed** with a seeder like `scripts/seed_auth.py`: dual HEC, refuses a second load, and `--check` runs the same raw search the notebook runs. Record within the story's window (SO-03: about 4 days).
4. **Promote** the analytics table, wait for rows (about 10 minutes after "Complete"), enable Open Sharing, and put the profile path and `<share>.<schema>.<table>` in `.env`.
5. **Notebook:** `build_notebook.py` writes it from code (stable cell IDs, one `params` cell, a Markdown heading per step, no outputs); `lake.py` is the data access (raw SPL2 search, range-read shared table, `fixture` mode); `show.py` draws the results (see "Notebook output that reads well on camera"). Stage all three with `fixtures.stage`. Keep the executed notebook with `recording.keep` and publish it with `artifacts.notebooks`; the transcript shows it after the last command that ran it, cell by cell, with a download.
6. **Preview the look, then get sign-off.** Run the cells on the fixture with `nbclient` in a scratch folder, then `scripts/notebook_preview.py <executed.ipynb> --cols 100` renders it with euporie into an asciinema page; serve the folder and send the link before recording.
7. **Run it locally first, through the wrapper.** Before any take, run every cell in the capture home's environment with the capture home's `jpterm`, in the agent's order: `kernel start`, `write params`, `execute params`, each gated cell without and with `--yes`, then the closing viewer. Time each cell; one over 30 s needs the wrapper's timeout. SO-03 lost take 1 to a cell that had only ever run through Python's `exec`, never through `jpterm`.
8. **Takes**, then post (holds, and the notebook pane), transcript, narration, the hub check, and a PR.

### Lessons from SO-03 (Machine Data Lake, Jupyter, Open Sharing)

Setup sheet: `scenarios/so-03-notebook-spray-hunt/fixtures/MDL_SETUP.md` (every step checked on the MDL stack, Splunk Cloud 10.8).
The 10.8 MDL docs block plain fetches (403); `curl` with a browser user agent or the Firecrawl CLI (`npx -y firecrawl-cli scrape <url> --only-main-content`) reads them.

**Landing data in the lake**
- **Direct HEC is the simple route; no Edge Processor or landing pipeline needed.** An HEC token whose default and only allowed index is `~.federated.<raw_table>` writes straight to the raw table. For the same events in a Splunk index too, send them a second time with an index token (the docs' "two-request model"). Don't use the landing definition's *Divert* or *Duplicate* for this: it pulls events that are already going to an index.
- **The raw table's landing definition still applies to direct HEC.** A "Keep data where …" action in it filtered our direct-HEC test events out. Leave the landing definition with one partition that matches nothing in your indexes and no actions.
- **Landing takes 8–10 minutes.** A test event sent with `mdl_test_id=<unique>` showed up in raw search only after about 8 minutes; wait at least 10 before deciding it was lost. Lost events would be in `lastchanceindex`.
- **The Splunk Cloud HEC gateway can answer `502` mid-load.** The batch wasn't accepted; resend it (`seed_auth.py` retries 5xx). A seeder that is deterministic per UTC day can resume from the count already indexed.
- **Set raw table retention longer than the oldest seeded event,** or the lake drops it on arrival. Static promotion limit at least the analytics window; the volume limit only matters above it.

**Searching the lake from code**
- Raw tables aren't classic indexes: `search index="~.federated.x"` and `| from federated:x` return nothing. They're SPL2 datasets. Dispatch SPL2 to the search head's `POST /services/search/v2/jobs` with `search=| @spl2 from <raw_table> | where like(_raw, "%…%")`; poll `/services/search/v2/jobs/<sid>` and page `/results`. Raw tables expose only `_time`, `_raw`, `host`, `source`, `sourcetype`: filter on text and parse `_raw` yourself. This is the Catalog's "Search", and it needs no SCS token.
- An analytics table is searched with `| @spl2 search index=<analytics_table>`.
- An `sc_admin` REST token can query everything above. Expect a message saying the search runs on an MDL raw dataset; it isn't an error.
- **A search can come back partial without a warning.** Once, one indexer dropped out and `search/jobs/export` counted 1,365 of 16,634 events; `tstats` and a rerun 20 s later were complete. Pre-flight checks retry before failing (`seed_auth.py --check` tries three times).

**Promoting to an analytics table**
- No props/transforms exist for a custom sourcetype, so the **Promote fields** dialog lists only raw fields as "unavailable". Ignore it: the schema comes from the SPL2 editor. Put the extraction inside `process_data` after `return from $source`:
  `| rex field=_raw /k1=(?P<k1>\S+) …/ | fields _time, k1, …`. The preview's **Fields** panel must list your columns before you click Next.
- The review page can say "Selected fields: host, source, sourcetype, _raw, _time" and "Estimated promotion volume 0 B". It still promotes. The table kept `host`, `source`, `sourcetype`, and an empty `_raw` next to the extracted columns; read only the columns you need.
- **A completed promotion can look empty for about 10 minutes.** Search and Open Sharing both returned 0 rows right after "Complete"; the rows appeared about 9 minutes later. Wait before deleting or re-promoting.

**Open Sharing (Delta Sharing) with pandas**
- Enable sharing on the **analytics table**, not the raw table. The downloaded profile is a secret: keep it outside the repo with `chmod 600`, and point `.env` at its path. The table name is `<share>.<schema>.<table>`; list it with `delta_sharing.SharingClient(profile).list_all_tables()`. The share name contains the stack name, so it stays in `.env`.
- **`delta_sharing.load_as_pandas` is far too slow for MDL tables.** Every Parquet file MDL writes holds about 6 MB of bloom filters (1 MB per string column) even when it has 4 rows: a 104,000-row table was 112 files and 706 MB and didn't load in 20 minutes. List the files with the client, then read each file's footer and only the needed column chunks with HTTP range requests, 16 in parallel, with retries (S3 drops reused connections). See `load_shared()` in `scenarios/so-03-notebook-spray-hunt/fixtures/lake.py`: 72 s for the whole table. `limit=` on `load_as_pandas` is fine for a sample.
- Profiles expire (the default is 14 days). Re-enabling sharing or recreating the table means downloading a new profile.

**Jupyter in a recording**
- Pin every notebook package (`recorder/notebook/requirements.txt`). Output that viewers see changes between releases: an unpinned `plotext` dropped `clear_figure`, which broke a cell. Test cells with `uv run --with-requirements recorder/notebook/requirements.txt` before recording.
- The agent runs cells only through the gated `jpterm` wrapper. Don't give the recorded client a Jupyter MCP server or notebook skills (`jupyter-notebook`, `pandas`); they let it edit or run cells around the gates. Use them while authoring.
- **jpterm 0.3.13** is pinned; 0.4.0 moved to a new CLI and rendering framework, so upgrade only on purpose and rerun the local check. Its `--help` is the reference; the docs site says little about the CLI.
  - `jpterm execute NB --cell ID` stops after **30 s** by default (`--timeout`) with "Timed out executing notebook". The wrapper adds `--timeout 600` unless one is given.
  - `jpterm write NB --cell params --source '…'` only saves the cell; it doesn't run it. The hint tells the agent to execute `params` right after.
  - `jpterm show NB --cell ID` prints a cell without running it. Allow it, or the agent reads the notebook JSON with `python3`.
  - The wrapper lets `--help` through. When a command fails the agent reads it; a refused `--help` left take 1's agent guessing.
- **The notebook pane** (`notebookPane: { notebook, cast, cols }` in `scenario.yaml`) shows the notebook beside the terminal, cell by cell, time-synced with the main player. The jpterm wrapper logs every `write` and `execute` with wall-clock start and end and a copy of the notebook after it (`~/.cache/jpterm-trace`, outside the workspace); capture copies that to `<take>/notebook-trace`, the driver writes cast t=0 to `<take>/clock.json`, and `pipeline.post` renders each state with euporie into `artifacts/notebook.cast` plus a frame index (`notebook.json`). Every frame is a real saved notebook; a running cell shows `[*]`. The hub pane never plays: it seeks to the main clock, scrolls to the cell, and has **Whole notebook** and fullscreen. Its header is the notebook name; the terminal's is "zsh — <client>" (`terminal.title` overrides).
- **The closing shot is `euporie-preview` in the plain shell** (after a `leave` beat for Copilot). It prints the whole executed notebook, and the last cell's output stays on screen. Its wrapper forces `--color-depth 24`, because euporie drops to monochrome when stdout isn't a terminal.
- **euporie sizes its page from the terminal on stderr** and uses 80 columns when there is none, even with `--max-notebook-width`. `COLUMNS` doesn't help; `pipeline/notebook_pane.render` gives stderr a pseudo-terminal of the wanted width.
- **When the lake is down, record on the fixture only with disclosure.** On SO-03's take 4 both the SPL2 raw search (`CONNECT.PLUGIN_RUNTIME_ERROR … LeapfrogLogger` in `search.log`) and Open Sharing (500) failed on the stack side for hours. `setup.sh fixture` checks the hot index only, and `stage.sh fixture <seed day>` builds the same story in memory, anchored to the seeding day so its numbers line up with the live hot index. The setup cell prints "lake: fixture" and the agent repeats it; say so in `capture.notes`, `how-it-works.md`, and a narration line. Re-record against the lake when it's back.

**Notebook output that reads well on camera**
- asciinema can't show images, so charts are text: plotext with `theme("clear")` (bar colours, no background fill), sized to the output area (about `cols - 12`). Matplotlib through `timg` renders as blurry blocks.
- Keep code cells plain hunt code and put presentation in a helper module (`show.py`): `result` (teal), `alert` (red), `note` (grey), a table with marked rows, and the charts. Plain ANSI text works everywhere: jpterm's output to the agent, euporie, the cast, and the transcript (which strips the codes). No emoji and no HTML or CSS boxes.
- One colour per meaning across every cell: red for the suspect and the breach, amber for "only in the lake" and the skipped false positive, teal for results and thresholds, grey for everything else.
- plotext misapplies per-bar colour lists on horizontal bars and dense bars. Draw one `bar` call per colour, or draw a horizontal ranking yourself with `█`.
- `seed_auth.py --check` must print `story present` before each take (`fixtures.setup` runs it). The story is anchored to the seeding day, so a take has to happen within about 4 days of seeding.

### Post, transcript, narration, and deploy (learned on SO-03)

- **Holds for Copilot use `settle: 0.06`.** A hold normally waits for a 0.3 s pause before freezing. Copilot's spinner ticks every 90 ms, so that pause never comes and the hold lands after the text has scrolled away. `immediate: true` can freeze a half-drawn message (Copilot draws one in writes about 35 ms apart). `settle: 0.06` freezes at the first gap after the message is drawn. Check each hold frame with pyte before narrating.
- **Holds apply in order.** One whose text never matches blocks every hold after it, and post prints "never applied". Match plain words: Copilot renders inline code with spaces around it, so avoid code spans in hold patterns.
- **Compression follows the noise list in `pipeline/post.py`.** A client whose spinner isn't on it never gets its waits cut. Copilot's (`◉ ◎ ○`, a blinking `●` before "Working" or "Running", the byte counter) is on it now. With it, SO-03 went from 5:00 to 2:27, and the holds brought it to 3:00 for the narration.
- **Gate times sit on the agent's question,** about 0.3 s before the next chapter, not on the first refusal line: the pause then shows the refusal, the exact command, and "Approve?". Give each gate a `summary` for its transcript chapter ("Searching the lake stopped at …"); the default says "The write stopped", which is wrong for a read.
- **Narration tooling:** final audio comes from `pipeline.narrate` (ElevenLabs CLI; check `elevenlabs auth status`). The ElevenLabs MCP transcribes flow assets and otherwise opens a file picker, so the listen-back uses `elevenlabs speech-to-text convert`. Real clips run 0.5–1.5 s longer or shorter than `--estimate`; trim words or move a start and rerun (clips are cached).
- **End with the value.** For a hunt, the last two lines say what each part buys: the hot index stays fast, the lake keeps history cheaply, and the agent turns that history into a tested detection with a person approving each costly step.
- **The hub has no formatter.** Don't run Prettier on `apps/hub`: its defaults rewrote whole files. Edit by hand and run `npm run lint`, `npx tsc -b`, and `npm run build`.
- **Deploy:** a merge to `main` deploys only when the repo has `CLOUDFLARE_API_TOKEN` (an account token from the Edit Cloudflare Workers template, with the custom domain's zone) and `CLOUDFLARE_ACCOUNT_ID`. Check an account token with `GET /accounts/<id>/tokens/verify`; it answers 401 on `/user/tokens/verify`. After setting the secrets, `gh run rerun <id> --failed` deploys the commit that was already tested.

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
