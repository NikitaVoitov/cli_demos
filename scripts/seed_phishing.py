#!/usr/bin/env python3
"""Seed the synthetic mail, proxy, endpoint, and sign-in data behind SO-08 (closed-loop phishing containment).

    python3 scripts/seed_phishing.py --create-index   # create index=demo_soc across the indexer cluster
    python3 scripts/seed_phishing.py --dry-run        # print the story and the plan; sends nothing
    python3 scripts/seed_phishing.py                  # seed (refuses if the index already holds events)
    python3 scripts/seed_phishing.py --check          # confirm the stack holds the story; exit 1 if not

Data goes in with `| collect` through splunkctl, like scripts/seed_fraud.py. Seven days of background traffic for
60 employees of acme-corp.example, plus the story, anchored at 09:42 UTC the day before seeding (the "Sent" time in
the forwarded report in the demo security mailbox):

  email:gateway     the lookalike invoice (ap-notices@northwind-billing.example) reaches all 14 people on the
                    finance list; SPF and DMARC fail; the real vendor, northwindtraders.example, mails normally
  proxy:web         3 recipients open the invoice link; one of them posts to the portal's verify page
  endpoint:process  Outlook opens the browser on those 3 laptops and nothing else starts: no payload ran
  identity:signin   40 minutes after the post, a sign-in as that user from a new IP fails MFA

The domain never appears in proxy logs before the campaign. Every name, domain, and address is fictitious
(.example domains, documentation and benchmark IP ranges). The laptop is `device`, so it never mixes with
Splunk's own `host` field. Reseed within about 5 days of a take, together with
the report email, so the dates still match. Prints counts only.
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.policy import SMTP
from email.utils import format_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from seed_fraud import create_index, splunkctl  # noqa: E402

INDEX = "demo_soc"
DAYS = 7
CORP = "acme-corp.example"
PHISH_DOMAIN = "northwind-billing.example"
PHISH_SENDER = f"ap-notices@{PHISH_DOMAIN}"
PHISH_SUBJECT = "Invoice INV-88213 overdue \u2013 action required"
PHISH_URL = f"https://{PHISH_DOMAIN}/portal/inv/88213"
PHISH_MESSAGE_ID = f"<88213.{PHISH_SENDER}>"
SENDING_IP = "203.0.113.66"
ATTACKER_IP = "198.51.100.77"

FINANCE = ["dana.lee", "mark.chen", "priya.shah", "tom.alvarez", "olivia.brooks", "sam.okafor", "grace.kim",
           "luis.romero", "nina.patel", "ethan.wu", "maria.garcia", "ben.carter", "aisha.khan", "jack.ross"]
# Minutes after delivery each one opened the link; priya.shah also submitted the portal's form.
CLICKS = {"mark.chen": 11, "priya.shah": 23, "tom.alvarez": 41}
SUBMITTED = "priya.shah"
EMPLOYEES = FINANCE + [
    "alex.morgan", "jordan.blake", "casey.nguyen", "riley.adams", "taylor.reed", "morgan.hayes", "jamie.fox",
    "drew.parker", "quinn.ellis", "avery.cole", "cameron.price", "skyler.ward", "reese.long", "parker.gray",
    "logan.bell", "harper.diaz", "emerson.ruiz", "rowan.hart", "sage.flores", "blake.turner", "kendall.ross",
    "hayden.cruz", "elliot.shaw", "finley.kerr", "dakota.lane", "peyton.webb", "marley.stone", "remy.fields",
    "spencer.vale", "arden.moss", "lennox.hale", "shiloh.page", "tatum.reyes", "oakley.dunn", "jules.hart",
    "noel.banks", "robin.chase", "sasha.wolfe", "kai.brennan", "milan.ortiz", "rory.quinn", "ari.santos",
    "devon.knox", "lee.harmon", "toby.mills", "zion.park"]
VENDORS = ["billing@northwindtraders.example", "payroll@contoso-payroll.example", "benefits@fabrikam-hr.example",
           "bookings@tailspin-travel.example", "support@litware-it.example", "news@adventure-works.example"]
SITES = {"intranet.acme-corp.example": "Business", "sharepoint.acme-corp.example": "Business",
         "portal.northwindtraders.example": "Business", "docs.contoso.example": "Business",
         "cdn.fabrikam.example": "Content Delivery", "news.example.com": "News", "search.example.net": "Search Engines",
         "crm.litware.example": "Business", "travel.tailspin.example": "Travel"}
APPS = {"outlook.exe": "explorer.exe", "msedge.exe": "explorer.exe", "teams.exe": "explorer.exe",
        "excel.exe": "outlook.exe", "onedrive.exe": "explorer.exe", "winword.exe": "outlook.exe"}


def device(user: str) -> tuple[str, str]:
    """The laptop and internal address a user always appears on; the same formula is used in SPL below."""
    h = hashlib.md5(user.encode()).hexdigest()
    return f"LT-{h[:6].upper()}", f"198.18.{int(h[:2], 16)}.{int(h[2:4], 16) % 250 + 1}"


def anchor() -> datetime:
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return today - timedelta(days=1) + timedelta(hours=9, minutes=42)


def iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%S.000+0000")


def story(t0: datetime) -> dict[str, list[tuple[datetime, dict]]]:
    """The campaign and what followed, event by event."""
    out: dict[str, list[tuple[datetime, dict]]] = {"email:gateway": [], "proxy:web": [], "endpoint:process": [],
                                                    "identity:signin": []}
    for i, user in enumerate(FINANCE):
        t = t0 + timedelta(seconds=2 * i)
        out["email:gateway"].append((t, {
            "message_id": "msg-88213-" + hashlib.md5(user.encode()).hexdigest()[:8], "internet_message_id": PHISH_MESSAGE_ID,
            "direction": "inbound", "sender": PHISH_SENDER, "sender_domain": PHISH_DOMAIN, "recipient": f"{user}@{CORP}",
            "subject": PHISH_SUBJECT, "action": "delivered", "spf": "fail", "dkim": "none", "dmarc": "fail",
            "src_ip": SENDING_IP, "urls": [PHISH_URL], "attachment_count": 0}))
    report = t0 + timedelta(minutes=52)
    out["email:gateway"].append((report, {
        "message_id": "msg-report-88213", "internet_message_id": f"<report-88213.dana.lee@{CORP}>", "direction": "internal",
        "sender": f"dana.lee@{CORP}", "sender_domain": CORP, "recipient": f"security@{CORP}", "subject": f"FW: {PHISH_SUBJECT}",
        "action": "delivered", "spf": "pass", "dkim": "pass", "dmarc": "pass", "src_ip": device("dana.lee")[1],
        "urls": [PHISH_URL], "attachment_count": 0}))
    for user, minutes in CLICKS.items():
        host, ip = device(user)
        t = t0 + timedelta(minutes=minutes)
        out["endpoint:process"].append((t - timedelta(seconds=1), {
            "device": host, "user": user, "process": "msedge.exe", "parent_process": "outlook.exe",
            "command_line": f'"msedge.exe" --single-argument {PHISH_URL}', "action": "process_start"}))
        out["proxy:web"].append((t, {
            "user": user, "src_ip": ip, "device": host, "http_method": "GET", "url": PHISH_URL, "domain": PHISH_DOMAIN,
            "status": 200, "action": "allowed", "category": "Newly Registered Domain", "bytes_out": 612, "bytes_in": 48211,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edg/130.0"}))
        # Each clicker was already signed in that morning, so there is a live session to revoke.
        out["identity:signin"].append((t0 - timedelta(minutes=90 - 7 * len(user) % 30), {
            "user": user, "src_ip": ip, "app": "Office 365", "result": "success", "failure_reason": "", "mfa": "satisfied",
            "session_id": "sess-" + hashlib.md5((user + "morning").encode()).hexdigest()[:10], "country": "US"}))
    host, ip = device(SUBMITTED)
    submit = t0 + timedelta(minutes=CLICKS[SUBMITTED] + 2)
    out["proxy:web"].append((submit, {
        "user": SUBMITTED, "src_ip": ip, "device": host, "http_method": "POST", "url": f"https://{PHISH_DOMAIN}/portal/verify",
        "domain": PHISH_DOMAIN, "status": 302, "action": "allowed", "category": "Newly Registered Domain",
        "bytes_out": 1840, "bytes_in": 920, "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edg/130.0"}))
    out["identity:signin"].append((submit + timedelta(minutes=40), {
        "user": SUBMITTED, "src_ip": ATTACKER_IP, "app": "Office 365", "result": "failure", "failure_reason": "MFA denied",
        "mfa": "denied", "session_id": "", "country": "NL"}))
    return out


def spl_list(values) -> str:
    return ",".join(values)


EMP = spl_list(EMPLOYEES)
COMMON = f"""
| streamstats count AS n
| eval _time = now() - {DAYS} * 86400 + n * ({DAYS} * 86400 / __COUNT__) + (random() % 1000) / 1000
| eval user = mvindex(split("{EMP}", ","), random() % {len(EMPLOYEES)}), h = md5(user)
| eval host = "LT-" . upper(substr(h, 1, 6))
| eval src_ip = "198.18." . tostring(tonumber(substr(h, 1, 2), 16)) . "." . tostring(tonumber(substr(h, 3, 2), 16) % 250 + 1)
"""
TS = 'strftime(_time, "%Y-%m-%dT%H:%M:%S.%3N%z")'
BACKGROUND = {
    "email:gateway": (3500, COMMON + f"""
