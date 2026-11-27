#!/usr/bin/env python3
"""Test every detection against its cases, compare with ESCU, check a week of endpoint data for noise, and have
Splunk AI Toolkit triage any noise.

    SPLUNK_MGMT_URL=... SPLUNK_TOKEN=<read-only> SPLUNK_HEC_URL=... SPLUNK_HEC_TOKEN=<dac_ci only> \
        python ci/test_detections.py

Run after `contentctl build`: the searches tested are the ones in the built app, with its own macros expanded. Each
test case's events go to the test index under their own host (ci-<run>-<n>), and the detection's search runs scoped
to that host. Writes
test_results/report.md (also to the GitHub job summary) and exits 1 when a case fails or noise is over budget.
"""

import os
import re
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from splunk import Splunk, send_hec  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((ROOT / "ci/config.yml").read_text())
SOURCE = "XmlWinEventLog:Microsoft-Windows-Sysmon/Operational"
TRIAGE_PROMPT = (
    "You triage alerts for the Splunk Enterprise Security detection '{name}'. In the last 7 days it fired {{hits}} "
    "times for account {{user}} on host {{dest}}: {{parent_process_name}} started {{process_name}} with command "
    "line {{process}}. First seen {{first}}, last seen {{last}}. Is this expected, approved activity or a likely "
    "attack? Answer on one line: VERDICT: expected or suspicious, then a dash and the reason in at most 25 words."
)


def built_searches() -> dict[str, str]:
    """Detection name -> search, from the built app's savedsearches.conf ('<label> - <name> - Rule'), with the
    app's own macros expanded: they only exist on Splunk after deploy, and the test must run the built logic."""
    macros = built_macros()
    out, name = {}, None
    for line in (ROOT / CFG["app_dir"] / "default/savedsearches.conf").read_text().splitlines():
        if m := re.match(r"^\[.+? - (.+) - Rule\]$", line):
            name = m.group(1)
        elif name and line.startswith("search = "):
            out[name] = expand(line[len("search = "):], macros)
    return out


def built_macros() -> dict[str, tuple[list[str], str]]:
    """'name' or 'name(n)' -> (argument names, definition), from the built app's macros.conf."""
    out, current = {}, None
    for line in (ROOT / CFG["app_dir"] / "default/macros.conf").read_text().splitlines():
        if line.startswith("[") and line.rstrip().endswith("]"):
            current = line.strip()[1:-1]
            out[current] = ([], "")
        elif current and "=" in line:
            key, value = (s.strip() for s in line.split("=", 1))
            if key == "definition":
                out[current] = (out[current][0], value)
            elif key == "args":
                out[current] = ([a.strip() for a in value.split(",")], out[current][1])
    return out


def expand(search: str, macros: dict[str, tuple[list[str], str]]) -> str:
    def one(m: re.Match) -> str:
        name, args = m.group(1), [a.strip() for a in m.group(2).split(",")] if m.group(2) else []
        key = f"{name}({len(args)})" if args else name
        if key not in macros:
            return m.group(0)
        names, definition = macros[key]
        for n, v in zip(names, args):
            definition = definition.replace(f"${n}$", v)
        return definition

    for _ in range(5):
        new = re.sub(r"`([A-Za-z0-9_]+)(?:\(([^`]*)\))?`", one, search)
        if new == search:
            break
        search = new
    return search


def scoped(search: str, scope: str) -> str:
    new, n = re.subn(r"(?i)(from\s+datamodel=\S+\s+where\s+)", lambda m: m.group(1) + scope + " ", search, count=1)
    if n != 1:
        raise ValueError("only tstats data model searches can be scoped")
    return new


def wait_indexed(splunk: Splunk, prefix: str, expected: int, timeout: int = 600) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        rows = splunk.search(f"| tstats count where index={CFG['test_index']} host={prefix}*", earliest="-1h")
        if rows and int(rows[0]["count"]) >= expected:
            return
        time.sleep(10)
    raise RuntimeError(f"test events not searchable after {timeout} s")


def md_table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return "\n".join(lines + ["| " + " | ".join(r) + " |" for r in rows])


