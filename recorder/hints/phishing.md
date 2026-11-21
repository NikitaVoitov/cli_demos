## Phishing reports

Employees forward suspicious email to the security inbox. Read it with the Outlook MCP tools only: `list_mail_folders`, then `list_mail_messages` with the "Phishing reports" folder id, then `get_mail_message` for the newest one. The forwarded original (sender, link, message ID) is in the body.

## Splunk Agent Launchpad

The SOC's triage agent in Splunk is `PhishingTriageAgent`. It searches Splunk itself; you only start it and read its answer. Run it with splunkctl, never with Splunk MCP (an agent run takes over a minute, longer than an MCP call can wait):

```
splunkctl search '| makeresults | aiagent agent_name="PhishingTriageAgent" prompt="<task>" | table status result_1' --max-time 300 -o json
```

- Triage task: `Triage the phishing email reported by <reporter>: sender <sender address>, link <link>.` Name the sender, never the subject.
- Verify task: `Verify containment for case <case>: sender domain <domain>, attacker IP <ip>.`
- The answer is in `result_1`. If `status` is `error`, run the same command once more.
- Searches without write commands run straight away; don't add `--yes`.

## Containment

Containment runs in n8n through `n8n-contain`, which waits for approval the same way splunkctl does. Use case ID __CASE_ID__.

1. Get the mailboxes to purge with one search: `splunkctl search 'index=demo_soc sourcetype=email:gateway sender_domain="<domain>" action=delivered | stats values(recipient) AS r | eval r=mvjoin(r, ",")' --max-time 120 -o json`
2. Run `n8n-contain --case __CASE_ID__ --message-id '<message id>' --domain <domain> --recipients <comma-separated mailboxes>` without `--yes`. It prints `CONFIRMATION_REQUIRED` and exits; that on-screen refusal is when you ask me. Never add `--yes` on your own.
3. Only after I approve, rerun exactly that command with `--yes`. n8n purges the email, blocks the domain, and posts the result to Slack.

## Show your evidence

The terminal hides tool results, so whoever watches only sees what you write. After each step, write a short message before the next tool call:

- The report: who reported it, the original sender, subject, and link, in 3 lines.
- The agent's triage: recipients and authentication, who clicked, form submissions, payload, follow-on sign-ins, each on one line with the numbers, then your recommendation.
- The agent's verify: mailboxes still holding the email, activity after containment, and whether containment is complete.

Keep each message under 8 lines.
