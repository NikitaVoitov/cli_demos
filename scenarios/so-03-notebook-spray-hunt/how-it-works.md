## About

A company's alert fires on 100 failed sign-ins in five minutes. Nobody has seen it fire in weeks, and a hunter still suspects a password spray: one source IP, one guess per account, spread across the whole day so that no five-minute window ever looks like an attack. The Splunk index only keeps 14 days of sign-ins, so even a confirmed suspect has no history to check. The rest sits in the Machine Data Lake, which is cheap to keep but slow and costly to search.

In this demo the hunter hands the hypothesis to GitHub Copilot CLI. The agent triages the last 14 days of the hot index through Splunk MCP and names the suspect IP. Then it opens the team's hunt notebook and runs it one cell at a time with jpterm. The first cell searches the lake's raw table for that IP's whole history, and shows the same IP running a three-day campaign 78 days ago and returning nine days ago. The second loads a 90-day analytics table, shared through Open Sharing, into the notebook's Python kernel with pandas. The third backtests a detection rule over those 90 days: it flags only the suspect, never fires the existing 100-failures alert, and skips a busy VPN address that fails for as many accounts but succeeds the rest of the time. The agent then checks the suspect against threat intelligence, finds that one privileged service account was breached, and prints the daily search to save as the new alert.

Each of those three cells reads the lake, so jpterm stops it with `CONFIRMATION_REQUIRED` until you approve. The notebook never writes to Splunk: the detection stays as text for you to review. The data is synthetic.

The notebook plays beside the terminal, cell by cell as the agent runs it. Each chart and table there is the cell's real saved output.

### What it uses

Splunk MCP lets the agent search the hot index. The notebook runs in a local Jupyter kernel through jpterm, a terminal client for notebooks that an agent can drive: it starts the kernel, runs one cell by ID, and saves the outputs into the notebook. The Machine Data Lake supplies two sources: the raw table, which keeps every event, and an analytics table promoted from it, which has a fixed schema and is shared with Open Sharing (the Delta Sharing protocol) so pandas can read it. The capture home's `jpterm` is a thin wrapper that holds the three lake cells until `--yes`, and lets the agent edit only the parameter cell.

### Prerequisites

- **Splunk Cloud** stack with **Machine Data Lake**, a raw table, and an analytics table shared with Open Sharing
- **Splunk MCP** app and an MCP token
- A Python environment with **jpterm**, **pandas**, **plotext**, and the **Delta Sharing** client, plus **euporie** to view the executed notebook
- **GitHub Copilot CLI**

### Learn more

- [Machine Data Lake](https://help.splunk.com/en/splunk-cloud-platform/land-data-in-machine-data-lake)
- [Python and pandas Open Sharing example](https://help.splunk.com/en/splunk-cloud-platform/land-data-in-machine-data-lake/10.5.2605/discover-and-search-machine-data-lake-data/query-and-access-machine-data-lake-data/python-and-pandas-open-sharing-example)
- [Splunk MCP on Splunkbase](https://splunkbase.splunk.com/app/7931)
- [jpterm](https://github.com/davidbrochart/jpterm)
- [GitHub Copilot CLI](https://docs.github.com/en/copilot/concepts/agents/about-copilot-cli)
