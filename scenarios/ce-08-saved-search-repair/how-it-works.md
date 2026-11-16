## About

A saved search that a report or an alert depends on stops returning results, and the cause is usually something it depends on, such as a macro that was deleted, rather than the search itself. Finding that by hand means running the search, reading the error, and hunting through the knowledge objects.

In this demo you point the agent at a saved search that has stopped working. It runs the search, finds the missing macro, and proposes restoring it, then waits for your approval. Once you approve, it restores the macro and reruns the search so you can see the results come back.

Splunk MCP lets the agent run the search and look up the objects it depends on. Agent Skills tell it how to diagnose a failing search. splunkctl applies the repair on Splunk Cloud, and only after you approve.

### Prerequisites

- **Splunk Cloud** stack with REST port 8089 reachable
- **splunkctl** 0.1.2 or later, with a token
- **Splunk MCP** app and an MCP token
- **Agent Skills**: splunkctl (`splunkctl skill install`), search-and-dashboard-troubleshooter
- **Cursor CLI**

### Learn more

- [splunkctl on GitHub](https://github.com/splunk/splunkctl)
- [Splunk Agent Skills](https://github.com/splunk/splunk-agent-skills)
- [Splunk MCP on Splunkbase](https://splunkbase.splunk.com/app/7931)
