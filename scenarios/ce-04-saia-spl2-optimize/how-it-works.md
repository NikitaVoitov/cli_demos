## About

A useful search can still waste time when it reads broadly, computes related facts in separate branches, and
joins the results back together. This demo starts with an SPL2 search for sign-in failure rates. GitHub Copilot
CLI uses the search-performance-optimizer skill to guide the comparison and asks Splunk AI Assistant for a
rewrite through the Splunk MCP Server. It uses splunkctl to run both queries as read-only jobs and compare
their runtimes and result rows.

The original search starts from a wildcard index selection, filters for the event type afterward, counts all
attempts in one branch, then counts failures in a second branch and joins those aggregates. Splunk AI Assistant
rewrites it to read the `demo_soc` index and calculate attempts and failures together in one `stats` operation,
then calculate the rate. This removes the separate search branch and join while keeping the report's fields and
calculations.

On the recorded CO2 data, the baseline took 91.56 seconds and the rewrite took 2.465 seconds. Both jobs reported
1,421,600 events and returned the same four rows. The comparison demonstrates this rewrite on the seeded data;
the narrower index scope should be retained only where it matches the intended data coverage.

### Prerequisites

- Splunk Cloud with the `demo_soc` sample data
- Splunk MCP Server with Splunk AI Assistant tools enabled
- GitHub Copilot CLI with the `search-performance-optimizer` and `splunkctl` skills

### Learn more

- [Splunk AI Assistant](https://www.splunk.com/en_us/products/splunk-ai-assistant.html)
- [Splunk Agent Skills](https://github.com/splunk/splunk-agent-skills)
- [Splunk MCP Server](https://help.splunk.com/en/splunk-cloud-platform/mcp-server-for-splunk-platform/2.1/about-splunk-mcp-server/about-mcp-server-for-splunk-platform)
