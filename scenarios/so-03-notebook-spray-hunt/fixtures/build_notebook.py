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
100 failures in 5 minutes never fires.

1. `params`: the suspect IP from the hot-index triage.
2. `raw-search`: its full history in the Machine Data Lake raw table. The hot index only keeps 14 days.
3. `load-shared`: the shared 90-day analytics table, loaded into this kernel with pandas.
4. `backtest`: the detection rule over 90 days, and the false positives it must skip.
5. `enrich`, `detection`: threat intel and privileged accounts, then the SPL to save as the alert."""

PARAMS = '''SUSPECT_IP = ""            # from the hot-index triage
WINDOW_DAYS = 90
MIN_USERS = 40             # distinct accounts failed per IP per day
MAX_TRIES_PER_USER = 3     # low and slow: a few attempts per account at most
MIN_FAIL_RATIO = 0.8       # a spray fails almost every attempt'''

SETUP = """import pandas as pd
import plotext as plt
import lake

print(lake.describe())"""

RAW_SEARCH = '''raw = lake.search_raw(SUSPECT_IP, days=120)
weekly = raw.set_index("_time").resample("W")["user"].size()
print(f"{len(raw):,} events from {SUSPECT_IP}, "
      f"{raw['user'].nunique()} accounts, "
      f"first seen {raw['_time'].min():%b %d}")
plt.clear_figure(); plt.theme("clear"); plt.plot_size(76, 9)
plt.bar([f"{d:%m-%d}" for d in weekly.index], list(weekly))
plt.title("events per week from the suspect IP")
plt.show()'''

LOAD_SHARED = '''tbl = lake.load_shared()
tbl["day"] = tbl["_time"].dt.floor("D")
tbl["is_fail"] = tbl["outcome"].eq("fail")
print(f"{len(tbl):,} sign-ins, {tbl['src_ip'].nunique()} source IPs, "
      f"{tbl['day'].min():%b %d} to {tbl['day'].max():%b %d}")
print(f"{tbl.memory_usage(deep=True).sum() / 1e6:.1f} MB in memory")'''

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
print(f"rule flags {len(flagged)} IP in {WINDOW_DAYS} days:")
print(flagged.assign(first=flagged["first"].dt.strftime("%b %d"),
                     last=flagged["last"].dt.strftime("%b %d")))
five = failed.groupby(["src_ip", failed["_time"].dt.floor("5min")])
print(f"old alert: busiest 5 min is {five.size().max()} "
      "failures, it needs 100")
busy = daily[(daily["users"] >= MIN_USERS) & ~rule]
print(f"skipped: {busy.reset_index()['src_ip'].nunique()} busy IP, "
      f"failure ratio at most {busy['ratio'].max():.0%}")
days = pd.date_range(tbl["day"].min(), tbl["day"].max(), freq="D")
series = daily.xs(SUSPECT_IP, level="src_ip")["users"]
series = series.reindex(days, fill_value=0)
plt.clear_figure(); plt.theme("clear"); plt.plot_size(76, 9)
plt.bar([f"{d:%m-%d}" for d in series.index], list(series))
plt.hline(MIN_USERS)
plt.title("accounts failed per day by the suspect IP")
plt.show()'''

ENRICH = '''intel = pd.read_csv("threat_intel.csv")
priv = pd.read_csv("privileged_users.csv")
ips = list(flagged.index)
print(intel[intel["indicator"].isin(ips)].to_string(index=False))
ok = tbl[tbl["src_ip"].isin(ips) & ~tbl["is_fail"]]
wins = ok[["_time", "src_ip", "user"]].merge(priv, on="user")
wins["_time"] = wins["_time"].dt.strftime("%b %d %H:%M")
print(f"privileged accounts the suspect got into: {len(wins)}")
print(wins.to_string(index=False))'''

DETECTION = '''spl = f"""index=demo_auth sourcetype="demo:auth:lake"
| eval failed=if(outcome="fail", 1, 0)
| stats count AS attempts, sum(failed) AS fails,
    dc(eval(if(failed=1, user, null()))) AS users BY src_ip
| eval ratio=fails/attempts, tries=fails/users
| where users>={MIN_USERS} AND ratio>={MIN_FAIL_RATIO}
    AND tries<={MAX_TRIES_PER_USER}"""
print("Daily saved search, ready for review:")
print(spl)'''


def code(cell_id, source, tags=None):
    metadata = {"tags": tags} if tags else {}
    return {"cell_type": "code", "id": cell_id, "metadata": metadata, "execution_count": None, "outputs": [], "source": source}


def build() -> dict:
    return {
        "cells": [
            {"cell_type": "markdown", "id": "intro", "metadata": {}, "source": INTRO},
            code("params", PARAMS, ["parameters"]),
            code("setup", SETUP),
            code("raw-search", RAW_SEARCH),
            code("load-shared", LOAD_SHARED),
            code("backtest", BACKTEST),
            code("enrich", ENRICH),
            code("detection", DETECTION),
        ],
        "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


if __name__ == "__main__":
    out = Path(sys.argv[1]) / "hunt.ipynb"
    out.write_text(json.dumps(build(), indent=1) + "\n")
    print(f"wrote {out.name}")
