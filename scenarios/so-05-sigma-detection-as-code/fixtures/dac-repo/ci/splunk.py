"""Small Splunk REST client for the CI scripts. Prints no hosts or tokens."""

import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

# Splunk Cloud stacks on staging and test instances present certificates runners don't trust.
CTX = ssl._create_unverified_context()


class Splunk:
    def __init__(self, base: str | None = None, token: str | None = None):
        self.base = (base or os.environ["SPLUNK_MGMT_URL"]).rstrip("/")
        self.token = token or os.environ["SPLUNK_TOKEN"]

    def call(self, method: str, path: str, data: dict | None = None, timeout: int = 300) -> tuple[int, dict]:
        params = {**(data or {}), "output_mode": "json"}
        if method in ("GET", "DELETE"):
            sep = "&" if "?" in path else "?"
            url, body = f"{self.base}{path}{sep}{urllib.parse.urlencode(params)}", None
        else:
            url, body = f"{self.base}{path}", urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(url, body, {"Authorization": f"Bearer {self.token}"}, method=method)
        for attempt in range(8):
            try:
                with urllib.request.urlopen(req, context=CTX, timeout=timeout) as r:
                    return r.status, json.loads(r.read() or b"{}")
            except urllib.error.HTTPError as e:
                # 503 includes "search concurrency limit reached": wait for a slot.
                if e.code >= 500 and attempt < 7:
                    time.sleep(10 if e.code == 503 else 5)
                    continue
                return e.code, {"messages": e.read().decode(errors="replace")[:500]}
        raise RuntimeError("unreachable")

    def search(self, spl: str, earliest: str = "-24h", latest: str = "now") -> list[dict]:
        status, body = self.call("POST", "/services/search/jobs", {
            "search": spl if spl.lstrip().startswith("|") else f"search {spl}",
            "exec_mode": "oneshot", "count": 0, "earliest_time": earliest, "latest_time": latest})
        if status != 200:
            raise RuntimeError(f"search failed: HTTP {status} {body.get('messages')}")
        fatal = [m.get("text") for m in body.get("messages", []) if m.get("type") in ("FATAL", "ERROR")]
        if fatal:
            raise RuntimeError(f"search failed: {fatal[0]}")
        return body.get("results", [])


def send_hec(events: list[dict]) -> None:
    """Send events to HEC in one request. Each event: {host, index, sourcetype, source, event, time}."""
    url = os.environ["SPLUNK_HEC_URL"].rstrip("/")
    url = url if url.endswith("/event") else url + "/services/collector/event"
    body = "".join(json.dumps(e) for e in events).encode()
    req = urllib.request.Request(url, body, {"Authorization": f"Splunk {os.environ['SPLUNK_HEC_TOKEN']}"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, context=CTX, timeout=60) as r:
                if r.status == 200:
                    return
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == 4:
                raise RuntimeError(f"HEC rejected the events: HTTP {e.code} {e.read().decode()[:200]}")
        time.sleep(3)
