# Stack side of SO-03: what must exist before recording

SO-03 runs on a Splunk Cloud stack with Machine Data Lake (the `mdl` capture profile). Checked against the MDL stack
(Splunk Cloud 10.8) and the 10.8 MDL docs. No values belong in this file.

Already in place on that stack: Machine Data Lake and Data Management (other users' raw tables and Edge Processor
routes land there), the Splunk MCP Server app, and the index `demo_auth` (14 days) with an HEC token for it. No Edge
Processor is needed: HEC sends straight to the raw table, which is the documented direct route.

## 1. Keys in `.env`

`python3 scripts/stack_profile.py init mdl` needs `SPLUNK_WEB_BASE_MDL`, `SPLUNK_REST_URL_MDL`,
`SPLUNK_REST_TOKEN_MDL`, `SPLUNK_MCP_TOKEN_MDL` (see that script's docstring). SO-03 also reads:

| Key | Used for |
|---|---|
| `SPLUNK_HEC_TOKEN_IDX_MDL` | `seed_auth.py`: the token whose default index is `demo_auth` |
| `SPLUNK_HEC_TOKEN_RAW_MDL` | `seed_auth.py`: the token whose default index is `~.federated.demo_auth_raw` |
| `SPLUNK_HEC_URL_MDL` | optional; defaults to `https://http-inputs-<host of SPLUNK_WEB_BASE_MDL>` |
| `SPLUNK_SHARE_PROFILE_MDL` | path to the Open Sharing profile file (step 5), outside the repo |
| `SPLUNK_SHARE_TABLE_MDL` | `share.schema.table` inside that profile |
| `SPLUNK_WEB_USER_MDL`, `SPLUNK_WEB_PASSWORD_MDL` | optional Splunk Web login for this stack |

`SPLUNK_HEC_TOKEN_MDL` is SO-08's `demo_soc` token; SO-03 does not use it. The REST token's user needs query access
to the raw table (step 3) and to `demo_auth`: the notebook's raw search runs as that user.

## 2. Index `demo_auth`

14 days retention, and an HEC token with default and allowed index `demo_auth`. Put the token in
`SPLUNK_HEC_TOKEN_IDX_MDL`. The seeder sets the sourcetype `demo:auth:lake` on each event.

## 3. Raw table `demo_auth_raw`

Catalog, Create, Dataset, Machine Data Lake (MDL).

- Name `demo_auth_raw`. Retention **6 months** (the story spans 120 days; its oldest events must not expire on arrival).
- Promotion limits: static promotions up to **90 days**; volume limit at least **5 GB** (the whole story is about
  10 MB, so no promotion waits for approval).
- Permissions: give the role of the REST token's user, and the MCP token's user, **Static promote, query, and view**.
- Data landing: one partition that matches nothing already flowing to an index (we used `source` equals
  `demo:auth:lake`; the seeder sends `source=sso`), routing left as it is, and **no actions**. A "Keep data where …"
  action also filters direct-HEC events: with one, our test events never landed.

Then Settings, Data inputs, HTTP Event Collector, New Token: name `demo_auth_raw_mdl`, default index
`~.federated.demo_auth_raw`, allowed indexes only that one. Put the token in `SPLUNK_HEC_TOKEN_RAW_MDL`. Wait a few
minutes for the token to deploy before seeding.

Test the route with one event, as the docs' "Route HEC events directly" page does: send
`mdl_test_id=<unique> action=direct_hec_test` with sourcetype `mdl:landing:test` through the raw-table token, then
search `| @spl2 from demo_auth_raw` for the ID. It took **about 8 minutes** to land; give it 10 before calling it lost.
The test sourcetype keeps it out of the promotion below.

## 4. Seed

Run from the repo root. The seeder reads the raw table through `lake.py`, which needs pandas, so run it as
`uv run --python 3.12 --with pandas --with requests python scripts/seed_auth.py <flag>` (below: `seed_auth.py`).

1. `seed_auth.py --dry-run` prints the story's numbers and sends nothing.
2. `seed_auth.py` sends the last 14 days to `demo_auth` and all 120 days to the raw table. It refuses if either
   already holds the story: a second seed would add a second, shifted copy to the raw table.
3. `seed_auth.py --check` prints `story present` once the raw table answers: about 5 minutes after the send ends.

The HEC gateway answered `502` once mid-load; the seeder now retries each batch. If a run stops anyway, the hot index
holds a whole number of batches and the story is the same for the whole UTC day, so the remainder can be sent from
that count (resume on the same day only).

Seed once. The story is anchored to the day it was sent, and `--check` fails after about 4 days because the second
campaign is no longer recent. Record within that window. To start over, delete and recreate the raw table and the
analytics table, and clean `demo_auth`.

## 5. Analytics table `demo_auth_hunt_90d`

After `--check` passes: Catalog, `demo_auth_raw`, Promote.

- Type **Static analytics table**. Time range: the last 90 days. Filter `sourcetype` = `demo:auth:lake`.
- Preview: there are no field suggestions for this sourcetype. Turn on the SPL2 editor and shape exactly five columns:

  ```
  | rex field=_raw /user=(?P<user>\S+) src_ip=(?P<src_ip>\S+) outcome=(?P<outcome>\S+) app=(?P<app>\S+)/
  | fields _time, src_ip, user, outcome, app
  ```

  Paste the module whole, with the two lines inside the function after `return from $source`:

  ```
  function process_data($source: dataset): dataset {
      return from $source
      | rex field=_raw /user=(?P<user>\S+) src_ip=(?P<src_ip>\S+) outcome=(?P<outcome>\S+) app=(?P<app>\S+)/
      | fields _time, src_ip, user, outcome, app
  }

  export process_data;
  ```

  Run the preview: the **Fields** panel lists the five columns (`_time` a timestamp, the rest strings). Ignore the
  **Promote fields** dialog and its "some fields are unavailable" warning: it offers props/transforms suggestions,
  and this sourcetype has none. The review page may still say "Selected fields: host, source, sourcetype, _raw, _time"
  and "Estimated promotion volume 0 B"; promote anyway.
- Name `demo_auth_hunt_90d`, then Start promotion. The job completed in about a minute, but the table answered
  searches and Open Sharing with **0 rows for about 9 more minutes**. Wait before deleting or promoting again. The
  result had 104,198 rows; it kept `host`, `source`, `sourcetype`, and an empty `_raw` next to the five columns.
- Open the analytics table, Manage tab: set an expiration that covers the recording days, then Enable sharing,
  then Download external sharing profile. Store it outside the repo with `chmod 600`. Put its path in
  `SPLUNK_SHARE_PROFILE_MDL`.
- `SPLUNK_SHARE_TABLE_MDL` is `<share>.<schema>.<table>`, here `<stack>.mdl_promoted_lakehouse.demo_auth_hunt_90d`. List
  the tables the profile can see with `delta_sharing.SharingClient(profile).list_all_tables()` in the notebook
  environment. The profile path and the table name are two different keys.
- Loading: the table is 112 Parquet files and 706 MB, almost all of it bloom filters (about 6 MB in every file).
  `delta_sharing.load_as_pandas` didn't finish in 20 minutes; `lake.load_shared()` reads only footers and the five
  columns with range requests and takes about 70 s. The profile expires (14 days here): re-download it after.

## 6. Checks

- `python3 scripts/stack_profile.py init mdl`, then `python3 scripts/stack_profile.py check mdl`.
- `seed_auth.py --check` prints `story present`. It runs the same raw-table search
  the notebook runs: `| @spl2 from demo_auth_raw | where like(_raw, "%src_ip=<ip> %")`, through the search head's
  `/services/search/v2/jobs`.
- Every cell against the live lake, without the agent (expect 675 suspect events first seen 78 days ago; 104,198
  sign-ins; the rule flagging only `198.51.100.22` on 13 days; `svc_backup` breached):
  `uv run --python 3.12 --with-requirements recorder/notebook/requirements.txt python` with the cells from
  `build_notebook.py`, in a scratch folder with `lake.py` and the two CSVs, and the `LAKE_*` variables from `stage.sh`.
- Dry run of the notebook without the lake: `LAKE_MODE=fixture` and `scripts/auth_hunt_data.py` next to `lake.py`.
  Never record in fixture mode: `lake.describe()` says `fixture` and the take would show it.
