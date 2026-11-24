#!/usr/bin/env python3
"""Seed the sign-in data behind SO-03 (the notebook password-spray hunt) into the MDL-enabled stack.

    python3 scripts/seed_auth.py --dry-run      # build the events and print the plan; sends nothing
    python3 scripts/seed_auth.py                # send them (refuses if demo_auth already holds events; --force overrides)
    python3 scripts/seed_auth.py --check        # verify the stack holds the story; exit 1 if not

The story is built by scripts/auth_hunt_data.py (120 days of sign-ins, a spray that returns after a quiet spell).
Dual HEC, so each destination gets exactly what it should keep:

  token SPLUNK_HEC_TOKEN_IDX_MDL   index demo_auth (14-day retention)      the last 14 days
  token SPLUNK_HEC_TOKEN_RAW_MDL   raw table ~.federated.demo_auth_raw      all 120 days

Both tokens must already exist with those default indexes. scenarios/so-03-notebook-spray-hunt/fixtures/MDL_SETUP.md
walks through the stack side. Read from .env (the profile suffix _MDL, see scripts/stack_profile.py):

  SPLUNK_HEC_URL_MDL       optional; defaults to https://http-inputs-<host of SPLUNK_WEB_BASE_MDL>
  SPLUNK_HEC_TOKEN_RAW_MDL, SPLUNK_HEC_TOKEN_IDX_MDL
  SPLUNK_REST_URL_MDL, SPLUNK_REST_TOKEN_MDL     the search head: counts demo_auth, and searches the raw table (--check)

TLS verification is off, as on any testing stack. Seed once per stack: the story is anchored to the day it is
generated, and a second seed would add a second, shifted copy to the raw table. --check fails once the second
campaign is no longer recent (about 4 days after seeding). Prints counts only.
"""

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scenarios/so-03-notebook-spray-hunt/fixtures"))
import auth_hunt_data as data  # noqa: E402

INDEX = "demo_auth"
RAW_TABLE = "demo_auth_raw"
BATCH = 2000
CTX = ssl._create_unverified_context()


def dotenv() -> dict:
    env = {}
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def need(env: dict, *keys: str) -> list[str]:
    missing = [k for k in keys if not env.get(k)]
    if missing:
        raise SystemExit("missing from .env: " + ", ".join(missing))
    return [env[k] for k in keys]


def hec_send(url: str, token: str, events: list[dict]) -> None:
    for start in range(0, len(events), BATCH):
        body = "".join(
            json.dumps({"time": e["t"], "host": data.HOST, "source": data.SOURCE, "sourcetype": data.SOURCETYPE,
                        "event": data.line(e)}) for e in events[start:start + BATCH]).encode()
        request = urllib.request.Request(f"{url}/services/collector/event", data=body,
                                         headers={"Authorization": f"Splunk {token}"})
        # The Splunk Cloud HEC gateway sometimes answers 502/503 under load; the batch was not accepted, so resend it.
        for attempt in range(5):
            try:
                with urllib.request.urlopen(request, context=CTX, timeout=120) as response:
                    result = json.load(response)
                break
            except urllib.error.HTTPError as error:
                if error.code not in (502, 503, 504) or attempt == 4:
                    raise SystemExit(f"HEC failed at event {start:,}: HTTP {error.code}")
                time.sleep(5 * (attempt + 1))
        if result.get("code") != 0:
            raise SystemExit(f"HEC rejected a batch: {result}")
        print(f"  sent {min(start + BATCH, len(events)):,} / {len(events):,}", flush=True)


