## Saved searches and macros

When a saved search fails, run it with the Splunk MCP `splunk_run_saved_search` tool first: the search parser's error names the first thing that is wrong, such as a macro that cannot be found. Look the object up with `splunk_get_knowledge_objects` (type `macros`, `saved_searches`) and, for a missing macro, work out its definition from the saved search's description and from the data it reads.

Fix the missing object, not the search: restore a macro with `splunkctl macro add <name> --definition '<SPL>'`. `splunkctl macro add` has no `--app` flag: it creates the macro in the `search` app for the current user, which is where this saved search runs, so no extra option is needed. After the fix, rerun the saved search with `splunk_run_saved_search` (a read), not `splunkctl saved-search dispatch`, so the only approval in the session is the repair itself.
