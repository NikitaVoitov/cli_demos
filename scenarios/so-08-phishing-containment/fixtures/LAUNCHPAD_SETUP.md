# SO-08: the PhishingTriageAgent agent in Agent Launchpad

Cursor CLI runs this agent with `| aiagent` through splunkctl twice: once to triage the reported email, once after
containment to confirm it worked. It uses splunkctl, not Splunk MCP, because a run takes about a minute and Cursor
CLI gives up on an MCP call sooner. The agent itself only reads Splunk, through its own Splunk MCP connection;
containment goes through n8n. It lives on the MDL stack (AI Toolkit 6.2.0). The data comes from
`scripts/seed_phishing.py`.

Field names below follow the AI Toolkit 6.2.0 docs,
[AI Toolkit Agent Launchpad](https://help.splunk.com/en/splunk-cloud-platform/apply-machine-learning/use-ai-toolkit/6.2.0/ai-toolkit-connections-containers-and-agents/ai-toolkit-agent-launchpad).

## Before you start

- **LLM connection** (AI Toolkit > Connections): OpenAI, Anthropic, Azure OpenAI, Amazon Bedrock, or Splunk
  hosted models. Custom LLM and Ollama connections don't work with Agent Launchpad.
- **Capability:** adding an MCP connection needs `edit_agent_connections` (the `mltk_admin` role has it).
- **Data:** index `demo_soc` on MDL with the seeded story, and the n8n HEC token writing `containment:audit` into
  the same index. `python3 scripts/with_stack.py mdl python3 scripts/seed_phishing.py --check` prints
  `story present`. Reseed within about 5 days of a take, and regenerate the report email with it:
  `python3 scripts/seed_phishing.py --report-eml .captures/so-08-phishing-containment/setup/phishing-report.eml`,
  then drag the file onto the demo-soc "Phishing reports" folder in Outlook for Mac and delete the old one.

- **Splunk MCP Server guardrails** (MCP Server app > Guardrails, admin only), only for calling the agent from an
  MCP client: `splunk_run_query` refuses commands outside its allowlist (`Forbidden command found: aiagent`), so
  add `aiagent` under Allowed SPL commands. On a shared stack this applies to every MCP user.

## Create settings

| Field | Value | Why |
|---|---|---|
| Agent name | `PhishingTriageAgent` | Letters and numbers only |
| Description | Triages a reported phishing email from Splunk data and confirms containment afterwards. Read-only. | Max 500 characters |
| LLM connection | `azure_gpt_5` (Azure OpenAI, deployment `gpt-5`) | The same Azure OpenAI resource the CO2 stack's AI Toolkit uses; created on MDL through AI Toolkit's `mltk/aicommander` REST endpoint, not the stack default |
| LLM temperature | `1` | GPT-5 is a reasoning model and accepts only its default temperature |
| Max tokens | `16000` | GPT-5 counts its reasoning toward this limit, so 5000 can cut an answer short |
| Reasoning effort | `Low` (try `None`) | The searches come ready in the prompt, so the model only fills in values and summarizes |

## Edit agent settings

**Default prompt** (used when `| aiagent` runs without `prompt=`; Cursor CLI always passes one, so this is the
fallback for a manual run):

```text
Triage the most recent email that an employee reported to security@acme-corp.example in the last 7 days.
Find who received it, who clicked its link, whether anyone submitted credentials, whether any payload ran,
and whether there were follow-on sign-ins. Then recommend what to contain.
```

**System prompt** (paste as written). Each task is one search the prompt hands over ready to run, so a run is
one tool call and one model turn, and every take follows the same pattern:

```text
You are a SOC triage agent for a phishing investigation. You only read Splunk with the splunk_run_query tool.
You never contain, block, delete, or change anything. Data: index=demo_soc, last 7 days. Find the campaign by
sender domain, never by subject (punctuation differs). Each task is ONE search: run it once, then answer.
Run another search only if it fails.

TRIAGE (replace <domain> with the sender's domain, all three places):
| multisearch [search index=demo_soc sourcetype=email:gateway earliest=-7d sender_domain="<domain>"]
 [search index=demo_soc sourcetype=proxy:web earliest=-7d domain="<domain>"]
 [search index=demo_soc sourcetype=endpoint:process earliest=-7d parent_process="msedge.exe" [search index=demo_soc
  sourcetype=proxy:web earliest=-7d domain="<domain>" | stats count BY user | fields user]]
 [search index=demo_soc sourcetype=identity:signin earliest=-7d [search index=demo_soc sourcetype=proxy:web
  earliest=-7d domain="<domain>" | stats count BY user | fields user]]
| eval part=case(sourcetype=="email:gateway","A recipients", sourcetype=="proxy:web","B clicks",
  sourcetype=="endpoint:process","C payload", true(),"D signins"),
  who=case(part=="A recipients","all", part=="D signins",user." ".src_ip, true(),user." ".device)
| stats dc(recipient) AS recipients values(spf) AS spf values(dkim) AS dkim values(dmarc) AS dmarc
  values(http_method) AS methods values(process) AS processes count values(country) AS country
  values(result) AS result values(mfa) AS mfa min(_time) AS first_seen BY part who
| eval first_seen=strftime(first_seen, "%Y-%m-%d %H:%M %Z")
Read it as: A = recipients and SPF/DKIM/DMARC. B = users who clicked (who = user and laptop); POST in methods
means a form was submitted, possible credential entry. C rows = something the browser started; no C rows means
no payload ran. D = sign-ins per user and IP; an IP with few sign-ins, first seen after that user's click, is new.
Report its country, result, and MFA outcome: a failed sign-in with MFA denied is an attempt, not a login.

VERIFY (replace <case>, <domain>, and <ip>, the attacker IP):
search index=demo_soc sourcetype=containment:audit case_id="<case>" | stats min(_time) AS at count BY action
| eval part="E actions"
| append [search index=demo_soc earliest=-7d ((sourcetype=email:gateway sender_domain="<domain>" action=delivered)
  OR (sourcetype=containment:audit case_id="<case>" action=message_purged)) | eval mailbox=coalesce(target, recipient)
  | stats values(sourcetype) AS seen BY mailbox | where mvcount(seen)=1 AND seen="email:gateway"
  | stats count AS still_holding | eval part="F mailboxes"]
| append [search index=demo_soc earliest=-7d ((sourcetype=proxy:web domain="<domain>") OR
  (sourcetype=identity:signin src_ip="<ip>")) [search index=demo_soc sourcetype=containment:audit case_id="<case>"
  | stats min(_time) AS earliest | return earliest] | stats count AS events_after_containment
  | eval part="G after containment"]
| eval at=strftime(at, "%Y-%m-%d %H:%M %Z")
Containment is complete only if still_holding is 0 and events_after_containment is 0; otherwise say what is
still open.

Answer in short lines with the numbers, times as shown. Triage: recipients and authentication, users who
clicked, form submissions, payload, follow-on sign-ins, and a recommendation (purge the email from every
mailbox, block the sender domain; name the users to follow up). Verify: mailboxes still holding it, activity
after containment, the containment actions with times, and whether containment is complete. Don't repeat the
SPL; it is in the run history.
```

**LLM connection:** the same connection as above.

**MCP connections:** add the Splunk MCP connection for this stack, then in its Tools list:

| Tool | Available | Approval setting |
|---|---|---|
| `splunk_run_query` | yes | Approval not required (it only reads) |
| `splunk_get_info`, `splunk_get_indexes`, `splunk_get_index_info`, `splunk_get_metadata` | no | The searches are in the prompt; these only invite exploring the stack |
| `search_create_splunk_alert`, `search_record_containment_action` | **no** | These write; the agent must not have them |
| `saia_*` tools | no | They hand the question to another assistant; the demo shows this agent's own searches |
| everything else | no | Not needed |

If tool calls fail to connect, the stack's API allowlist may be missing the Agent Launchpad IP for its AWS region
(the docs list one IP per region under "Supported regions and IPs to allowlist").

**Knowledge bases:** none. The system prompt carries the data guide.

**Agent skills:** none.

**Invocation configurations:**

| Setting | Value | Why |
|---|---|---|
| Agent timeout duration | `450` (default) | A run takes about a minute; splunkctl waits up to its `--max-time` (300 s in the hint) |
| Max invocations per command | `1` | `aiagent` runs once per search result; Cursor CLI always sends one row, and 1 stops an accidental multi-row run from calling the model 10 times |

No alert or saved search triggers this agent; Cursor CLI calls it with `| aiagent` through splunkctl.

Agents are private by default, which is fine: the Splunk MCP user that Cursor CLI uses is the agent's owner.

## Try it

In Search (the docs note `aiagent` raises a safeguard warning there; select Run Query Anyway), then the same text
through Cursor CLI:

```spl
| makeresults | aiagent agent_name="PhishingTriageAgent" prompt="Triage the phishing email reported by Dana Lee: sender ap-notices@northwind-billing.example, link https://northwind-billing.example/portal/inv/88213."
```

Expected: 14 recipients (the finance list), SPF and DMARC fail, a domain first seen at delivery; 3 clicked
(mark.chen, priya.shah, tom.alvarez) and priya.shah posted to /portal/verify; no payload; one sign-in as
priya.shah from 198.51.100.77 (NL) denied by MFA. Recommendation: purge 14 mailboxes, block
northwind-billing.example, and follow up with the 3 users who clicked.

The verify prompt only makes sense once the n8n containment run has written its `containment:audit` records:

```spl
| makeresults | aiagent agent_name="PhishingTriageAgent" prompt="Verify containment for case PH-1042: sender domain northwind-billing.example, attacker IP 198.51.100.77."
```

Each run appears under AI Toolkit > Agents > Agent run history, with the tools it called in order.

## If creating an agent fails with "SCS Token not found"

"Error creating agent. Internal Server Error occurred." with this in `index=_internal source=*mlspl.log`:

```text
RuntimeError: Failed to fetch SCS token: HTTP 400 Bad Request -- SCS Token not found
```

AI Toolkit fetches a Splunk Cloud Services token before it saves any agent, so the agent's name and settings are
never reached. The stack has no SCS token for AI Toolkit: its link to a provisioned SCS tenant, or AI Toolkit's
activation on that tenant, is missing. The stack's admin UI can't fix this; the stack's owner, Splunk Cloud ops,
or Support has to check it. This is why the agent moved from the CO2 stack to MDL.
