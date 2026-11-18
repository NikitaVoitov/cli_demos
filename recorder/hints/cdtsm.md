## Cisco Deep Time Series Model (CDTSM)

The AI Toolkit's pretrained time series model runs on our own endpoint, so no model training is needed. Call it with `apply CDTSM` in `splunk_run_query`.

The Splunk MCP Server can take a few seconds to connect after the session starts. If its tools are missing, look again; never search with `splunkctl` instead.

- The model needs history before the detection window: set `earliest_time` to `-24h` in `splunk_run_query`, whose default is only 6 hours.
- Anomaly mode needs one row per timestamp and named fields (no `*`). For a metric per region: `| bin _time span=5m | stats perc95(latency_ms) AS p95 by _time region | apply CDTSM p95 BY region mode=anomaly detection_window_earliest=-8h`.
- It adds `p95.forecast` (what the model expected), `p95.threshold_upper`, and `_isAnomaly.p95` (1 inside an anomaly window). Quote fields with dots in `eval` and `where`, for example `'_isAnomaly.p95'`.
- Summarize with `stats` by region: anomalous 5-minute points, first and last anomalous time, peak p95, and peak p95 divided by the forecast.

## Alerts

An alert is a scheduled saved search, created with `splunkctl saved-search add <name> --search '<SPL>' --param ...`. Use `--describe` for the keys. It needs `is_scheduled=1`, `cron_schedule`, `dispatch.earliest_time`, `dispatch.latest_time`, `alert_type=number of events`, `alert_comparator=greater than`, `alert_threshold=0`, `alert.track=1`, and a `description`. To fire only on new anomalies, end the search with a `where` on `'_isAnomaly.p95'=1` and the last 30 minutes of `_time`.

Never ask for approval instead of running the command. Run the create without `--yes` first: splunkctl refuses it on screen with `CONFIRMATION_REQUIRED`, and that refusal is when you ask me. Then wait, and only after I approve, rerun exactly that command with `--yes`.

## Show your evidence

The terminal hides MCP results, so whoever watches only sees what you write. After each step, write a short message before the next tool call:

- The anomaly check: a small table with one row per region (anomalous window, peak p95, peak versus forecast), then one line on what it means.
- The alert: its name, schedule, and the condition that fires it.

Keep each message under 8 lines.
