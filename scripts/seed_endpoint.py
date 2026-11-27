#!/usr/bin/env python3
"""Seed the endpoint data behind SO-05's noise check: a quiet fleet plus a nightly purple-team run.

    python3 scripts/seed_endpoint.py --dry-run     # build the events and print the plan; sends nothing
    python3 scripts/seed_endpoint.py               # send every night of the last 14 days that isn't there yet
    python3 scripts/seed_endpoint.py --check       # verify the last 7 days hold the story; exit 1 if not

index=demo_endpoint, Sysmon EventID 1 (process creation) as XmlWinEventLog, parsed by the Splunk Add-on for Sysmon
into the Endpoint.Processes data model. Each UTC night of the last 14 days holds:

  fleet         ~40 ordinary process starts on five workstations and two servers, including an approved ProcDump
                of a hung IIS worker (w3wp.exe, not LSASS)
  purple team   at 03:00 UTC on PT-LAB-01.acme.example, svc_purpleteam runs the Atomic Red Team T1003.001 tests
                that the baseline detections already exclude (ProcDump of LSASS, Mimikatz) plus the comsvcs.dll
                MiniDump test (PowerShell wrapper and rundll32), which a new comsvcs detection catches

Events are cloned from Splunk's attack_data (T1003.001, Atomic Red Team, Sysmon), cached under .captures/cache, with
host, account, time, and process IDs rewritten. Every name is fictitious (acme.example). Deterministic per night, so
rerunning only fills missing nights. Sends with SPLUNK_HEC_URL and SPLUNK_HEC_TOKEN_DAC from .env (the dac_ci HEC
token, whose allowed indexes include demo_endpoint); checks with splunkctl. Prints counts only.
"""

import argparse
import hashlib
import json
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = "demo_endpoint"
DAYS = 14
ATTACK_DATA = ("https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/"
               "T1003.001/atomic_red_team/windows-sysmon.log")
CACHE = ROOT / ".captures/cache/attack_data_T1003.001_windows-sysmon.log"
SOURCE = "XmlWinEventLog:Microsoft-Windows-Sysmon/Operational"
LAB = ("PT-LAB-01.acme.example", r"ACME\svc_purpleteam")
FLEET = [("WS-0142.acme.example", r"ACME\jlee"), ("WS-0177.acme.example", r"ACME\mgarcia"),
         ("WS-0203.acme.example", r"ACME\aokafor"), ("WS-0219.acme.example", r"ACME\pnovak"),
         ("WS-0231.acme.example", r"ACME\tchen"), ("IIS-03.acme.example", r"ACME\svc_iisadmin"),
         ("FS-01.acme.example", r"NT AUTHORITY\SYSTEM")]
