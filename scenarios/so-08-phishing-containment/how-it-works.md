## About

Dana in Finance gets an "overdue invoice" email from a billing company she has never heard of. The link asks her to sign in to see the invoice. She forwards it to the security inbox and moves on. Thirteen of her colleagues got the same email, and not all of them were as careful.

Triage like this is slow by hand: one search for who received the message, another for who clicked, another for what ran on their laptops, and another for strange sign-ins. Each hour of delay is another chance for someone to type their password into the fake portal.

In this demo the analyst gives Cursor CLI the report. Cursor reads Dana's email through Outlook and hands the case to a triage agent built in Splunk Agent Launchpad. The agent searches Splunk itself: 14 people received the email, SPF and DMARC failed, and the sender's domain had never been seen before. Three people clicked, one of them submitted the portal's form, and about 40 minutes later someone tried to sign in as her from the Netherlands, stopped only by MFA. No payload ran.

Cursor recommends purging the email and blocking the domain, and starts an n8n workflow to do it, after your approval. n8n reports back in Slack, and the same Launchpad agent then confirms in Splunk that no mailbox still holds the email and nothing touched the domain since. Splunk finds the threat, n8n acts on it, and Splunk proves the fix held.

### What it uses

The Outlook MCP lets Cursor read the security inbox. Splunk Agent Launchpad, part of the Splunk AI Toolkit, runs the triage agent inside Splunk, and Cursor starts it with splunkctl. Containment runs in an n8n workflow that only starts after your approval, and posts its result to Slack. In this demo the workflow's purge and block steps write the audit records a mail system would, so Splunk can verify them. The Transcript tab shows the workflow's full n8n JSON under the containment command, ready to import into your own n8n. The data, mailboxes, and domains are synthetic.

### Prerequisites

- **Splunk Cloud** stack with the **Splunk AI Toolkit** and **Agent Launchpad**
- **Splunk MCP** app (the agent's searches) and **splunkctl**
- **n8n** workflow with a webhook trigger, and a **Slack** app for the notice
- **Outlook** mailbox for reports, read through the **Outlook MCP**
- **Cursor CLI**

### Learn more

- [AI Toolkit Agent Launchpad](https://help.splunk.com/en/splunk-cloud-platform/apply-machine-learning/use-ai-toolkit/6.2.0/ai-toolkit-connections-containers-and-agents/ai-toolkit-agent-launchpad)
- [Splunk MCP on Splunkbase](https://splunkbase.splunk.com/app/7931)
- [n8n webhook node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/)
