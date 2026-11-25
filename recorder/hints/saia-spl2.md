## SPL2 performance workflow

Use the `search-performance-optimizer` skill. Measure the baseline before changing the query, and compare the
completed job's runtime, event count, result count, and output rows after the rewrite.

The workspace has `login_failure_rate.spl2`. Run it as SPL2 with `splunkctl` by prefixing the query with `| `,
start it detached with `splunkctl --yes`, and poll `splunkctl jobs status <sid>` until `dispatchState` is `DONE`.
Then use `splunkctl jobs show <sid>` to read its rows. Do the same for the optimized query. The user has
authorized these read-only search jobs; do not pass `--read-only` (it blocks job submission), and do not change
Splunk configuration.

Ask Splunk AI Assistant to optimize this SPL2 query with `saia_generate_spl`, setting `spl_only` to true. Use
this request: "Optimize this SPL2 search for performance. Return valid SPL2 (not SPL1) with the same output
fields and no added time filter." Save the returned query as `optimized_login_failure_rate.spl2`. Run searches
read-only; do not make changes to Splunk.
