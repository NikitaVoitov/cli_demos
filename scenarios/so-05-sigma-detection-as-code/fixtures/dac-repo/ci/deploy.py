#!/usr/bin/env python3
"""Deploy the built app's macros and detections to the Enterprise Security search head over REST, then verify.

    SPLUNK_MGMT_URL=... SPLUNK_TOKEN=<deploy token> python ci/deploy.py

Creates the app if missing, then creates or updates each stanza of the built default/macros.conf and
default/savedsearches.conf in it (owner nobody). Detections are shared globally like ESCU's; a macro is shared
globally unless another app already shares one by that name (ESCU's security_content_* macros), so ours never
shadow theirs. Detections in the app that are no longer in the repo are deleted. Ends by checking that every
detection is enabled, scheduled, and an ES correlation search.
"""

import os
import sys
import urllib.parse
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from splunk import Splunk  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / yaml.safe_load((ROOT / "ci/config.yml").read_text())["app_dir"]


def stanzas(path: Path) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    current = None
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("[") and line.rstrip().endswith("]"):
            current = line.strip()[1:-1]
            out[current] = {}
        elif current is not None and "=" in line:
            key, value = line.split("=", 1)
            out[current][key.strip()] = value.strip()
    out.pop("default", None)
    return out


def check(status: int, body: dict, what: str) -> None:
    if status not in (200, 201):
        sys.exit(f"{what}: HTTP {status} {body.get('messages')}")


def main() -> int:
    splunk, app = Splunk(), APP_DIR.name
    q = lambda s: urllib.parse.quote(s, safe="")  # noqa: E731
    ns = f"/servicesNS/nobody/{q(app)}"

    if splunk.call("GET", f"/services/apps/local/{q(app)}")[0] != 200:
        label = stanzas(APP_DIR / "default/app.conf").get("ui", {}).get("label", app)
        check(*splunk.call("POST", "/services/apps/local", {"name": app, "label": label, "template": "barebones",
                                                            "visible": "false"}), f"app {app}")
        print(f"app {app}: created")

    def upsert(endpoint: str, name: str, values: dict[str, str]) -> str:
        status, found = splunk.call("GET", f"{endpoint}/{q(name)}")
        # The namespace also resolves objects other apps share globally; only ours count as existing.
        mine = status == 200 and found["entry"][0]["acl"]["app"] == app
        if mine:
            check(*splunk.call("POST", f"{endpoint}/{q(name)}", values), name)
            return "updated"
        check(*splunk.call("POST", endpoint, {"name": name, **values}), name)
        return "created"

    def share(path: str, sharing: str) -> None:
        check(*splunk.call("POST", f"{path}/acl", {"sharing": sharing, "owner": "nobody"}), f"{path} acl")

    _, listed = splunk.call("GET", "/servicesNS/-/-/admin/macros", {"count": 0, "f": "title"})
    elsewhere = {e["name"] for e in listed.get("entry", []) if e["acl"]["app"] != app and e["acl"]["sharing"] == "global"}
    for name, values in stanzas(APP_DIR / "default/macros.conf").items():
        print(f"macro {name}: {upsert(f'{ns}/configs/conf-macros', name, values)}")
        share(f"{ns}/configs/conf-macros/{q(name)}", "app" if name in elsewhere else "global")

    detections = stanzas(APP_DIR / "default/savedsearches.conf")
    for name, values in detections.items():
        print(f"detection {name}: {upsert(f'{ns}/configs/conf-savedsearches', name, values)}")
    # Git is the source of truth: a detection removed from the repo is removed from the app.
    _, ours = splunk.call("GET", f"{ns}/saved/searches", {"count": 0, "search": f"eai:acl.app={app}"})
    for entry in ours.get("entry", []):
        if entry["acl"]["app"] == app and entry["name"] not in detections:
            check(*splunk.call("DELETE", f"{ns}/saved/searches/{q(entry['name'])}"), entry["name"])
            print(f"detection {entry['name']}: removed (no longer in the repo)")
    splunk.call("POST", f"{ns}/saved/searches/_reload")
    for name in detections:
        share(f"{ns}/saved/searches/{q(name)}", "global")

    rows, bad = [], 0
    for name in detections:
        status, body = splunk.call("GET", f"{ns}/saved/searches/{q(name)}")
        c = body["entry"][0]["content"] if status == 200 else {}
        ok = (c.get("disabled") in (False, "0") and c.get("is_scheduled") in (True, "1")
              and str(c.get("action.correlationsearch.enabled")) == "1")
        bad += not ok
        rows.append(f"| {name} | {'on' if c.get('disabled') in (False, '0') else 'off'} | {c.get('cron_schedule', '-')} "
                    f"| {c.get('next_scheduled_time') or '-'} | {'ok' if ok else '**NOT READY**'} |")
    text = ("## Deployed to Enterprise Security\n\n| Detection | Status | Schedule | Next run | Check |\n|---|---|---|---|---|\n"
            + "\n".join(rows) + "\n")
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(text)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
