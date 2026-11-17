#!/usr/bin/env python3
"""Seed synthetic payments-fraud data for SO-07 into index=demo_payments, then train the demo ML model.

Usage: python3 scripts/seed_fraud.py [--create-index] [--check] [--model-only]

--create-index creates demo_payments across the indexer cluster through the search head's index manager
(`splunkctl index add` only creates it on the search head). If the index exists it removes it instead. Removing
does not empty it: the buckets stay, and recreating the same name brings the old events back. Without the
can_delete role, the only way to start empty is a new index name. It uses SPLUNK_WEB_USER and SPLUNK_WEB_PASSWORD
from .env and the host in ~/.splunkctl/config.yaml.

Data goes in with `| collect` through splunkctl (the HEC token only allows its own index), the same way
CE-01's demo_checkout was loaded. Four sourcetypes cover the last 7 days:

  authentication         logins; three external IPs brute-force a dozen accounts in the last 48 h
  user_access            sessions of the legitimate users only
  merchant_transactions  card payments; 40 accounts with no login history run small card-testing charges
                         from the attacker IPs, and every one is declined with E4051
  bank_transactions      settlements, which carry no merchant_name

Two AI Toolkit models back two saved searches. demo_txn_amount_model (DensityFunction on amount) only flags a
few large legitimate purchases, a quick check that rules one theory out. demo_ip_decline_model (DensityFunction
on declines per source IP) flags the three attacker IPs, which the agent then confirms against logins and
sessions. Prints counts only. Reseed within ~5 days of a take.
"""

import argparse
import base64
import json
import re
import ssl
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = "demo_payments"
DAYS = 7
ATTACK_IPS = ["203.0.113.45", "198.51.100.23", "203.0.113.178"]
COMMON = f"""
| streamstats count AS n
| eval _time = now() - {DAYS} * 86400 + n * ({DAYS} * 86400 / __COUNT__) + (random() % 1000) / 1000
| eval user_id = "user_" . tostring(10000 + random() % 300)
| eval src_ip = "198.18." . tostring(random() % 250) . "." . tostring(random() % 250 + 1)
"""

ATTACK_TIME = "| eval _time = now() - 172800 + n * (165600 / __COUNT__) + (random() % 1000) / 1000"
ATTACK_IP = "| eval src_ip = mvindex(split(\"" + ",".join(ATTACK_IPS) + "\", \",\"), random() % 3)"

