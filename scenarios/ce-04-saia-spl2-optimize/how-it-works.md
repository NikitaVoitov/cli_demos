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

Both complete queries appear in the terminal. The closing side-by-side comparison uses
[icdiff](https://github.com/jeffkaufman/icdiff): the original is on the left and SAIA's rewrite on the right.
Red marks removed code, green marks additions, and yellow highlights changed expressions. Narration explains
the original's extra work and the rewrite's combined aggregation while the relevant code stays on screen.

Using synthetic sign-in data, the baseline took 148.107 seconds and the rewrite took 7.913 seconds, about
19 times faster in this recorded run. Both jobs reported 1,421,600 events and returned the same four rows by
value; the order of tied rows changed. Timings vary with caching and load. Only narrow the index scope if it
still covers all the data your search needs.

### Prerequisites

- Splunk Cloud with the `demo_soc` sample data
- Splunk MCP Server with Splunk AI Assistant tools enabled
- GitHub Copilot CLI with the `search-performance-optimizer` and `splunkctl` skills
- icdiff, installed with the pipeline requirements, for the recorded terminal comparison

### Learn more

- [Splunk AI Assistant](https://www.splunk.com/en_us/products/splunk-ai-assistant.html)
- [Splunk Agent Skills](https://github.com/splunk/splunk-agent-skills)
- [Splunk MCP Server](https://help.splunk.com/en/splunk-cloud-platform/mcp-server-for-splunk-platform/2.1/about-splunk-mcp-server/about-mcp-server-for-splunk-platform)
