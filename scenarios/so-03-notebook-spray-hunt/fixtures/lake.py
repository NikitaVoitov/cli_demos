"""Data access for hunt.ipynb: the Machine Data Lake raw table and the shared analytics table.

    lake.describe()                    one line saying where the data comes from
    lake.search_raw(ip, days=120)      raw-table search for one source IP (the storage-optimized path)
    lake.load_shared()                 the analytics table shared with Open Sharing, as a pandas DataFrame

Both return the same columns: _time (UTC), src_ip, user, outcome, app.

Settings come from the environment, which the capture home's jpterm wrapper fills from ~/.config/hunt.env:

    LAKE_MODE            live (default) or fixture: the same synthetic story built in memory, when the lake is unavailable
    LAKE_FIXTURE_DAY     fixture only: the YYYY-MM-DD the stack was seeded, so the story matches its hot index
    LAKE_REST_URL        https://<stack>:8089, the search head's REST API
    LAKE_REST_TOKEN      a bearer token for that API, with query access to the raw table
    LAKE_RAW_DATASET     the raw table's name
    LAKE_SHARE_PROFILE   the Open Sharing profile file downloaded from the Catalog
    LAKE_SHARE_TABLE     share.schema.table inside that profile
    LAKE_VERIFY          0 skips TLS verification (testing stacks only)

Raw search is what the Catalog's Search action dispatches: an SPL2 search job (`| @spl2 from <raw table>`) on the
search head. Raw tables expose only _time, _raw, and the metadata fields, so the IP filter is a text match.
"""

import io
import os
import re
import time
import warnings
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

MODE = os.environ.get("LAKE_MODE", "live")
RAW = os.environ.get("LAKE_RAW_DATASET", "demo_auth_raw")
SHARED = os.environ.get("LAKE_SHARE_TABLE", "")
COLUMNS = ["_time", "src_ip", "user", "outcome", "app"]

# Raw tables only expose _raw and the metadata fields, so filter on text and parse key=value afterwards.
_RAW_QUERY = '| @spl2 from {table} | where like(_raw, "%src_ip={ip} %") | fields _time, _raw'


def describe() -> str:
    where = "fixture (not the lake)" if MODE == "fixture" else "live"
    return f"lake: {where} | raw {RAW} | shared {SHARED.split('.')[-1] or '(not set)'}"


def _frame(rows) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=COLUMNS)
    frame["_time"] = pd.to_datetime(frame["_time"], utc=True)
    return frame.sort_values("_time").reset_index(drop=True)


# --- offline fixture --------------------------------------------------------------------------------------------

def _fixture_events():
    from datetime import datetime, timezone

    import auth_hunt_data as data   # staged next to this file only in fixture mode

    day = os.environ.get("LAKE_FIXTURE_DAY")
    return data.events(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc) if day else None)


def _fixture(ip: str | None, days: int) -> pd.DataFrame:
    events = _fixture_events()
    last = max(e["t"] for e in events)
    cutoff = last - last % 86400 - days * 86400   # whole days, like the lake's day-partitioned tables
    rows = [[pd.Timestamp(e["t"], unit="s", tz="UTC"), e["src_ip"], e["user"], e["outcome"], e["app"]]
            for e in events if e["t"] >= cutoff and (ip is None or e["src_ip"] == ip)]
    return _frame(rows)


# --- live: SPL2 search jobs on the search head ------------------------------------------------------------------

def _rest(method: str, path: str, **kwargs):
    import requests

    verify = os.environ.get("LAKE_VERIFY", "1") != "0"
    if not verify:
        warnings.filterwarnings("ignore", message="Unverified HTTPS request")
    response = requests.request(
        method, f"{os.environ['LAKE_REST_URL'].rstrip('/')}/services/search/v2/jobs{path}",
        headers={"Authorization": f"Bearer {os.environ['LAKE_REST_TOKEN']}"}, timeout=120, verify=verify, **kwargs)
    response.raise_for_status()
    return response.json()


def _job_rows(query: str, days: int) -> list[dict]:
    job = _rest("POST", "", data={"search": query, "earliest_time": f"-{days}d", "latest_time": "now",
                                  "output_mode": "json"})
    sid = job["sid"]
    for _ in range(300):
        state = _rest("GET", f"/{sid}", params={"output_mode": "json"})["entry"][0]["content"]
        if state.get("isFailed") or state.get("dispatchState") == "FAILED":
            raise RuntimeError(f"raw search failed: {state.get('messages')}")
        if state.get("isDone"):
            break
        time.sleep(1)
    else:
        raise TimeoutError("raw search did not finish in 5 minutes")
    rows, offset = [], 0
    while True:
        page = _rest("GET", f"/{sid}/results", params={"output_mode": "json", "offset": offset, "count": 5000})["results"]
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


class _Ranges(io.RawIOBase):
    """A read-only file over one presigned URL that fetches only the byte ranges Parquet asks for.

    MDL writes a 1 MB bloom filter per string column into every file, between the tiny column data at the start
    and the footer at the end. Reading the footer and the selected columns skips them."""

    def __init__(self, session, url: str, size: int):
        self.session, self.url, self.size, self.pos = session, url, size, 0
        tail = max(0, size - 65536)
        self.cache = {0: self._get(0, min(size, 65536)), tail: self._get(tail, size)}

    def _get(self, start: int, end: int) -> bytes:
        response = self.session.get(self.url, headers={"Range": f"bytes={start}-{end - 1}"}, timeout=120)
        response.raise_for_status()
        return response.content

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = 0) -> int:
        self.pos = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        return self.pos

    def read(self, n: int = -1) -> bytes:
        end = self.size if n is None or n < 0 else min(self.size, self.pos + n)
        for start, chunk in self.cache.items():
            if start <= self.pos and end <= start + len(chunk):
                data = chunk[self.pos - start:end - start]
                break
        else:
            data = self._get(self.pos, end)
        self.pos = end
        return data


def _shared_files():
    from delta_sharing.protocol import DeltaSharingProfile, Table
    from delta_sharing.rest_client import DataSharingRestClient

    share, schema, name = SHARED.split(".")
    client = DataSharingRestClient(DeltaSharingProfile.read_from_file(os.environ["LAKE_SHARE_PROFILE"]))
    return client.list_files_in_table(Table(name=name, share=share, schema=schema)).add_files


def load_shared() -> pd.DataFrame:
    if MODE == "fixture":
        return _fixture(None, 90)
    import pyarrow as pa
    import pyarrow.parquet as pq
    import requests
    import urllib3

    session = requests.Session()
    # S3 sometimes drops a reused keep-alive connection; the ranged GETs are safe to repeat.
    retry = urllib3.util.Retry(total=5, backoff_factor=0.5, status_forcelist=(500, 502, 503, 504))
    session.mount("https://", requests.adapters.HTTPAdapter(pool_maxsize=16, max_retries=retry))

    def read(f):
        return pq.ParquetFile(_Ranges(session, f.url, f.size)).read(columns=COLUMNS)

    with ThreadPoolExecutor(max_workers=16) as pool:
        tables = list(pool.map(read, _shared_files()))
    return _frame(pa.concat_tables(tables).to_pandas().values.tolist())
