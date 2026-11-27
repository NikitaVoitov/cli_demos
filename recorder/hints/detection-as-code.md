## Detections as code

Today you work on the SOC's detections, not the checkout service. The team keeps its Splunk Enterprise Security detections in the Git repo `./acme-detections` (on GitHub; `gh` works for that repo only). Read `acme-detections/AGENTS.md` first and follow it exactly: it says how a SigmaHQ rule becomes a detection, how tests and tuning work, and how changes ship.

- In this demo nothing changes Splunk from this machine: no `splunkctl` writes. Read Splunk with the Splunk MCP Server tools. A detection reaches Enterprise Security only when its pull request is merged; the `deploy` workflow installs it.
- ES detections are saved searches. Find ESCU's with `splunk_get_knowledge_objects` or a `| rest /servicesNS/-/-/saved/searches` search, and read each one's SPL and macros before saying what it catches.
- Real attack data for T1003.001 (Splunk attack_data, Atomic Red Team run, Sysmon) is in `./attack_data/T1003.001-windows-sysmon.log`, one XML event per line. Build `match` cases from its EventID 1 events, and craft variants by changing only the CommandLine of a real event.
- Run `contentctl build` and `python ci/check_sigma.py` in the repo before you push.
- Branch from `main`, commit, `git push`, then `gh pr create --base main --fill`. Wait for CI with `gh pr checks <number> --watch --interval 15`, then read the report CI posts on the pull request: `gh pr view <number> --comments`. The newest comment is the current run.
- Merging deploys to production, so `gh pr merge` stops with `CONFIRMATION_REQUIRED`. Never add `--yes` on your own: quote the `CONFIRMATION_REQUIRED` line, show me the command, and wait for my approval; then rerun exactly that command with `--yes`. Merge with `--squash --delete-branch`.
- After the merge, follow the deploy: `gh run list --workflow deploy --limit 1`, then `gh run watch <id> --exit-status`. Then confirm with the Splunk MCP tools that the detection is enabled, scheduled, and a correlation search, and run it once with `splunk_run_query`: `| savedsearch "<detection name>" earliest=-24h latest=now`.

## Show your evidence

The terminal collapses command output, so whoever watches only sees what you write. After each step, write a short message before your next tool call, under 10 lines, with a small table where it helps:

- Coverage: which detection exists, whether it is on, what its SPL requires, and the variants it would miss.
- The draft: the detection's name, MITRE technique, risk score, and each test case with what it should do.
- CI: each check's result, the test table (ESCU vs ours), the noise count, and what the AI triage said about it.
- Tuning: the exact exclusion and why it is narrow, and the new CI result.
- Deploy: the workflow result, the detection's state in Splunk, and what the run found.
