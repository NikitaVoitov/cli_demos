## About

Building a dashboard usually means finding the data, writing the searches, publishing the dashboard, and then opening Splunk Web to see whether the panels actually render. That loop is slow, and a panel that looks finished can still be empty.

In this demo you ask for a checkout latency dashboard for the last 24 hours. The agent finds the checkout data in Splunk, drafts the dashboard, and stops before anything is published so you can approve it. Once you do, it publishes the dashboard and checks in Splunk Web that every panel renders.

Splunk MCP lets the agent search your data without changing anything. Dashboard Studio is the dashboard it builds. splunkctl is how that dashboard reaches Splunk Cloud, and it waits for your approval before it does.

### Prerequisites

- **Splunk Cloud** stack with REST port 8089 reachable
- **splunkctl** 0.1.2 or later, with a token
- **Splunk MCP** app and an MCP token
- **Agent Skills**: splunkctl (`splunkctl skill install`), search-and-dashboard-troubleshooter, playwright-cli
- **Cursor CLI** with Playwright CLI

### Learn more

- [splunkctl on GitHub](https://github.com/splunk/splunkctl)
- [Splunk Agent Skills](https://github.com/splunk/splunk-agent-skills)
- [Splunk MCP on Splunkbase](https://splunkbase.splunk.com/app/7931)
- [Playwright CLI](https://www.npmjs.com/package/@playwright/cli)
