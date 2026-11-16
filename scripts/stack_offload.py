#!/usr/bin/env python3
"""Temporarily offload the shared CO2 stack by pausing Enterprise Security workload.

    stack_offload.py plan      # read-only: show what would change
    stack_offload.py disable   # snapshot, then pause ES enforcement, DM acceleration, ES searches, stuck jobs
    stack_offload.py cancel    # cancel queued/parsing scheduler and ES jobs again (not restorable)
    stack_offload.py restore   # put back exactly what the snapshot recorded as enabled

Uses the host and token from ~/.splunkctl/config.yaml. splunkctl itself can't address
/servicesNS/<owner>/<app>/..., which is where ES content lives, so this calls REST directly.
The staging stack's 8089 certificate chains to a non-public root, hence the unverified context.
"""

import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parent.parent / ".captures" / "offload" / "snapshot.json"

ES_APP = re.compile(r"^(SplunkEnterpriseSecuritySuite|SA-.*|DA-ESS-.*|missioncontrol|exposure-analytics)$")
CANCEL_PROVENANCE = {"scheduler", "summary_director"}


def config():
    text = (Path.home() / ".splunkctl" / "config.yaml").read_text()
    host = re.search(r"^host:\s*(\S+)", text, re.M).group(1).strip("'\"")
    token = re.search(r"^token:\s*(\S+)", text, re.M).group(1).strip("'\"")
    return host.rstrip("/"), token


HOST, TOKEN = config()
CTX = ssl._create_unverified_context()


def call(path, data=None, method=None):
    url = HOST + path
    body = None
    if data is not None:
        body = urllib.parse.urlencode({**data, "output_mode": "json"}).encode()
    elif "output_mode" not in path:
        url += ("&" if "?" in url else "?") + "output_mode=json"
    req = urllib.request.Request(url, data=body, method=method or ("POST" if body else "GET"))
    req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, context=CTX, timeout=120) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


def q(s):
    return urllib.parse.quote(s, safe="")


def ns(acl):
    # App- and global-shared objects live under nobody; writing through the owner's namespace
    # leaves them untouched and creates a private copy instead.
    owner = acl.get("owner") if acl.get("sharing") == "user" else "nobody"
    return f"/servicesNS/{q(owner or 'nobody')}/{q(acl['app'])}"


def inventory():
    searches = call("/servicesNS/-/-/saved/searches?count=0&search=" + q("is_scheduled=1 disabled=0"))["entry"]
    models = call("/servicesNS/-/-/datamodel/model?count=0")["entry"]
    try:
        enforce = call("/servicesNS/-/-/data/inputs/dm_accel_settings?count=0")["entry"]
    except urllib.error.HTTPError:
        enforce = []
    return {
        "takenAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "searches": [
            {"name": e["name"], "app": e["acl"]["app"], "owner": e["acl"]["owner"], "sharing": e["acl"]["sharing"]}
            for e in searches
            if ES_APP.match(e["acl"]["app"])
        ],
        "models": [
            {"name": e["name"], "app": e["acl"]["app"], "owner": e["acl"]["owner"], "sharing": e["acl"]["sharing"],
             "acceleration": e["content"]["acceleration"]}
            for e in models
            if json.loads(e["content"].get("acceleration") or "{}").get("enabled") is True
        ],
        "enforcement": [
            {"name": e["name"], "app": e["acl"]["app"], "owner": e["acl"]["owner"], "sharing": e["acl"]["sharing"]}
            for e in enforce
            if str(e["content"].get("acceleration")).lower() in ("1", "true")
        ],
    }


def stuck_jobs():
    jobs = call("/services/search/jobs?count=0")["entry"]
    return [
        j["content"]["sid"]
        for j in jobs
        if j["content"].get("dispatchState") in ("QUEUED", "PARSING")
        and (j["content"].get("provenance") in CANCEL_PROVENANCE or ES_APP.match(j["acl"].get("app") or ""))
    ]


def run(label, items, fn):
    ok = failed = 0
    for item in items:
        try:
            fn(item)
            ok += 1
        except (urllib.error.URLError, OSError) as err:
            failed += 1
            reason = f"HTTP {err.code}" if isinstance(err, urllib.error.HTTPError) else type(err).__name__
            print(f"  ! {label} {item.get('name', item) if isinstance(item, dict) else item}: {reason}")
    print(f"{label}: {ok} ok, {failed} failed")


def accel(model, enabled):
    settings = json.loads(model["acceleration"])
    settings["enabled"] = enabled
    call(f"{ns(model)}/datamodel/model/{q(model['name'])}", {"acceleration": json.dumps(settings)})


def main(mode):
    if mode == "plan":
        inv = inventory()
        print(json.dumps({k: len(v) if isinstance(v, list) else v for k, v in inv.items()}, indent=2))
        print(f"stuck scheduler jobs: {len(stuck_jobs())}")
        return

    if mode == "disable":
        # An existing snapshot means an earlier disable was interrupted: resume from it, because
        # a fresh inventory would no longer list what that run already turned off.
        if SNAPSHOT.exists():
            inv = json.loads(SNAPSHOT.read_text())
            print(f"resuming from snapshot: {SNAPSHOT}")
        else:
            inv = inventory()
            SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
            SNAPSHOT.write_text(json.dumps(inv, indent=2))
            print(f"snapshot: {SNAPSHOT}")
        run("enforcement off", inv["enforcement"],
            lambda e: call(f"{ns(e)}/data/inputs/dm_accel_settings/{q(e['name'])}", {"acceleration": "0"}))
        run("acceleration off", inv["models"], lambda m: accel(m, False))
        run("ES searches disabled", inv["searches"],
            lambda s: call(f"{ns(s)}/saved/searches/{q(s['name'])}", {"disabled": "1"}))
        run("stuck jobs cancelled", stuck_jobs(),
            lambda sid: call(f"/services/search/jobs/{q(sid)}/control", {"action": "cancel"}))
        return

    if mode == "cancel":
        run("stuck jobs cancelled", stuck_jobs(),
            lambda sid: call(f"/services/search/jobs/{q(sid)}/control", {"action": "cancel"}))
        return

    if mode == "restore":
        inv = json.loads(SNAPSHOT.read_text())
        run("ES searches enabled", inv["searches"],
            lambda s: call(f"{ns(s)}/saved/searches/{q(s['name'])}", {"disabled": "0"}))
        run("acceleration on", inv["models"], lambda m: accel(m, True))
        run("enforcement on", inv["enforcement"],
            lambda e: call(f"{ns(e)}/data/inputs/dm_accel_settings/{q(e['name'])}", {"acceleration": "1"}))
        SNAPSHOT.rename(SNAPSHOT.with_name(f"snapshot.restored-{int(time.time())}.json"))
        return

    sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