EVERYDAY = [
    (r"C:\Program Files\Google\Chrome\Application\chrome.exe", r'"C:\Program Files\Google\Chrome\Application\chrome.exe" --type=renderer', r"C:\Windows\explorer.exe"),
    (r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE", r'"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE"', r"C:\Windows\explorer.exe"),
    (r"C:\Windows\System32\rundll32.exe", r'"C:\Windows\System32\rundll32.exe" shell32.dll,Control_RunDLL desk.cpl', r"C:\Windows\explorer.exe"),
    (r"C:\Windows\System32\rundll32.exe", r'"C:\Windows\System32\rundll32.exe" printui.dll,PrintUIEntry /il', r"C:\Windows\explorer.exe"),
    (r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe", r'"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile Get-Service', r"C:\Windows\explorer.exe"),
    (r"C:\Windows\System32\cmd.exe", r'"C:\Windows\system32\cmd.exe" /c "ipconfig /all"', r"C:\Windows\explorer.exe"),
    (r"C:\Windows\System32\taskmgr.exe", r'"C:\Windows\system32\taskmgr.exe" /4', r"C:\Windows\explorer.exe"),
    (r"C:\Windows\System32\svchost.exe", r"C:\Windows\system32\svchost.exe -k netsvcs -p", r"C:\Windows\System32\services.exe"),
]
APPROVED_DUMP = (r"C:\Tools\Sysinternals\procdump.exe", r"C:\Tools\Sysinternals\procdump.exe -accepteula -ma w3wp.exe D:\dumps\w3wp-hang.dmp", r"C:\Windows\System32\cmd.exe")


def dotenv(key: str) -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"{key} missing from .env")


def attack_events() -> dict[str, str]:
    if not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(ATTACK_DATA, CACHE)
    lines = [l for l in CACHE.read_text().splitlines() if "<EventID>1</EventID>" in l]
    find = lambda pattern: next(l for l in lines if re.search(pattern, l))  # noqa: E731
    return {
        "procdump": find(r"procdump\.exe\s+-accepteula -ma lsass"),
        "mimikatz": find(r"sekurlsa::minidump"),
        "comsvcs_ps": find(r"powershell\.exe\" &amp; \{C:\\Windows\\System32\\rundll32\.exe C:\\windows\\System32\\comsvcs\.dll"),
        "comsvcs": find(r"\"C:\\Windows\\System32\\rundll32\.exe\" C:\\windows\\System32\\comsvcs\.dll MiniDump"),
    }


def data(event: str, name: str, value: str) -> str:
    esc = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(rf"(<Data Name='{name}'>)[^<]*", lambda m: m.group(1) + esc, event)


def rewrite(event: str, when: datetime, host: str, user: str, key: str, image=None, cmd=None, parent=None) -> str:
    h = hashlib.sha256(key.encode()).hexdigest()
    event = re.sub(r"<Computer>[^<]*</Computer>", f"<Computer>{host}</Computer>", event)
    event = re.sub(r"SystemTime='[^']*'", f"SystemTime='{when:%Y-%m-%dT%H:%M:%S}.{when.microsecond:06d}00Z'", event)
    event = data(event, "UtcTime", f"{when:%Y-%m-%d %H:%M:%S}.{when.microsecond // 1000:03d}")
    event = data(event, "User", user)
    event = data(event, "ProcessGuid", "{%s-%s-%s-%s-%s}" % (h[:8], h[8:12], h[12:16], h[16:20], h[20:32]))
    event = data(event, "ProcessId", str(1000 + int(h[:4], 16) % 9000))
    if image:
        event = data(event, "Image", image)
        event = data(event, "OriginalFileName", Path(image.replace("\\", "/")).name.upper())
    if cmd:
        event = data(event, "CommandLine", cmd)
    if parent:
        event = data(event, "ParentImage", parent)
        event = data(event, "ParentCommandLine", f'"{parent}"')
    return event


def night(day: datetime, src: dict[str, str]) -> list[tuple[datetime, str, str]]:
    """(time, host, raw) for one UTC day."""
    out = []
    seed = int(hashlib.sha256(day.strftime("%Y-%m-%d").encode()).hexdigest(), 16)
    for i in range(40):
        host, user = FLEET[(seed >> i) % len(FLEET)]
        image, cmd, parent = EVERYDAY[(seed >> (i + 7)) % len(EVERYDAY)]
        when = day + timedelta(hours=7 + (seed >> (i * 3)) % 12, minutes=(seed >> (i * 2)) % 60, seconds=i)
        out.append((when, host, rewrite(src["procdump"], when, host, user, f"{day:%F}-{i}", image, cmd, parent)))
    when = day + timedelta(hours=14, minutes=20)
    host, user = FLEET[5]
    out.append((when, host, rewrite(src["procdump"], when, host, user, f"{day:%F}-iis", *APPROVED_DUMP)))
    host, user = LAB
    for n, kind in enumerate(["procdump", "mimikatz", "comsvcs_ps", "comsvcs"]):
        when = day + timedelta(hours=3, minutes=n * 2, seconds=n)
        out.append((when, host, rewrite(src[kind], when, host, user, f"{day:%F}-lab-{kind}")))
    return out


def nights() -> list[datetime]:
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return [today - timedelta(days=d) for d in range(DAYS, -1, -1)]


def search(spl: str) -> list[dict]:
    out = subprocess.run(["splunkctl", "--insecure", "--timeout", "240", "--yes", "search", "export", spl, "--output", "json"],
                         capture_output=True, text=True, timeout=300)
    try:
        return json.loads(out.stdout or "[]")
    except json.JSONDecodeError:
        raise SystemExit(f"search failed: {out.stdout[:200]} {out.stderr[:200]}")


def present_days() -> set[str]:
    """Days whose purple-team run is already indexed (that run is the last thing a night needs)."""
    rows = search(f"| tstats count where index={INDEX} host=PT-LAB-01 earliest=-{DAYS + 1}d@d by _time span=1d")
    return {datetime.fromisoformat(r["_time"].replace(" UTC", "+00:00").replace(" ", "T")).strftime("%F")
            for r in {r["_time"]: r for r in rows}.values() if int(r.get("count", 0)) > 0}


def send(events: list[tuple[datetime, str, str]]) -> None:
    url = dotenv("SPLUNK_HEC_URL").rstrip("/")
    url = url if url.endswith("/event") else url + "/services/collector/event"
    ctx = ssl._create_unverified_context()
    for i in range(0, len(events), 500):
        body = "".join(json.dumps({"time": t.timestamp(), "host": h.split(".")[0], "index": INDEX, "sourcetype": "XmlWinEventLog",
                                   "source": SOURCE, "event": raw}) for t, h, raw in events[i:i + 500]).encode()
        req = urllib.request.Request(url, body, {"Authorization": f"Splunk {dotenv('SPLUNK_HEC_TOKEN_DAC')}"})
        for attempt in range(5):
            try:
                urllib.request.urlopen(req, context=ctx, timeout=60).read()
                break
            except urllib.error.HTTPError as e:
                if e.code < 500 or attempt == 4:
                    raise SystemExit(f"HEC rejected the batch: HTTP {e.code} {e.read().decode()[:200]}")
                time.sleep(3)


def check() -> int:
    rows = search(f"| tstats count from datamodel=Endpoint.Processes where index={INDEX} earliest=-7d@d "
                  "Processes.process=\"*comsvcs*\" Processes.user=svc_purpleteam by _time span=1d")
    # Export streams preview rows before the final ones; the last row per key wins.
    lab_nights = sum(int(c) > 0 for c in {r["_time"]: r.get("count", 0) for r in rows}.values())
    total = search(f"| tstats count where index={INDEX} earliest=-7d@d")
    print(f"{INDEX}, last 7 days: {total[-1]['count'] if total else 0} events; purple-team comsvcs runs on {lab_nights} nights")
    if lab_nights < 6:
        print("story missing: run python3 scripts/seed_endpoint.py")
        return 1
    print("story present")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.check:
        return check()
    src = attack_events()
    todo = nights()
    if not args.dry_run:
        have = present_days()
        todo = [d for d in todo if d.strftime("%F") not in have]
    now = datetime.now(timezone.utc)
    events = [e for d in todo for e in night(d, src) if e[0] <= now]
    print(f"{len(todo)} nights to send, {len(events)} events ({sum('PT-LAB' in h for _, h, _ in events)} purple team)")
    if args.dry_run or not events:
        return 0
    send(events)
    print(f"sent {len(events)} events to {INDEX}; they are searchable within a few minutes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
