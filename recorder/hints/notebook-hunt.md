## Hunting in a notebook

Sign-in events (sourcetype `demo:auth:lake`) are in the Splunk index `demo_auth`, which keeps 14 days. Search it with the Splunk MCP Server tools. The Machine Data Lake keeps 120 days of the same events in a raw table, and a 90-day analytics table is shared with this workspace. `hunt.ipynb` reads both.

Run the notebook with `jpterm`, one cell at a time. It is a guided hunt: do not edit any cell except `params`.

- `jpterm kernel start hunt.ipynb` starts the kernel once. `jpterm show hunt.ipynb --cell <id>` prints a cell without running it.
- `jpterm write hunt.ipynb --cell params --source '<text>'` sets the parameters. Send the whole cell and change only `SUSPECT_IP`. Writing doesn't run it: execute `params` right after, before `setup`.
- `jpterm execute hunt.ipynb --cell <id>` runs a cell and prints it with its output. Run them in this order: `params`, `setup`, `raw-search`, `load-shared`, `backtest`, `enrich`, `detection`.
- `raw-search`, `load-shared`, and `backtest` read the lake, so jpterm stops each one with `CONFIRMATION_REQUIRED`. Same rule as splunkctl: never add `--yes` on your own. When a cell stops, quote its `CONFIRMATION_REQUIRED` line, show me the command, and wait for my approval; then rerun exactly that command with `--yes`.

## Show your evidence

The terminal truncates long output, so whoever watches only sees what you write. After each step, write a short message before your next tool call, under 8 lines:

- Triage of the hot index: the suspect IP, how many accounts it failed against, and why it looks like a spray.
- Each notebook cell: the key numbers and what they mean for the hunt.
