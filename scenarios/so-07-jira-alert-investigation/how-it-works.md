## About

A payments company's SOC queue has a new high-priority alert in Jira: declined card payments are spiking at two partner merchants. Five other alerts sit next to it. One reports brute-force logins, one reports merchant complaints about card testing, and others cover odd sessions, settlement returns, and a printer. Is this one incident or six?

Answering that by hand is slow. An analyst opens every ticket, writes a search for each data source, and has to know which machine learning model to trust. Meanwhile the attacker keeps testing stolen cards.

In this demo the analyst hands the alert to Cursor CLI with one prompt. The agent reads the queue and runs the two models the team already saved in Splunk. The first model, on transaction amounts, flags only a few large but ordinary purchases, so the agent rules that theory out. The second model, on declines per source IP, flags three IP addresses. Each made about 200 declined charges of around $13, spread across the same 40 accounts. The agent then checks those IPs against the login and session data. The same IPs brute-forced 12 online-banking accounts and got into five. The declines, the card-testing complaints, and the brute-force alert turn out to be one attack.

The agent drafts a follow-up ticket to block the three IPs, with the evidence attached, and waits for your approval before it writes to Jira. One prompt takes the analyst from an alert to a named attacker and an evidence-backed ticket. All they have to do is approve.

### What it uses

The Atlassian MCP lets the agent read Jira. Splunk MCP lets it search Splunk and run Splunk AI Toolkit models without changing anything. The Atlassian CLI (acli) is the only way it can write to Jira, and it waits for your approval first. The data and tickets are synthetic and live on a demo Jira site.

### Prerequisites

- **Splunk Cloud** stack with the **Splunk AI Toolkit**
- **Splunk MCP** app and an MCP token
- **Jira Cloud** site, with the **Atlassian Rovo MCP server** and the **Atlassian CLI** (acli) signed in
- **Cursor CLI**

### Learn more

- [Leveraging LLM reasoning and ML capabilities for Jira alert investigations (Splunk Lantern)](https://lantern.splunk.com/Security_Use_Cases/Automation_and_Orchestration/Leveraging_LLM_reasoning_and_ML_capabilities_for_Jira_alert_investigations)
- [Splunk MCP on Splunkbase](https://splunkbase.splunk.com/app/7931)
- [Atlassian Rovo MCP server](https://support.atlassian.com/atlassian-rovo-mcp-server/)
- [Atlassian CLI](https://developer.atlassian.com/cloud/acli/)
