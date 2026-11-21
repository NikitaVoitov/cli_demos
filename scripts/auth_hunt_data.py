"""Synthetic sign-in events for SO-03: a low-and-slow password spray hidden in 120 days of ordinary logins.

One generator feeds every consumer, so the hot index, the Machine Data Lake raw table, the shared analytics
table and the offline notebook check all describe the same story:

  * ~250 ordinary sign-ins a day from 403 accounts, each from its own address, about 3 % failures.
  * A corporate VPN egress (VPN_IP): ~900 sign-ins a day from 150 of those accounts and about 8 % failures.
    It fails for as many distinct accounts as the attacker does, but succeeds the rest of the time. It is the
    false positive a rule has to survive.
  * The attacker (ATTACKER_IP) sprays one attempt per account across ~50 accounts a day, all day, so no
    five-minute window comes near the existing alert's 100 failures. It ran for three days about 78 days ago,
    stopped, and returned 9 days ago. One late-night attempt on a privileged service account succeeds.

The hot index keeps 14 days, so it shows only the second campaign. The raw table keeps all 120, so the first one
turns up only there. Only standard library; the same date always gives the same events.

    python3 scripts/auth_hunt_data.py            # prints the story's numbers
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

UTC = timezone.utc

DAYS = 120
HOT_DAYS = 14
ATTACKER_IP = "198.51.100.22"
VPN_IP = "203.0.113.7"
PRIVILEGED = ["svc_backup", "adm_ops", "svc_deploy"]
COMPROMISED = "svc_backup"
USERS = [f"user{n:04d}" for n in range(1, 401)] + PRIVILEGED
CAMPAIGNS = [(-78, -76), (-9, 0)]   # inclusive day offsets from today
SPRAY_ACCOUNTS_PER_DAY = (46, 58)
SOURCETYPE = "demo:auth:lake"
SOURCE = "sso"
HOST = "auth-gateway"
SEED = 20261119


def home_ip(user: str) -> str:
    n = USERS.index(user)
    return f"198.18.{n // 250}.{n % 250 + 1}"


def _work_hours(rng: random.Random) -> float:
    """Seconds into the day: most sign-ins land between 08:00 and 18:00."""
    if rng.random() < 0.8:
        return rng.uniform(8 * 3600, 18 * 3600)
    return rng.uniform(0, 86400)


def events(today: datetime | None = None) -> list[dict]:
    """Every event, oldest first: {t (epoch), src_ip, user, outcome, app, reason}."""
    today = (today or datetime.now(UTC)).replace(hour=0, minute=0, second=0, microsecond=0)
    out: list[dict] = []
    for back in range(DAYS - 1, -1, -1):
        day = today - timedelta(days=back)
        rng = random.Random(f"{SEED}:{day:%Y-%m-%d}")
        base = day.timestamp()

        def add(offset: float, ip: str, user: str, ok: bool, app: str) -> None:
            out.append({"t": round(base + offset, 3), "src_ip": ip, "user": user, "app": app,
                        "outcome": "success" if ok else "fail", "reason": "ok" if ok else "bad_password"})

        for _ in range(250):
            user = rng.choice(USERS)
            add(_work_hours(rng), home_ip(user), user, rng.random() > 0.03, "sso")
        for _ in range(900):
            add(_work_hours(rng), VPN_IP, rng.choice(USERS[:150]), rng.random() > 0.08, "vpn")

        if any(lo <= -back <= hi for lo, hi in CAMPAIGNS):
            targets = rng.sample(USERS, rng.randint(*SPRAY_ACCOUNTS_PER_DAY))
            for i, user in enumerate(targets):
                # One attempt per account, spaced across the whole day with a little jitter.
                add((i + rng.random() * 0.8) * 86400 / len(targets), ATTACKER_IP, user, False, "sso")
            if back == 2:
                add(3 * 3600 + 12 * 60 + 9, ATTACKER_IP, COMPROMISED, True, "sso")
    out.sort(key=lambda e: e["t"])
    return out


def line(e: dict) -> str:
    """The event as a log line. Splunk's default key=value extraction reads it, and so does the raw-table parser."""
    return f"user={e['user']} src_ip={e['src_ip']} outcome={e['outcome']} app={e['app']} reason={e['reason']}"


def hot(evts: list[dict], today: datetime | None = None) -> list[dict]:
    """The slice the Splunk index keeps."""
    today = (today or datetime.now(UTC)).replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff = (today - timedelta(days=HOT_DAYS - 1)).timestamp()
    return [e for e in evts if e["t"] >= cutoff]


def summary(evts: list[dict]) -> dict:
    fails = [e for e in evts if e["outcome"] == "fail"]
    spray = [e for e in evts if e["src_ip"] == ATTACKER_IP]
    return {
        "events": len(evts),
        "failures": len(fails),
        "attacker_events": len(spray),
        "attacker_accounts": len({e["user"] for e in spray}),
        "attacker_first": datetime.fromtimestamp(min(e["t"] for e in spray), UTC).strftime("%Y-%m-%d"),
        "attacker_successes": [e["user"] for e in spray if e["outcome"] == "success"],
    }


if __name__ == "__main__":
    allv = events()
    print("all 120 days:", summary(allv))
    print("hot 14 days: ", summary(hot(allv)))