SEARCHES = {
    "authentication": (8000, COMMON + """
| eval action = if(random() % 100 < 3, "failure", "success"), app = "online-banking"
| eval _raw = json_object("timestamp", strftime(_time, "%Y-%m-%dT%H:%M:%S.%3N%z"), "user_id", user_id, "src_ip", src_ip, "action", action, "app", app)
| table _time _raw
| collect index=demo_payments sourcetype=authentication source=auth-gateway host=auth-gateway"""),
    "authentication-attack": (900, "| streamstats count AS n\n" + ATTACK_TIME + "\n" + ATTACK_IP + """
| eval user_id = "user_" . tostring(10010 + random() % 12)
| eval action = if(n % 180 == 0, "success", "failure"), app = "online-banking"
| eval _raw = json_object("timestamp", strftime(_time, "%Y-%m-%dT%H:%M:%S.%3N%z"), "user_id", user_id, "src_ip", src_ip, "action", action, "app", app)
| table _time _raw
| collect index=demo_payments sourcetype=authentication source=auth-gateway host=auth-gateway"""),
    "user_access": (6000, COMMON + """
| eval r = random() % 100, page = case(r < 40, "login", r < 70, "view_balance", r < 90, "transfer", true(), "logout")
| eval session_id = substr(md5(user_id . "-" . floor(_time / 1800)), 1, 12), country = mvindex(split("US,US,US,GB,DE,CA", ","), random() % 6)
| eval _raw = json_object("timestamp", strftime(_time, "%Y-%m-%dT%H:%M:%S.%3N%z"), "user_id", user_id, "src_ip", src_ip, "session_id", session_id, "page", page, "country", country)
| table _time _raw
| collect index=demo_payments sourcetype=user_access source=web-portal host=web-portal"""),
    "merchant_transactions": (7000, COMMON + """
| eval m = random() % 6, merchant_name = mvindex(split("Northwind Electronics,Contoso Gift Cards,Fabrikam Travel,Tailspin Grocers,Adventure Works Outdoor,Litware Books", ","), m)
| eval merchant_category = mvindex(split("electronics,gift_cards,travel,grocery,outdoor,books", ","), m)
| eval u1 = (random() % 100000 + 1) / 100001, u2 = (random() % 100000 + 1) / 100001, z = sqrt(-2 * ln(u1)) * cos(2 * pi() * u2)
| eval amount = round(exp(ln(60) + 0.6 * z) * if(n % 997 == 0, 25, 1), 2)
| eval declined = if(random() % 100 < 3, 1, 0), status = if(declined = 1, "declined", "approved")
| eval error_code = if(declined = 1, mvindex(split("E1001,E2002", ","), random() % 2), "")
| eval transaction_id = "txn_" . substr(md5(n . "-" . random()), 1, 10), country = mvindex(split("US,US,US,GB,DE,CA", ","), random() % 6)
| eval _raw = json_object("timestamp", strftime(_time, "%Y-%m-%dT%H:%M:%S.%3N%z"), "transaction_id", transaction_id, "user_id", user_id, "merchant_name", merchant_name, "merchant_category", merchant_category, "amount", amount, "ip_address", src_ip, "country", country, "status", status, "error_code", error_code)
| table _time _raw
| collect index=demo_payments sourcetype=merchant_transactions source=payments-gateway host=payments-gateway"""),
    "merchant_transactions-fraud": (600, "| streamstats count AS n\n" + ATTACK_TIME + "\n" + ATTACK_IP + """
| eval user_id = "user_" . tostring(10900 + random() % 40)
| eval m = random() % 2, merchant_name = mvindex(split("Northwind Electronics,Contoso Gift Cards", ","), m)
| eval merchant_category = mvindex(split("electronics,gift_cards", ","), m)
| eval amount = round(1 + (random() % 2400) / 100, 2), status = "declined", error_code = "E4051"
| eval transaction_id = "txn_" . substr(md5(n . "-" . random()), 1, 10), country = "US"
| eval _raw = json_object("timestamp", strftime(_time, "%Y-%m-%dT%H:%M:%S.%3N%z"), "transaction_id", transaction_id, "user_id", user_id, "merchant_name", merchant_name, "merchant_category", merchant_category, "amount", amount, "ip_address", src_ip, "country", country, "status", status, "error_code", error_code)
| table _time _raw
| collect index=demo_payments sourcetype=merchant_transactions source=payments-gateway host=payments-gateway"""),
    "bank_transactions": (2500, COMMON + """
| eval account_id = "acct_" . substr(md5(user_id), 1, 8), amount = round(exp(ln(300) + 0.7 * ((random() % 1000) / 500 - 1)), 2)
| eval settlement_id = "stl_" . substr(md5(n . "-" . random()), 1, 10), status = if(random() % 100 < 2, "returned", "settled")
| eval _raw = json_object("timestamp", strftime(_time, "%Y-%m-%dT%H:%M:%S.%3N%z"), "settlement_id", settlement_id, "account_id", account_id, "user_id", user_id, "amount", amount, "status", status)
| table _time _raw
| collect index=demo_payments sourcetype=bank_transactions source=core-banking host=core-banking"""),
}

TXNS = f"index={INDEX} sourcetype=merchant_transactions earliest=-{DAYS}d"
PER_IP = (f"{TXNS} | stats count AS txns count(eval(status=\"declined\")) AS declines dc(user_id) AS users "
          "avg(amount) AS avg_amount BY ip_address | eval avg_amount = round(avg_amount, 2)")
# (model, training search, saved search, saved search body, description)
MODELS = [
    ("demo_txn_amount_model",
     f"{TXNS} status=approved | fit DensityFunction amount by merchant_category threshold=0.002 into app:demo_txn_amount_model",
     "demo_txn_amount_outliers",
     f"{TXNS} | apply app:demo_txn_amount_model | where 'IsOutlier(amount)'=1 "
     "| table _time user_id merchant_name merchant_category amount status | sort - amount",
     "Transaction amounts the demo_txn_amount_model DensityFunction model flags as outliers"),
    ("demo_ip_decline_model",
     f"{PER_IP} | fit DensityFunction declines dist=norm threshold=0.01 into app:demo_ip_decline_model",
     "demo_ip_decline_outliers",
     f"{PER_IP} | apply app:demo_ip_decline_model | where 'IsOutlier(declines)'=1 "
     "| table ip_address txns declines users avg_amount | sort - declines",
     "Source IPs whose card declines the demo_ip_decline_model DensityFunction model flags as outliers"),
]