| eval v = random() % {len(VENDORS)}, sender = mvindex(split("{spl_list(VENDORS)}", ","), v), sender_domain = mvindex(split(sender, "@"), 1)
| eval spam = if(random() % 100 < 3, 1, 0), action = if(spam = 1, "quarantined", "delivered")
| eval subject = case(v = 0, "Your monthly statement from Northwind Traders", v = 1, "Payslip available", v = 2, "Benefits enrollment reminder", v = 3, "Trip confirmation", v = 4, "Ticket update", true(), "This week at Adventure Works")
| eval _raw = json_object("timestamp", {TS}, "message_id", "msg-" . substr(md5(n . user), 1, 12), "internet_message_id", "<" . substr(md5(n . "id"), 1, 16) . "@" . sender_domain . ">", "direction", "inbound", "sender", sender, "sender_domain", sender_domain, "recipient", user . "@{CORP}", "subject", subject, "action", action, "spf", if(spam = 1, "softfail", "pass"), "dkim", if(spam = 1, "none", "pass"), "dmarc", if(spam = 1, "fail", "pass"), "src_ip", "192.0.2." . tostring(10 + v), "urls", json_array(), "attachment_count", random() % 2)
| table _time _raw
| collect index={INDEX} sourcetype=email:gateway source=mail-gateway host=mail-gateway"""),
    "proxy:web": (8000, COMMON + f"""
