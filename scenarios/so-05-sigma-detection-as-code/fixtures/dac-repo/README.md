# ACME SOC detections

Custom Splunk Enterprise Security detections, built from [Sigma](https://sigmahq.io) rules with
[sigma-cli](https://github.com/SigmaHQ/sigma-cli) and packaged with [contentctl](https://github.com/splunk/contentctl).
Conventions: [AGENTS.md](AGENTS.md).

| Path | What |
|---|---|
| `sigma/rules/` | Community Sigma rules we use (SigmaHQ, DRL 1.1) |
| `detections/` | ES detections in contentctl YAML, one per Sigma rule |
| `macros/` | Shared macros and per-detection `_filter` tuning |
| `tests/` | Test cases per detection and the Sysmon events they replay |
| `ci/` | Scripts the workflows run |
| `.github/workflows/` | `validate` on every pull request, `deploy` on merge to `main` |

```bash
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
contentctl build                     # validate and package into dist/
```