def main() -> int:
    splunk = Splunk()
    run = os.environ.get("GITHUB_RUN_ID", str(int(time.time()))) + "-" + os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    prefix = f"ci-{run}-"
    searches = built_searches()
    manifests = [yaml.safe_load(p.read_text()) for p in sorted((ROOT / "tests").glob("*.yml"))]

    cases, events = [], []
    for m in manifests:
        if m["detection"] not in searches:
            raise SystemExit(f"tests/{m['detection']}: no such detection in the built app")
        for c in m["cases"]:
            host = f"{prefix}{len(cases)}"
            raw = [l for l in (ROOT / c["file"]).read_text().splitlines() if l.strip()]
            events += [{"time": time.time(), "host": host, "index": CFG["test_index"], "sourcetype": "XmlWinEventLog",
                        "source": SOURCE, "event": r} for r in raw]
            cases.append({**c, "detection": m["detection"], "compare_with": m.get("compare_with"), "host": host})
    send_hec(events)
    print(f"replayed {len(events)} events for {len(cases)} test cases into {CFG['test_index']}")
    wait_indexed(splunk, prefix, len(events))

    escu = {}
    for name in {c["compare_with"] for c in cases if c["compare_with"]}:
        status, body = splunk.call("GET", f"/servicesNS/-/-/saved/searches/{urllib.parse.quote(name, safe='')}")
        escu[name] = body["entry"][0]["content"]["search"] if status == 200 else None

    def fires(search: str, host: str) -> bool:
        return bool(splunk.search(scoped(search, f"index={CFG['test_index']} host={host}"), earliest="-1h"))

    def run_case(c: dict) -> dict:
        got = fires(searches[c["detection"]], c["host"])
        base = escu.get(c["compare_with"]) if c["compare_with"] else None
        return {**c, "fired": got, "escu": None if base is None else fires(base, c["host"]),
                "ok": got == (c["expect"] == "match")}

    with ThreadPoolExecutor(3) as pool:
        results = list(pool.map(run_case, cases))

    noise_cfg, triage = CFG["noise"], []

    def noise(name: str) -> tuple[str, int, list[dict]]:
        base = scoped(searches[name], f"index={noise_cfg['index']}")
        rows = splunk.search(base + " | stats sum(count) as hits", earliest=noise_cfg["earliest"])
        hits = int(float(rows[0].get("hits") or 0)) if rows else 0
        verdicts = []
        if hits:
            prompt = TRIAGE_PROMPT.format(name=name).replace('"', "'")
            verdicts = splunk.search(
                base + " | stats sum(count) as hits min(firstTime) as first max(lastTime) as last"
                " first(process) as process by user dest parent_process_name process_name | head 5"
                f' | ai prompt="{prompt}" connection={CFG["triage"]["connection"]}', earliest=noise_cfg["earliest"])
        return name, hits, verdicts

    with ThreadPoolExecutor(3) as pool:
        noise_rows = list(pool.map(noise, sorted({m["detection"] for m in manifests})))

    failed = [r for r in results if not r["ok"]] + [n for n in noise_rows if n[1] > noise_cfg["budget"]]
    mark = {True: "fires", False: "silent", None: "-"}
    report = ["## Detection tests", "", md_table(
        ["Detection", "Case", "Expected", "ESCU rule", "This detection", "Result"],
        [[r["detection"], r["name"], "fires" if r["expect"] == "match" else "silent", mark[r["escu"]],
          mark[r["fired"]], "pass" if r["ok"] else "**FAIL**"] for r in results])]
    report += ["", f"## Noise: last 7 days of `{noise_cfg['index']}` (budget {noise_cfg['budget']} alerts)", "",
               md_table(["Detection", "Alerts", "Result"],
                        [[n, str(h), "pass" if h <= noise_cfg["budget"] else "**OVER BUDGET**"] for n, h, _ in noise_rows])]
    for name, _, verdicts in noise_rows:
        for v in verdicts:
            triage.append([name, v.get("user", ""), v.get("dest", ""), v.get("process_name", ""), v.get("hits", ""),
                           " ".join(str(v.get("ai_result_1", "")).split())])
    if triage:
        report += ["", f"## AI triage of the noise (Splunk AI Toolkit, connection `{CFG['triage']['connection']}`)", "",
                   md_table(["Detection", "Account", "Host", "Process", "Alerts", "Verdict"], triage)]
    report += ["", f"**{'FAILED' if failed else 'PASSED'}**: {sum(r['ok'] for r in results)}/{len(results)} cases pass; "
               f"{sum(h > noise_cfg['budget'] for _, h, _ in noise_rows)} detection(s) over the noise budget."]
    text = "\n".join(report) + "\n"

    (ROOT / "test_results").mkdir(exist_ok=True)
    (ROOT / "test_results/report.md").write_text(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(text)
    print(text)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
