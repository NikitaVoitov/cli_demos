# SO-08: the n8n containment workflow

After the analyst approves, Cursor CLI runs the gated `n8n-contain` wrapper, which calls the n8n workflow
**Closed-loop phishing containment** on the demo n8n Cloud instance (`N8N_URL` in `.env`). The workflow source is
`fixtures/contain-phishing.workflow.ts` (n8n Workflow SDK); the hub draws its sanitized export
(`python -m pipeline.workflow`) on the real n8n canvas.

```text
Start containment ─┬─ Purge email from inboxes ─┬─ Wait for results ── Notify analyst in Slack
  (webhook, called  └─ Block sender domain ───────┘   (merge, 2 inputs)     (#phishing-response)
   by Cursor CLI)
```

The two containment steps are simulated. Each is an HTTP Request that writes the audit record the real system
would emit to Splunk HEC as `sourcetype=containment:audit`: one `message_purged` per mailbox and one
`domain_blocked`, both with the case ID. That is what the triage agent's verify
step reads. Say so on the demo page.

## What exists

| Piece | Where |
|---|---|
| Workflow | n8n, personal project, "Closed-loop phishing containment" |
| Credential "Cursor CLI webhook" | header `X-Demo-Token`; its value is `N8N_WEBHOOK_TOKEN` in `.env` |
| Credential "Splunk HEC (MDL demo_soc)" | header `Authorization: Splunk <SPLUNK_HEC_TOKEN_MDL>`; the HEC address is set on the two HTTP nodes in n8n only |
| Wrapper | `recorder/clients/cursor-cli/n8n-contain.tmpl`, installed by `python3 scripts/ce01_capture.py n8n` |
| Slack channel | `#phishing-response` in the personal soc-team workspace |
| Slack bot | "SOC Automation" app, `fixtures/slack-app.manifest.json`; the Slack step has the n8n footer link off so the instance hostname never shows |

The demo runs on the MDL stack: the n8n credential "Splunk HEC (MDL demo_soc)" holds `SPLUNK_HEC_TOKEN_MDL`, a
token whose index is `demo_soc`, so the records land next to the story data and the agent searches
`index=demo_soc sourcetype=containment:audit case_id=<case>`. Moving to another stack means a new HEC credential
and the address on the two HTTP nodes. splunkctl reaches MDL through `python3 scripts/with_stack.py mdl …`
(the profile from `python3 scripts/stack_profile.py init mdl`), so `~/.splunkctl` stays on CO2.

## Before the first real run

1. **Slack bot:** create the "SOC Automation" app in the soc-team workspace from
   `fixtures/slack-app.manifest.json` (api.slack.com/apps > Create New App > From a manifest), then
   **Install to Workspace**. Put its Bot User OAuth Token (`xoxb-…`, from OAuth & Permissions, not the
   `xapp-` app-level token) in `.env` as `SLACK_XOB_TOKEN`.
   No channel invite is needed: `chat:write.public` lets the bot post to public `#phishing-response`.
   Don't use n8n's one-click Slack OAuth: the node then posts with your user token, so the notice comes from
   you and Slack doesn't alert you.
2. **n8n credential and publish:** create a Slack "Access Token" credential "Slack SOC Automation bot" from
   `SLACK_XOB_TOKEN` (public API), attach it to **Notify analyst in Slack**, and publish. n8n refuses to
   publish until the Slack credential is set. The production webhook is `<N8N_URL>/webhook/contain-phishing`.
3. **Test** with a throwaway case, which the verify step never matches:

```sh
python3 scripts/ce01_capture.py setup && python3 scripts/ce01_capture.py n8n
HOME=/Users/Shared/splunk-demo /Users/Shared/splunk-demo/bin/n8n-contain --case TEST-0002 \
  --message-id '<test@example.com>' --domain test.example --recipients probe@acme-corp.example --yes
```

Expected: one line, `Contained TEST-0002: purged 1 mailboxes, blocked test.example; analyst notified in Slack`, a
Slack message in `#phishing-response`, and two `containment:audit` events for TEST-0002 in Splunk.

## In the take

```sh
n8n-contain --case PH-1042 --message-id '<88213.ap-notices@northwind-billing.example>' \
  --domain northwind-billing.example --recipients <14 mailboxes>
```

Without `--yes` it prints `CONFIRMATION_REQUIRED` and runs nothing: that is the approval gate
(`recording.gateEvidence: CONFIRMATION_REQUIRED`). With `--yes` it waits for the workflow to finish and prints
the result. The canvas starts animating at that call.
