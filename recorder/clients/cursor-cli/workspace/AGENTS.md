# payments

The checkout service sends its request logs to Splunk Cloud. This folder is the working directory for Splunk content; write new files here.

## Splunk

- Search Splunk with the Splunk MCP Server tools. They are read-only.
- Change Splunk only with `splunkctl`. Run each write without `--yes` first: splunkctl stops it with `CONFIRMATION_REQUIRED`, and that is when you ask me. Show me the command and wait for my approval, then rerun exactly that command with `--yes`. Never add `--yes` on your own.
- Knowledge objects go in the `search` app and their names start with `demo_`.
- Learn `splunkctl` from its skill, `--help`, and `--describe`. Do not inspect the splunkctl binary or its source; the help text is complete.
