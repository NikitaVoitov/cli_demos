"""Data access for hunt.ipynb: the Machine Data Lake raw table and the shared analytics table.

    lake.describe()                    one line saying where the data comes from
    lake.search_raw(ip, days=120)      raw-table search for one source IP (the storage-optimized path)
    lake.load_shared()                 the analytics table shared with Open Sharing, as a pandas DataFrame

Both return the same columns: _time (UTC), src_ip, user, outcome, app.

Settings come from the environment, which the capture home's jpterm wrapper fills from ~/.config/hunt.env:

    LAKE_MODE            live (default) or fixture: the same synthetic story built in memory, for dry runs only
    LAKE_SCS_URL         https://<host>/<tenant>, the Splunk Cloud Services API root for the search job calls
    LAKE_SCS_TOKEN       a bearer token for that API
    LAKE_RAW_DATASET     the raw table's name
    LAKE_SHARE_PROFILE   the Open Sharing profile file downloaded from the Catalog
    LAKE_SHARE_TABLE     share.schema.table inside that profile
    LAKE_VERIFY          0 skips TLS verification (testing stacks only)

UNVERIFIED against a live stack: the SPL2 in `_RAW_QUERY` and the SCS job calls. Fix them in this file only.
"""

import os
import re
import time
import warnings

import pandas as pd

MODE = os.environ.get("LAKE_MODE", "live")
RAW = os.environ.get("LAKE_RAW_DATASET", "demo_auth_raw")
SHARED = os.environ.get("LAKE_SHARE_TABLE", "")
COLUMNS = ["_time", "src_ip", "user", "outcome", "app"]

# Raw tables only expose _raw and the metadata fields, so filter on text and parse key=value afterwards.
_RAW_QUERY = "| from '{table}' | where like(_raw, \"%src_ip={ip} %\") | fields _time, _raw"


def describe() -> str:
    where = "fixture (not the lake)" if MODE == "fixture" else "live"
    return f"lake: {where} | raw {RAW} | shared {SHARED.split('.')[-1] or '(not set)'}"


def _frame(rows) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=COLUMNS)
    frame["_time"] = pd.to_datetime(frame["_time"], utc=True)
    return frame.sort_values("_time").reset_index(drop=True)


# --- offline fixture --------------------------------------------------------------------------------------------

def _fixture_events():
    import auth_hunt_data as data   # staged next to this file only for dry runs

    return data.events()


def _fixture(ip: str | None, days: int) -> pd.DataFrame:
    events = _fixture_events()
    cutoff = max(e["t"] for e in events) - days * 86400 + 86400
    rows = [[pd.Timestamp(e["t"], unit="s", tz="UTC"), e["src_ip"], e["user"], e["outcome"], e["app"]]
            for e in events if e["t"] >= cutoff and (ip is None or e["src_ip"] == ip)]
    return _frame(rows)


# --- live: Splunk Cloud Services search jobs --------------------------------------------------------------------

def _scs(method: str, path: str, **kwargs):
    import requests

    verify = os.environ.get("LAKE_VERIFY", "1") != "0"
    if not verify:
        warnings.filterwarnings("ignore", message="Unverified HTTPS request")
    response = requests.request(
        method, f"{os.environ['LAKE_SCS_URL']}/search/v3alpha1/{path}",
        headers={"Authorization": f"Bearer {os.environ['LAKE_SCS_TOKEN']}"}, timeout=120, verify=verify, **kwargs)
    response.raise_for_status()
    return response.json()


def _job_rows(query: str, days: int) -> list[dict]:
    job = _scs("POST", "jobs", json={"query": query, "module": "", "queryParameters": {"earliest": f"-{days}d", "latest": "now"}})
    sid = job["sid"]
    for _ in range(300):
        state = _scs("GET", f"jobs/{sid}")
        if state.get("status") == "done":
            break
        if state.get("status") in ("failed", "canceled"):
            raise RuntimeError(f"search job {state['status']}: {state.get('message', '')}")
        time.sleep(1)
    else:
        raise TimeoutError("raw search did not finish in 5 minutes")
    rows, offset = [], 0
    while True:
        page = _scs("GET", f"jobs/{sid}/results", params={"offset": offset, "count": 5000})["results"]
        rows += page
        if len(page) < 5000:
            return rows
        offset += len(page)


def _parse(rows: list[dict]) -> pd.DataFrame:
    parsed = []
    for row in rows:
        kv = dict(re.findall(r"(\w+)=(\S+)", row["_raw"]))
        parsed.append([row["_time"], kv.get("src_ip"), kv.get("user"), kv.get("outcome"), kv.get("app")])
    return _frame(parsed)


# --- public API -------------------------------------------------------------------------------------------------

def search_raw(ip: str, days: int = 120) -> pd.DataFrame:
    if not ip:
        raise ValueError("set SUSPECT_IP in the params cell first")
    if MODE == "fixture":
        return _fixture(ip, days)
    return _parse(_job_rows(_RAW_QUERY.format(table=RAW, ip=ip), days))


def load_shared() -> pd.DataFrame:
    if MODE == "fixture":
        return _fixture(None, 90)
    import delta_sharing

    frame = delta_sharing.load_as_pandas(f"{os.environ['LAKE_SHARE_PROFILE']}#{SHARED}")
    return _frame(frame[COLUMNS].values.tolist())
