# Stack side of SO-03: what must exist before recording

SO-03 runs on a Splunk Cloud stack with Machine Data Lake (the `mdl` capture profile). Nothing here is verified
against a live stack yet; the checks at the end say when it is right. No values belong in this file.

## 1. Profile and keys in `.env`

`python3 scripts/stack_profile.py init mdl` needs `SPLUNK_WEB_BASE_MDL`, `SPLUNK_REST_URL_MDL`,
`SPLUNK_REST_TOKEN_MDL`, `SPLUNK_MCP_TOKEN_MDL` (see that script's docstring). The seeder and the staging script
also read:

| Key | Used for |
|---|---|
| `SPLUNK_HEC_URL_MDL`, `SPLUNK_HEC_TOKEN_MDL`, `SPLUNK_HEC_TOKEN_IDX_MDL` | `seed_auth.py`: raw table token, index token |
| `SPLUNK_SCS_URL_MDL`, `SPLUNK_SCS_TOKEN_MDL` | `lake.py`: raw-table search jobs (`https://<host>/<tenant>`) |
| `SPLUNK_SHARE_PROFILE_MDL` | path to the Open Sharing profile file (step 5) |
| `SPLUNK_SHARE_TABLE_MDL` | `share.schema.table` inside that profile |
| `SPLUNK_WEB_USER_MDL`, `SPLUNK_WEB_PASSWORD_MDL` | optional Splunk Web login for this stack |

## 2. Index `demo_auth`

Create it on the stack with **14 days** retention. HEC token `SPLUNK_HEC_TOKEN_IDX_MDL`: default and allowed index
`demo_auth`, sourcetype `demo:auth:lake`.

## 3. Raw table `demo_auth_raw`

Datasets, Create dataset, Machine Data Lake. Retention **180 days** (the story spans 120; the seeder's oldest events
must not expire on arrival). Static promotion: up to 90 days, a volume limit of at least 5 GB. HEC token
`SPLUNK_HEC_TOKEN_MDL`: default and allowed index `~.federated.demo_auth_raw`. Open problems from the first attempt
on a staging stack: dataset creation failed with a 503 ("cleanup is pending"), and direct HEC to the default raw
table landed in `lastchanceindex` instead of the table.

## 4. Seed

`python3 scripts/seed_auth.py --dry-run`, then `python3 scripts/seed_auth.py`. It refuses to double-load `demo_auth`.

## 5. Analytics table `demo_auth_hunt_90d`

Catalog, `demo_auth_raw`, static promotion to an **analytics table**, last **90 days**, sourcetype `demo:auth:lake`.
The schema is exactly these five columns, so the SPL2 shaping step extracts them from `_raw`:
`_time`, `src_ip`, `user`, `outcome`, `app` (strings except `_time`). Then Manage, Enable sharing (Open Sharing),
download the sharing profile, and put its path and table name in `.env` (step 1).

## 6. Checks

- `python3 scripts/stack_profile.py check mdl`
- `python3 scripts/seed_auth.py --check` prints `story present`. It runs the same raw-table search the notebook runs.
- Dry run of the notebook without the lake: `LAKE_MODE=fixture` and `scripts/auth_hunt_data.py` next to `lake.py`.
  Never record in fixture mode: `lake.describe()` says `fixture` and the take would show it.
- If `lake.py`'s SPL2 or SCS job calls differ on your stack, fix them in `lake.py` (marked UNVERIFIED), nowhere else.