| eval s = random() % {len(SITES)}, domain = mvindex(split("{spl_list(SITES)}", ","), s), category = mvindex(split("{spl_list(SITES.values())}", ","), s)
| eval method = if(random() % 10 = 0, "POST", "GET"), status = if(random() % 50 = 0, 404, 200)
| eval _raw = json_object("timestamp", {TS}, "user", user, "src_ip", src_ip, "device", host, "http_method", method, "url", "https://" . domain . "/" . substr(md5(n . "p"), 1, 8), "domain", domain, "status", status, "action", "allowed", "category", category, "bytes_out", 300 + random() % 2000, "bytes_in", 2000 + random() % 90000, "user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edg/130.0")
| table _time _raw
| collect index={INDEX} sourcetype=proxy:web source=web-proxy host=web-proxy"""),
    "endpoint:process": (5000, COMMON + f"""
| eval a = random() % {len(APPS)}, process = mvindex(split("{spl_list(APPS)}", ","), a), parent_process = mvindex(split("{spl_list(APPS.values())}", ","), a)
| eval _raw = json_object("timestamp", {TS}, "device", host, "user", user, "process", process, "parent_process", parent_process, "command_line", "\\"" . process . "\\"", "action", "process_start")
| table _time _raw
| collect index={INDEX} sourcetype=endpoint:process source=edr host=edr"""),
    "identity:signin": (3000, COMMON + f"""
