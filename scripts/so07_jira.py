#!/usr/bin/env python3
"""Jira fixtures for SO-07 on the personal demo site (never a corporate site).

  python3 scripts/so07_jira.py project   # create the SOC project if it is missing
  python3 scripts/so07_jira.py reset     # retire leftover tickets, keep or recreate the six alert tickets
  python3 scripts/so07_jira.py latest    # print the key of the newest follow-up ticket (for the screenshot)

Reads JIRA_SITE, JIRA_EMAIL, and JIRA_TOKEN from .env. Prints keys and counts only.
"""

import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = "SOC"
LABEL = "so07-demo"
BLOCKED_SITES = {"splunk.atlassian.net"}

ALERTS = [
    ("Abnormal user behavior: spike in declined card payments", "High", """
Declined card payments rose well above baseline in the last 48 hours, concentrated on two partner merchants:
Northwind Electronics and Contoso Gift Cards.

Splunk data
- index=demo_payments sourcetype=merchant_transactions
- fields: user_id, merchant_name, amount, status, error_code, ip_address
- window: last 7 days"""),
    ("Brute-force login attempts from external IPs", "High", """
Hundreds of failed logins against a small set of online-banking accounts, a few of them followed by a success.

Splunk data
- index=demo_payments sourcetype=authentication
- fields: user_id, src_ip, action
- window: last 7 days"""),
    ("Partner merchants report card-testing complaints", "Medium", """
Northwind Electronics and Contoso Gift Cards report bursts of small card charges they believe are card testing.

Splunk data
- index=demo_payments sourcetype=merchant_transactions
- fields: merchant_name, amount, status, error_code
- window: last 7 days"""),
    ("Unusual session activity after failed logins", "Medium", """
Session volume looks normal, but the auth team asks whether any accounts transact without logging in.

Splunk data
- index=demo_payments sourcetype=user_access
- fields: user_id, src_ip, session_id, page
- window: last 7 days"""),
    ("Settlement returns above normal for partner merchants", "Low", """
Returned settlements are slightly above normal this week. This data has no merchant_name field.

Splunk data
- index=demo_payments sourcetype=bank_transactions
- fields: account_id, user_id, amount, status
- window: last 7 days"""),
    ("Printer offline on floor 3", "Low", """
Facilities report the floor 3 printer is offline. No Splunk data is attached to this alert."""),
]


def env(key: str) -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"{key} missing from .env")


SITE = env("JIRA_SITE").removeprefix("https://").rstrip("/")
if SITE in BLOCKED_SITES or not SITE.endswith(".atlassian.net"):
    raise SystemExit("JIRA_SITE must be the personal demo site, not a corporate one")
AUTH = base64.b64encode(f"{env('JIRA_EMAIL')}:{env('JIRA_TOKEN')}".encode()).decode()


def call(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"https://{SITE}{path}",
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Basic {AUTH}", "Accept": "application/json", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return {"_status": 404}
        raise SystemExit(f"{method} {path} failed with HTTP {error.code}: {error.read().decode()[:300]}")


def search(jql: str) -> list[dict]:
    return call("POST", "/rest/api/3/search/jql", {"jql": jql, "fields": ["summary", "labels", "created", "status"], "maxResults": 100}).get("issues", [])


def retire(issue: dict) -> None:
    """The SOC project cannot delete issues; close leftovers so they leave the open-alert search."""
    labels = sorted(set(issue.get("fields", {}).get("labels", []) + ["so07-retired"]))
    call("PUT", f"/rest/api/3/issue/{issue['key']}", {"fields": {"labels": labels}})
    trans = call("GET", f"/rest/api/3/issue/{issue['key']}/transitions").get("transitions", [])
    done = next((t["id"] for t in trans if t["name"] == "Done"), None)
    if done:
        call("POST", f"/rest/api/3/issue/{issue['key']}/transitions", {"transition": {"id": done}})


def ensure_project() -> None:
    if call("GET", f"/rest/api/3/project/{PROJECT}").get("_status") != 404:
        print(f"project {PROJECT} exists")
        return
    me = call("GET", "/rest/api/3/myself")
    call("POST", "/rest/api/3/project", {
        "key": PROJECT, "name": "SOC alerts", "projectTypeKey": "software",
        "projectTemplateKey": "com.pyxis.greenhopper.jira:gh-simplified-kanban-classic",
        "leadAccountId": me["accountId"], "assigneeType": "PROJECT_LEAD",
    })
    print(f"project {PROJECT} created")


def reset() -> None:
    # This project cannot delete issues. Close leftover follow-ups and keep the six demo alerts.
    live = []
    retired = 0
    for issue in search(f"project = {PROJECT}"):
        labels = set(issue.get("fields", {}).get("labels", []))
        status = issue.get("fields", {}).get("status", {}).get("name", "")
        if {"alert", LABEL} <= labels and "so07-retired" not in labels and status != "Done":
            live.append(issue)
        else:
            retire(issue)
            retired += 1
    # Severity shows as the Jira priority, so the alert list reads like a triage queue.
    severity = {summary: level for summary, level, _ in ALERTS}
    for issue in live:
        level = severity.get(issue["fields"]["summary"])
        if level:
            call("PUT", f"/rest/api/3/issue/{issue['key']}", {"fields": {"priority": {"name": level}}})
    created = []
    needed = ALERTS[len(live):]
    for summary, level, description in needed:
        created.append(call("POST", "/rest/api/2/issue", {"fields": {
            "project": {"key": PROJECT}, "issuetype": {"name": "Task"}, "summary": summary,
            "priority": {"name": level},
            "description": f"Severity: {level}\n{description.strip()}", "labels": ["alert", LABEL],
        }})["key"])
    kept = [i["key"] for i in live]
    print(f"retired {retired}; kept alerts {', '.join(kept) or '(none)'}; created {', '.join(created) or '(none)'}")


def latest() -> None:
    issues = search(f"project = {PROJECT} AND labels = follow-up ORDER BY created DESC")
    if not issues:
        issues = search(f"project = {PROJECT} AND labels != alert AND labels != so07-retired ORDER BY created DESC")
    if not issues:
        raise SystemExit("no follow-up ticket yet")
    print(issues[0]["key"])


if __name__ == "__main__":
    commands = {"project": ensure_project, "reset": reset, "latest": latest}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        raise SystemExit(__doc__)
    commands[sys.argv[1]]()
