#!/usr/bin/env python3
"""Write hunt.ipynb, the guided hunt the agent runs cell by cell.

    python3 build_notebook.py <directory>

The notebook is the same file every take starts from: no outputs, one empty parameter (SUSPECT_IP) for the agent
to fill in from its triage of the hot index, and stable cell IDs. The jpterm wrapper holds `raw-search`,
`load-shared` and `backtest` until the viewer approves them (recording.notebook.gated in scenario.yaml).
Standard library only.
"""

import json
import sys
from pathlib import Path

INTRO = """# Hunt: low-and-slow password spray (T1110.003)

**Hypothesis.** One source IP tries a single password against many accounts, slowly enough that the alert on
100 failures in 5 minutes never fires. The hot index keeps 14 days; the Machine Data Lake keeps the rest."""

PARAMS = '''SUSPECT_IP = ""            # from the hot-index triage
WINDOW_DAYS = 90
MIN_USERS = 40             # distinct accounts failed per IP per day
MAX_TRIES_PER_USER = 3     # low and slow: a few attempts per account at most
MIN_FAIL_RATIO = 0.8       # a spray fails almost every attempt'''

SETUP = """import pandas as pd
import lake
import show

show.note(lake.describe())"""

RAW_SEARCH = '''raw = lake.search_raw(SUSPECT_IP, days=120)
weekly = raw.set_index("_time").resample("W")["user"].size()
hot_from = pd.Timestamp.now(tz="UTC").floor("D") - pd.Timedelta(days=14)
show.weekly(weekly, hot_from, f"events per week from {SUSPECT_IP}")
show.result(f"*{len(raw):,}* events from *{SUSPECT_IP}* against "
            f"*{raw['user'].nunique()}* accounts, first seen *{raw['_time'].min():%b %d}*")
show.note(f"the 14-day index holds {(raw['_time'] >= hot_from).sum():,} of them")'''

LOAD_SHARED = '''tbl = lake.load_shared()
tbl["day"] = tbl["_time"].dt.floor("D")
tbl["is_fail"] = tbl["outcome"].eq("fail")
reach = tbl[tbl["is_fail"]].groupby("src_ip")["user"].nunique()
show.ranked(reach.nlargest(6), SUSPECT_IP, "accounts with a failed sign-in, top source IPs")
show.result(f"*{len(tbl):,}* sign-ins from *{tbl['src_ip'].nunique()}* source IPs, "
            f"*{tbl['day'].min():%b %d}* to *{tbl['day'].max():%b %d}*")
show.note(f"{tbl.memory_usage(deep=True).sum() / 1e6:.1f} MB in memory")'''

BACKTEST = '''g = ["src_ip", "day"]
daily = tbl.groupby(g).agg(attempts=("user", "size"),
                           fails=("is_fail", "sum"))
failed = tbl[tbl["is_fail"]]
daily["users"] = failed.groupby(g)["user"].nunique()
daily["users"] = daily["users"].fillna(0)
daily["ratio"] = daily["fails"] / daily["attempts"]
daily["tries"] = daily["fails"] / daily["users"].clip(lower=1)
rule = ((daily["users"] >= MIN_USERS)
        & (daily["ratio"] >= MIN_FAIL_RATIO)
        & (daily["tries"] <= MAX_TRIES_PER_USER))
hits = daily[rule].reset_index()
flagged = hits.groupby("src_ip").agg(days=("day", "size"),
                                     first=("day", "min"),
                                     last=("day", "max"))
busy = daily[(daily["users"] >= MIN_USERS) & ~rule].reset_index()
show.rule_map(daily.reset_index(), MIN_USERS, MIN_FAIL_RATIO,
              flagged=flagged.index, skipped=busy["src_ip"].unique(),
              title=f"every source IP, every day for {WINDOW_DAYS} days")
show.result(f"the rule flags *{len(flagged)}* IP in {WINDOW_DAYS} days:")
show.table(flagged.reset_index().assign(first=flagged["first"].dt.strftime("%b %d").values,
                                        last=flagged["last"].dt.strftime("%b %d").values),
           mark=flagged.index)
five = failed.groupby(["src_ip", failed["_time"].dt.floor("5min")]).size()
show.note(f"old alert: the most failures any IP made in 5 minutes is {five.max()}; it fires at 100")
show.note(f"skipped {busy['src_ip'].nunique()} busy IP: failure ratio at most {busy['ratio'].max():.0%}")
days = pd.date_range(tbl["day"].min(), tbl["day"].max(), freq="D")
series = daily.xs(SUSPECT_IP, level="src_ip")["users"].reindex(days, fill_value=0)
show.daily(series, MIN_USERS, f"accounts failed per day by {SUSPECT_IP}")'''

ENRICH = '''intel = pd.read_csv("threat_intel.csv")
priv = pd.read_csv("privileged_users.csv")
ips = list(flagged.index)
show.table(intel[intel["indicator"].isin(ips)], mark=ips)
ok = tbl[tbl["src_ip"].isin(ips) & ~tbl["is_fail"]]
wins = ok[["_time", "src_ip", "user"]].merge(priv, on="user")
show.result(f"privileged accounts the suspect got into: *{len(wins)}*")
for time, ip, user, role in wins.itertuples(index=False):
    show.alert(f"*{user}* ({role}) signed in from {ip} on *{time:%b %d %H:%M}*")'''

DETECTION = '''spl = f"""index=demo_auth sourcetype="demo:auth:lake"
| eval failed=if(outcome="fail", 1, 0)
| stats count AS attempts, sum(failed) AS fails,
    dc(eval(if(failed=1, user, null()))) AS users BY src_ip
| eval ratio=fails/attempts, tries=fails/users
| where users>={MIN_USERS} AND ratio>={MIN_FAIL_RATIO}
    AND tries<={MAX_TRIES_PER_USER}"""
show.result("Daily saved search, ready for review:")
print(spl)'''

STEPS = {
    "params": "## 1. Parameters",
    "raw-search": "## 2. Full history in the raw table\n\nSPL2 over the Machine Data Lake raw table, which keeps what the hot index has aged out.",
    "load-shared": "## 3. The shared 90-day table\n\nThe promoted analytics table, read over Open Sharing straight into pandas.",
    "backtest": "## 4. Backtest the detection",
    "enrich": "## 5. Threat intel and privileged accounts",
    "detection": "## 6. The detection to save",
}


def code(cell_id, source, tags=None):
    metadata = {"tags": tags} if tags else {}
    return {"cell_type": "code", "id": cell_id, "metadata": metadata, "execution_count": None, "outputs": [], "source": source}


def step(cell_id, source, tags=None):
    heading = {"cell_type": "markdown", "id": f"{cell_id}-md", "metadata": {}, "source": STEPS[cell_id]}
    return [heading, code(cell_id, source, tags)]


def build() -> dict:
    return {
        "cells": [
            {"cell_type": "markdown", "id": "intro", "metadata": {}, "source": INTRO},
            *step("params", PARAMS, ["parameters"]),
            code("setup", SETUP),
            *step("raw-search", RAW_SEARCH),
            *step("load-shared", LOAD_SHARED),
            *step("backtest", BACKTEST),
            *step("enrich", ENRICH),
            *step("detection", DETECTION),
        ],
        "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


if __name__ == "__main__":
    out = Path(sys.argv[1]) / "hunt.ipynb"
    out.write_text(json.dumps(build(), indent=1) + "\n")
    print(f"wrote {out.name}")
