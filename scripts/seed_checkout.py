#!/usr/bin/env python3
"""Seed synthetic checkout events for CE-01 into the demo_checkout index via HEC.

Usage: python3 scripts/seed_checkout.py [--hours 48] [--per-minute 30] [--dry-run]

Reads SPLUNK_HEC_URL and SPLUNK_DEMO_HEC_TOKEN (scoped to demo_checkout) from .env.
Prints counts only.
"""

import argparse
import json
import math
import random
import ssl
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = "demo_checkout"
SOURCETYPE = "checkout"
BATCH = 500

REGIONS = [("us-east-1", 0.40, 1.00), ("us-west-2", 0.25, 1.05), ("eu-west-1", 0.25, 1.10), ("ap-southeast-1", 0.10, 1.35)]
ENDPOINTS = [("POST /checkout", 0.60, 1.0), ("POST /checkout/confirm", 0.30, 1.4), ("GET /checkout/status", 0.10, 0.35)]
METHODS = [("card", 0.70), ("wallet", 0.22), ("bank", 0.08)]


def env(key: str) -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"{key} missing from .env")


def pick(options):
    r, acc = random.random(), 0.0
    for opt in options:
        acc += opt[1]
        if r <= acc:
            return opt
    return options[-1]


def event(ts: float, now: float) -> dict:
    region, _, region_factor = pick(REGIONS)
    endpoint, _, endpoint_factor = pick(ENDPOINTS)
    method = pick(METHODS)[0]
    hour = time.gmtime(ts).tm_hour
    diurnal = 1.0 + 0.25 * math.sin((hour - 9) / 24 * 2 * math.pi)
    incident = region == "eu-west-1" and now - 5 * 3600 <= ts <= now - 3 * 3600
    latency = random.lognormvariate(math.log(170), 0.45) * region_factor * endpoint_factor * diurnal
    if incident:
        latency *= random.uniform(2.8, 4.2)
    error_5xx = 0.045 if incident else 0.004
    r = random.random()
    status = random.choice([502, 503, 504]) if r < error_5xx else random.choice([400, 402, 409]) if r < error_5xx + 0.015 else 200
    return {
        "time": round(ts, 3),
        "host": f"checkout-api-{random.randint(1, 6):02d}",
        "source": "checkout-api",
        "sourcetype": SOURCETYPE,
        "index": INDEX,
        "event": {
            "service": "checkout-api",
            "region": region,
            "endpoint": endpoint,
            "status": status,
            "latency_ms": int(latency),
            "payment_method": method,
            "amount_usd": round(random.lognormvariate(math.log(48), 0.8), 2),
            "trace_id": f"{random.getrandbits(64):016x}",
        },
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--hours", type=float, default=48)
    p.add_argument("--per-minute", type=int, default=30)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    url = env("SPLUNK_HEC_URL").rstrip("/")
    if not url.endswith("/services/collector/event"):
        url += "/services/collector/event"
    token = env("SPLUNK_DEMO_HEC_TOKEN")
    ctx = ssl._create_unverified_context()

    random.seed(20261116)
    now = time.time()
    start = now - args.hours * 3600
    events = []
    t = start
    while t < now:
        rate = args.per_minute / 60
        t += random.expovariate(rate)
        events.append(event(t, now))
    print(f"generated {len(events)} events over {args.hours} h")
    if args.dry_run:
        print(json.dumps(events[0], indent=2))
        return

    sent = 0
    for i in range(0, len(events), BATCH):
        body = "\n".join(json.dumps(e) for e in events[i : i + BATCH]).encode()
        req = urllib.request.Request(url, data=body, headers={"Authorization": f"Splunk {token}"})
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            reply = json.loads(resp.read())
            if reply.get("code") != 0:
                raise SystemExit(f"HEC rejected batch {i // BATCH}: {reply}")
        sent += len(events[i : i + BATCH])
    print(f"sent {sent} events to index={INDEX}")


if __name__ == "__main__":
    main()
