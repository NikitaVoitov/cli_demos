#!/usr/bin/env python3
"""Run Splunk AppInspect (Splunk Cloud Victoria checks) on the built app package.

    SPLUNK_COM_USERNAME=... SPLUNK_COM_PASSWORD=... python ci/appinspect.py dist/<app>-latest.tar.gz

Skips with a notice when the splunk.com credentials aren't set. Exits 1 on any failure or error check.
"""

import base64
import json
import os
import sys
import time
import urllib.request
import uuid
from pathlib import Path

API = "https://appinspect.splunk.com/v1/app"


def request(url: str, token: str | None = None, data: bytes | None = None, headers: dict | None = None) -> dict:
    h = {**(headers or {})}
    if token:
        h["Authorization"] = f"bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, data, h), timeout=120) as r:
        return json.loads(r.read())


def main() -> int:
    user, password = os.environ.get("SPLUNK_COM_USERNAME"), os.environ.get("SPLUNK_COM_PASSWORD")
    if not (user and password):
        print("::notice::AppInspect skipped: SPLUNK_COM_USERNAME and SPLUNK_COM_PASSWORD are not set")
        return 0
    basic = base64.b64encode(f"{user}:{password}".encode()).decode()
    token = request("https://api.splunk.com/2.0/rest/login/splunk", headers={"Authorization": f"Basic {basic}"})["data"]["token"]

    package = Path(sys.argv[1])
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"included_tags\"\r\n\r\nprivate_victoria\r\n"
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"app_package\"; filename=\"{package.name}\"\r\n"
            "Content-Type: application/gzip\r\n\r\n").encode() + package.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    req = request(f"{API}/validate", token, body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    for _ in range(60):
        status = request(f"{API}/validate/status/{req['request_id']}", token)
        if status["status"] in ("SUCCESS", "FAILURE"):
            break
        time.sleep(10)
    info = status.get("info", {})
    print(f"AppInspect ({package.name}, private_victoria): " + ", ".join(f"{k} {v}" for k, v in info.items() if v))
    return 1 if status["status"] != "SUCCESS" or info.get("failure") or info.get("error") else 0


if __name__ == "__main__":
    sys.exit(main())