| eval app = mvindex(split("Office 365,VPN,Expense portal", ","), random() % 3), fail = if(random() % 100 < 2, 1, 0)
| eval _raw = json_object("timestamp", {TS}, "user", user, "src_ip", src_ip, "app", app, "result", if(fail = 1, "failure", "success"), "failure_reason", if(fail = 1, "Wrong password", ""), "mfa", if(fail = 1, "not_reached", "satisfied"), "session_id", "sess-" . substr(md5(user . floor(_time / 28800)), 1, 10), "country", "US")
| table _time _raw
| collect index={INDEX} sourcetype=identity:signin source=identity-provider host=identity-provider"""),
}
SOURCES = {"email:gateway": "mail-gateway", "proxy:web": "web-proxy", "endpoint:process": "edr",
           "identity:signin": "identity-provider"}


def story_spl(sourcetype: str, events: list[tuple[datetime, dict]]) -> str:
    rows = [{"t": t.timestamp(), "raw": json.dumps({"timestamp": iso(t), **fields})} for t, fields in events]
    data = json.dumps(rows).replace("\\", "\\\\").replace('"', '\\"')
    source = SOURCES[sourcetype]
    return (f'| makeresults format=json data="{data}" | eval _time = t, _raw = raw | table _time _raw '
            f"| collect index={INDEX} sourcetype={sourcetype} source={source} host={source}")


def counts() -> dict:
    out = splunkctl("search", f"| tstats count WHERE index={INDEX} earliest=-{DAYS + 1}d BY sourcetype", "-o", "json")
    rows = json.loads(out or "[]")
    rows = rows.get("results", rows) if isinstance(rows, dict) else rows
    return {r["sourcetype"]: int(r["count"]) for r in rows}


def check() -> int:
    spl = (f'search index={INDEX} earliest=-{DAYS}d ((sourcetype=email:gateway internet_message_id="{PHISH_MESSAGE_ID}") '
           f'OR (sourcetype=proxy:web domain={PHISH_DOMAIN}) OR (sourcetype=identity:signin src_ip={ATTACKER_IP})) '
           '| stats count(eval(sourcetype="email:gateway")) AS delivered '
           'dc(eval(if(sourcetype="proxy:web", user, null()))) AS clickers '
           'count(eval(http_method="POST")) AS posts count(eval(sourcetype="identity:signin")) AS attacker_signins '
           'min(_time) AS first')
    rows = json.loads(splunkctl("search", spl, "-o", "json") or "[]")
    rows = rows.get("results", rows) if isinstance(rows, dict) else rows
    row = rows[0] if rows else {}
    got = {k: int(float(row.get(k, 0) or 0)) for k in ("delivered", "clickers", "posts", "attacker_signins")}
    age = (datetime.now(timezone.utc).timestamp() - float(row.get("first") or 0)) / 86400
    print(f"{counts()}\nstory: {got}, campaign {age:.1f} days old")
    want = {"delivered": len(FINANCE), "clickers": len(CLICKS), "posts": 1, "attacker_signins": 1}
    problems = [f"{k} is {got[k]}, expected {v}" for k, v in want.items() if got[k] != v]
    if age > 5:
        problems.append("the campaign is more than 5 days old; reseed, and resend the report email")
    for problem in problems:
        print(f"PROBLEM: {problem}")
    print("story present" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


def report_eml(t0: datetime) -> bytes:
    """Dana Lee's report as a received message. Outlook for Mac imports an .eml dragged onto a folder with its own
    From header; outlook.com can only send as the mailbox itself."""
    report, sent = t0 + timedelta(minutes=52), t0.strftime("%A, %B %-d, %Y %-I:%M %p (UTC)")
    forwarded = [("From", f"Northwind Billing &lt;{PHISH_SENDER}&gt;"), ("Sent", sent), ("To", f"dana.lee@{CORP}"),
                 ("Subject", PHISH_SUBJECT), ("Message-ID", PHISH_MESSAGE_ID.replace("<", "&lt;").replace(">", "&gt;"))]
    note = ("Hi Security team,\n\nThis looks suspicious. I don't recognize Northwind Billing, and the link asks me to sign "
            "in to see the invoice. I didn't click it. A few people on the finance team got the same email.\n\nThanks,\nDana")
    lure = ("Dear customer,\n\nOur records show that invoice INV-88213 for $18,440.00 is now 14 days overdue. To avoid a "
            "late fee and a hold on your account, please review and settle the invoice today.\n\n"
            f"View the invoice: {PHISH_URL}\n\nYou will be asked to confirm your company sign-in to open the document.\n\n"
            "Accounts Payable Notices\nNorthwind Billing")
    para = lambda text: "".join(f"<p>{block.replace(chr(10), '<br>')}</p>" for block in text.split("\n\n"))
    html = (f'<div style="font-family:Segoe UI,Arial,sans-serif;font-size:14px">{para(note)}<hr>'
            f'<p style="color:#555">{"<br>".join(f"<b>{k}:</b> {v}" for k, v in forwarded)}</p>'
            + para(lure).replace(PHISH_URL, f'<a href="{PHISH_URL}">{PHISH_URL}</a>') + "</div>")
    text = note + "\n\n-----\n" + "\n".join(f"{k}: {v}" for k, v in forwarded).replace("&lt;", "<").replace("&gt;", ">") \
        + "\n\n" + lure
    msg = EmailMessage()
    msg["From"] = f"Dana Lee <dana.lee@{CORP}>"
    msg["To"] = f"Security Team <security@{CORP}>"
    msg["Subject"] = f"FW: {PHISH_SUBJECT}"
    msg["Date"] = format_datetime(report)
    msg["Message-ID"] = f"<report-88213.dana.lee@{CORP}>"
    msg["X-Unsent"] = "0"
    # Outlook for Mac mangles quoted-printable soft line breaks on import, so the body goes in as base64 with CRLFs.
    msg.set_content(text, cte="base64")
    msg.add_alternative(html, subtype="html", cte="base64")
    return msg.as_bytes(policy=SMTP)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--create-index", action="store_true", help="create the index cluster-wide and exit")
    p.add_argument("--report-eml", type=Path, metavar="FILE",
                   help="write Dana Lee's report email for today's anchor (run on the day you seed) and exit")
    p.add_argument("--dry-run", action="store_true", help="print the story and the plan; send nothing")
    p.add_argument("--check", action="store_true", help="confirm the stack holds the story")
    args = p.parse_args()
    if args.create_index:
        create_index(INDEX)
        return 0
    if args.check:
        return check()
    if args.report_eml:
        args.report_eml.parent.mkdir(parents=True, exist_ok=True)
        args.report_eml.write_bytes(report_eml(anchor()))
        print(f"wrote {args.report_eml}; drag it onto the Phishing reports folder in Outlook for Mac")
        return 0

    t0 = anchor()
    events = story(t0)
    print(f"campaign delivered {iso(t0)}; story events {sum(map(len, events.values()))}; "
          f"background {sum(c for c, _ in BACKGROUND.values()):,} over {DAYS} days")
    for sourcetype, rows in events.items():
        print(f"  {sourcetype:<17} {len(rows)} story events")
    if args.dry_run:
        print("dry run: nothing sent")
        return 0
    if counts():
        raise SystemExit(f"index={INDEX} already has events; seeding again would double them")
    for sourcetype, (count, body) in BACKGROUND.items():
        splunkctl("search", f"| makeresults count={count}" + body.replace("__COUNT__", str(count)), "--max-time", "600", "-o", "json")
        print(f"seeded background {sourcetype}: {count:,}")
    for sourcetype, rows in events.items():
        splunkctl("search", story_spl(sourcetype, rows), "--max-time", "300", "-o", "json")
        print(f"seeded story {sourcetype}: {len(rows)}")
    return check()


if __name__ == "__main__":
    sys.exit(main())