def splunkctl(*args: str, check: bool = True) -> str:
    # splunkctl holds every search job for confirmation; a fixture runs unattended.
    proc = subprocess.run(["splunkctl", "--insecure", "--yes", *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise SystemExit(f"splunkctl {args[0]} {args[1] if len(args) > 1 else ''} failed: {proc.stderr.strip()[:300]}")
    return proc.stdout


def dotenv(key: str) -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"{key} missing from .env")


def create_index() -> None:
    config = (Path.home() / ".splunkctl/config.yaml").read_text()
    host = re.search(r"^\s*host:\s*['\"]?([^'\"\s]+)", config, re.M).group(1).rstrip("/")
    if not host.startswith("http"):
        host = f"https://{host}"
    if not re.search(r":\d+$", host):
        host += ":8089"
    splunkctl("index", "remove", INDEX, check=False)
    auth = base64.b64encode(f"{dotenv('SPLUNK_WEB_USER')}:{dotenv('SPLUNK_WEB_PASSWORD')}".encode()).decode()
    manager = f"{host}/servicesNS/nobody/search/cluster_blaster_indexes/sh_indexes_manager"
    ctx = ssl._create_unverified_context()
    headers = {"Authorization": f"Basic {auth}"}
    try:
        urllib.request.urlopen(urllib.request.Request(f"{manager}/{INDEX}?output_mode=json", headers=headers),
                               context=ctx, timeout=60).close()
        exists = True
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise SystemExit(f"index manager lookup failed: HTTP {error.code} {error.read().decode()[:300]}")
        exists = False
    if exists:
        drop = urllib.request.Request(f"{manager}/{INDEX}?output_mode=json", method="DELETE", headers=headers)
        try:
            urllib.request.urlopen(drop, context=ctx, timeout=60).close()
        except urllib.error.HTTPError as error:
            raise SystemExit(f"index manager could not remove {INDEX}: HTTP {error.code} {error.read().decode()[:300]}")
        print(f"index {INDEX} removed (its buckets stay, so recreating this name restores the old events)")
        return
    body = urllib.parse.urlencode({"name": INDEX, "datatype": "event", "maxGlobalDataSizeMB": 500, "maxGlobalRawDataSizeMB": 0,
                                   "frozenTimePeriodInSecs": 2592000}).encode()
    req = urllib.request.Request(f"{manager}?output_mode=json", data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60):
            print(f"index {INDEX} created across the indexer cluster")
    except urllib.error.HTTPError as error:
        raise SystemExit(f"index manager rejected {INDEX}: HTTP {error.code} {error.read().decode()[:300]}")


def counts() -> dict:
    out = splunkctl("search", f"| tstats count WHERE index={INDEX} earliest=-{DAYS + 1}d BY sourcetype", "-o", "json")
    rows = json.loads(out or "[]")
    rows = rows.get("results", rows) if isinstance(rows, dict) else rows
    return {r["sourcetype"]: int(r["count"]) for r in rows}


def train_models() -> None:
    for model, fit, saved, body, description in MODELS:
        splunkctl("search", fit, "--max-time", "300", "-o", "json")
        splunkctl("saved-search", "remove", saved, check=False)
        splunkctl("saved-search", "add", saved, "--search", body, "--param", f"description={description}",
                  "--param", f"dispatch.earliest_time=-{DAYS}d", "--param", "dispatch.latest_time=now", "-o", "json")
        splunkctl("acl", "set", saved, "--type", "saved-search", "--sharing", "app", "--owner", "nobody",
                  "--read", "*", "-o", "json")
        print(f"model {model} trained; saved search {saved} shared in the search app")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--create-index", action="store_true", help="create the index cluster-wide and exit")
    p.add_argument("--check", action="store_true", help="print event counts and exit")
    p.add_argument("--model-only", action="store_true", help="retrain the models and recreate their saved searches")
    args = p.parse_args()
    if args.create_index:
        create_index()
        return
    if args.check:
        print(counts() or f"index={INDEX} is empty")
        return
    if not args.model_only:
        if counts():
            raise SystemExit(f"index={INDEX} already has events; seeding again would double them")
        for name, (count, body) in SEARCHES.items():
            spl = f"| makeresults count={count}" + body.replace("__COUNT__", str(count))
            splunkctl("search", spl, "--max-time", "600", "-o", "json")
            print(f"seeded {name}: {count} events")
    train_models()
    print(counts())


if __name__ == "__main__":
    main()
