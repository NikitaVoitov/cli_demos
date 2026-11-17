## Jira

Security alerts are work items in Jira project __JIRA_PROJECT__ on __JIRA_SITE__, labeled `alert`. Each one names the Splunk index, sourcetype, and fields to look at.

- Read Jira with the Atlassian MCP tools (`searchJiraIssuesUsingJql`, `getJiraIssue`). Call `getAccessibleAtlassianResources` once for the cloudId.
- Change Jira only with `acli`, which is signed in to this site. Same rule as splunkctl: never add `--yes` on your own, and never ask for approval instead of running the command. Run the write without `--yes` first. acli prints `CONFIRMATION_REQUIRED` and exits; that on-screen refusal is when you ask me. Then wait, and only after I approve, rerun exactly that command with `--yes`. The Atlassian MCP write tools are not available here.
- A follow-up ticket is one command: `acli jira workitem create --project __JIRA_PROJECT__ --type Task --summary '<summary>' --description '<plain text>' --label follow-up`. Name the alert it follows up in the description.

## ML in Splunk

Our own saved searches and ML models start with `demo_`; ignore the Enterprise Security ones. List them with `| rest /servicesNS/-/-/saved/searches splunk_server=local | search title=demo_*` in `splunk_run_query`, then run each one with `splunk_run_saved_search`. The AI Toolkit's `fit` and `apply` commands work in `splunk_run_query`.

## Show your evidence

The terminal hides MCP results, so whoever watches only sees what you write. After each step below, write a short message before the next tool call:

- The open alerts: one line per alert with its key, priority, and what it reports.
- Each ML saved search: which model it applies and to what data, then its top rows as a small table (at most 5 rows), and what that result means.
- Each confirming search: the key numbers in one or two lines.

Keep each message under 8 lines.
