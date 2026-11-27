# SO-05 setup: stack, GitHub repo, and capture home

Everything below was done once on the CO2 stack (Splunk Cloud 10.5, ES 8.6.1, ESCU 6.11.1, AI Toolkit 6.2.0) and the
private demo repo. Values live in `.env` (keys in `.env.example`, SO-05 block) and in the repo's Actions secrets.

## 1. Splunk (the ES search head)

- **Apps:** Enterprise Security, ESCU (its `ESCU - Dump LSASS via comsvcs DLL - Rule` stays off), Splunk Add-on for
  Sysmon (parses `XmlWinEventLog` into the Endpoint data model), CIM (`cim_Endpoint_indexes` left as `()`).
- **Indexes** (cluster manager): `dac_ci` for CI's replayed tests and `demo_endpoint` for the week of endpoint data.
- **HEC token** `dac_ci_hec` with `index = dac_ci`, `indexes = dac_ci,demo_endpoint`, `useACK = 0`. On this clustered
  stack it must be a cluster-manager bundle app (`<manager-apps>/hec_dac_ci/local/inputs.conf`, then
  `splunk apply cluster-bundle`); tokens made with ACS or Splunk Web return 403 Invalid token. A bundle push delays
  indexing for several minutes. `.env`: `SPLUNK_HEC_TOKEN_DAC`.
- **CI reader:** role `dac_ci_reader` (imports `user`; search and default indexes `dac_ci`, `demo_endpoint`;
  `apply_ai_commander_command`, `list_ai_commander_config`, `list_storage_passwords`; 10 concurrent searches), user
  `dac_ci_reader`, and a 90-day token: `SPLUNK_CI_READ_TOKEN`. The `ai` command must read the LLM connection's key,
  hence `list_storage_passwords`; on this stack that also lets the token read the other secrets shared with everyone.
- **Deploy token:** a 90-day token for the admin user: `SPLUNK_CI_DEPLOY_TOKEN`. CI creates the app
  `DA-ESS-DaC-Demo` if it is missing.
- **AI Toolkit:** the `azure_gpt_5` LLM connection (Azure OpenAI), readable by everyone.
- **Data:** `python3 scripts/seed_endpoint.py` (14 nights; reruns fill only missing nights), then `--check`.

Not used yet: Detection Studio. Its library is empty on CO2 because `dlx-app` gets "SCS Token not found" from
`/services/authorization/scs_tokens/dlx` (the stack is not provisioned for SCS service tokens). Staging ACS returns
500 on private app installs, so CI deploys over REST instead of `acs apps install`.

## 2. GitHub

- Private repo `DAC_DEMO_REPO`. Its baseline is `fixtures/dac-repo/` pushed to `main` and tagged `baseline`
  (re-tag after changing the template).
- Actions secrets: `SPLUNK_MGMT_URL` (the ES search head's management URL), `SPLUNK_HEC_URL`, `SPLUNK_HEC_TOKEN_DAC`,
  `SPLUNK_CI_READ_TOKEN`, `SPLUNK_CI_DEPLOY_TOKEN`; optionally `SPLUNK_COM_USERNAME`/`SPLUNK_COM_PASSWORD` to run
  AppInspect. GitHub-hosted runners reach the stack's management port and HEC without an allowlist.
- A fine-grained token for the capture home, limited to this repo: Contents and Pull requests read/write, Actions
  read/write (the reset dispatches `deploy`). `.env`: `GH_TOKEN_DAC_DEMO`.

## 3. Capture home

`recording.integrations: [github]` runs `scripts/ce01_capture.py github`: the gated `gh` (only this repo;
`gh pr merge` held until `--yes`; no settings, secrets, or API writes), a git credential helper with the token, and
`sigma`/`contentctl` from a pinned environment (`fixtures/dac-repo/requirements.txt`).

## 4. Before each take

`fixtures.setup` tops up the endpoint data and runs `fixtures/repo.py reset`: closes open pull requests, deletes
branches, moves `main` to `baseline`, and runs `deploy`, which removes the previous take's detection from ES. It
then checks ES holds exactly the baseline. `fixtures.stage` clones the repo into `~/payments/acme-detections`.

Expect a take to run 20 to 30 minutes: CI waits for the stack to index the replayed events (1 to 7 minutes per run).

## 5. After a take, before the next reset

1. Note the pull request number and the three run IDs (`gh run list`): the `validate` run that failed on noise, the
   green one after tuning, and the `deploy` run. Put the run IDs in `post.holds` (`ci-run`, `green-run`, `deploy-run`
   match `gh run watch <id>` on screen), then run `pipeline.post`.
2. `.captures/venv/bin/python scenarios/so-05-sigma-detection-as-code/fixtures/artifacts.py <pr>` publishes the
   files the transcript shows: the Sigma rule, detection, tests, tuning macro, the correlation search contentctl
   builds, both workflows, and both CI reports.
3. `node scripts/github_web_login.mjs` once (a real Chrome window; sign in to GitHub), then
   `node scenarios/so-05-sigma-detection-as-code/fixtures/screenshots.mjs github <pr> <failed-run> <green-run> <deploy-run>`
   for the three Actions runs and CI's report on the pull request. Refresh the Splunk Web session
   (`cd apps/hub && node ../../scripts/splunk_web_login.mjs`), then `screenshots.mjs es` for Content management and
   the detection's search in the ES editor.
4. Set the chapter, gate, browser step, and narration times from `pipeline.post`'s output, then run
   `pipeline.transcript` and `pipeline.narrate`.