def rest_search(env: dict, spl: str) -> list[dict]:
    url, token = need(env, "SPLUNK_REST_URL_MDL", "SPLUNK_REST_TOKEN_MDL")
    body = urllib.parse.urlencode({"search": spl, "output_mode": "json", "earliest_time": "-30d"}).encode()
    request = urllib.request.Request(f"{url}/services/search/jobs/export", data=body,
                                     headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(request, context=CTX, timeout=300) as response:
        lines = [json.loads(line) for line in response.read().decode().splitlines() if line.strip()]
    return [line["result"] for line in lines if "result" in line]


def hot_stats(env: dict) -> dict:
    rows = rest_search(env, f'search index={INDEX} sourcetype="{data.SOURCETYPE}" | stats count, latest(_time) AS latest, '
                            f'count(eval(src_ip="{data.ATTACKER_IP}")) AS attacker')
    return rows[0] if rows else {"count": "0", "attacker": "0", "latest": "0"}


def raw_suspect(env: dict):
    """The suspect's events in the raw table, through the same search the notebook runs."""
    os.environ.update({"LAKE_MODE": "live", "LAKE_RAW_DATASET": RAW_TABLE, "LAKE_VERIFY": "0",
                       "LAKE_REST_URL": need(env, "SPLUNK_REST_URL_MDL")[0], "LAKE_REST_TOKEN": need(env, "SPLUNK_REST_TOKEN_MDL")[0]})
    import lake
    return lake.search_raw(data.ATTACKER_IP, days=120)


def check(env: dict) -> int:
    problems = []
    # A busy indexer can drop out of one search without a warning; the export endpoint then returns partial counts.
    for attempt in range(3):
        hot = hot_stats(env)
        if int(hot["attacker"]) >= 300 or attempt == 2:
            break
        time.sleep(20)
    age_days = (datetime.now(timezone.utc).timestamp() - float(hot.get("latest") or 0)) / 86400
    print(f"hot index {INDEX}: {int(hot['count']):,} events, {int(hot['attacker']):,} from the suspect, newest {age_days:.1f} days old")
    if int(hot["attacker"]) < 300:
        problems.append("the second campaign is missing from the hot index")
    if age_days > 4:
        problems.append("the newest hot event is older than 4 days; reseed")

    raw = raw_suspect(env)
    first_age = (datetime.now(timezone.utc) - raw["_time"].min()).days if len(raw) else 0
    print(f"raw table {RAW_TABLE}: {len(raw):,} events from the suspect, first seen {first_age} days ago")
    if len(raw) < 600:
        problems.append("the raw table is missing the suspect's history")
    if first_age < 70:
        problems.append("the first campaign (about 78 days ago) is missing from the raw table")
    for problem in problems:
        print(f"PROBLEM: {problem}")
    print("story present" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--force", action="store_true", help="send even if the index or raw table already holds the story")
    args = parser.parse_args()

    events = data.events()
    hot = data.hot(events)
    print(f"story: {data.summary(events)}")
    print(f"index {INDEX} gets {len(hot):,} events; raw table {RAW_TABLE} gets {len(events):,}")
    if args.dry_run:
        print("dry run: nothing sent")
        return 0

    env = dotenv()
    if args.check:
        return check(env)
    token_raw, token_idx = need(env, "SPLUNK_HEC_TOKEN_RAW_MDL", "SPLUNK_HEC_TOKEN_IDX_MDL")
    url = (env.get("SPLUNK_HEC_URL_MDL")
           or f"https://http-inputs-{urllib.parse.urlparse(need(env, 'SPLUNK_WEB_BASE_MDL')[0]).netloc}").rstrip("/")
    if not args.force and int(hot_stats(env)["count"]) > 0:
        raise SystemExit(f"{INDEX} already holds the story; sending again would double it (--force to do it anyway)")
    if not args.force and len(raw_suspect(env)) > 0:
        raise SystemExit(f"{RAW_TABLE} already holds the story; a second, shifted copy would break it (--force to do it anyway)")
    print(f"sending to {INDEX}")
    hec_send(url, token_idx, hot)
    print(f"sending to {RAW_TABLE}")
    hec_send(url, token_raw, events)
    print("done; promote 90 days of the raw table to the analytics table next (MDL_SETUP.md, step 5)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
