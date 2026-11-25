"""Terminal output for hunt.ipynb: coloured text and text charts, nothing else.

Everything is printed with ANSI colours, so jpterm (what the agent reads), euporie and the recording show the same
output, and the hub's transcript shows it as plain text. Emphasis inside a message is marked *like this*.

    show.result("*679* events from *198.51.100.22*")      a conclusion, in teal
    show.alert("*svc_backup* signed in from the suspect")  a compromise, in red
    show.note("skipped 203.0.113.7: at most 9% failures")  context, in grey
    show.table(frame, mark=["198.51.100.22"])              aligned columns; rows whose first column is marked in red
    show.weekly / show.ranked / show.rule_map / show.daily  plotext charts
"""

import re

import plotext as plt

WIDTH = 88
TEAL, RED, AMBER, GREY = 37, 203, 214, 245
_RESET = "\x1b[0m"


def _fg(code: int) -> str:
    return f"\x1b[38;5;{code}m"


def _emphasis(text: str, color: int) -> str:
    return re.sub(r"\*(.+?)\*", lambda m: f"\x1b[1m{m.group(1)}\x1b[22m", f"{_fg(color)}{text}") + _RESET


def result(text: str) -> None:
    print(_emphasis(text, TEAL))


def alert(text: str) -> None:
    print(_emphasis(text, RED))


def note(text: str) -> None:
    print(_emphasis(text, GREY))


def table(frame, mark=()) -> None:
    mark = {str(m) for m in mark}
    lines = frame.to_string(index=False).split("\n")
    print(f"\x1b[1m{lines[0]}{_RESET}")
    for key, line in zip(frame.iloc[:, 0].astype(str), lines[1:]):
        print(f"{_fg(RED)}{line}{_RESET}" if key in mark else line)


def _figure(height: int, title: str) -> None:
    plt.clear_figure()
    plt.theme("clear")
    plt.plot_size(WIDTH, height)
    plt.title(title)


def _bars(values, colors, width: float) -> None:
    """Vertical bars at x = 1..n, one plotext call per colour (a colour list per bar gets misapplied)."""
    for color in dict.fromkeys(colors):
        xs = [i + 1 for i, c in enumerate(colors) if c == color]
        plt.bar(xs, [values[i - 1] for i in xs], color=color, width=width)


def _axes(values, labels=None, every: int = 1) -> None:
    """Whole-number y ticks, and every `every`-th x label so dates don't run together."""
    top = max(values) if len(values) else 0
    step = next(n for n in (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 10**9) if n * 4 >= top)
    plt.yticks(list(range(0, int(top) + 1, step)))
    if labels is not None:
        positions = list(range(1, len(labels) + 1))
        plt.xticks(positions[::every], labels[::every])


def _legend(*items) -> None:
    print("   ".join(f"{_fg(color)}■{_RESET} {name}" for color, name in items))


def weekly(series, hot_from, title: str) -> None:
    """Weekly counts: weeks the 14-day index no longer holds in amber, the rest in teal."""
    _figure(12, title)
    labels = [f"{d:%b %d}" for d in series.index]
    _bars(list(series), [AMBER if d < hot_from else TEAL for d in series.index], width=0.6)
    _axes(list(series), labels, every=2)
    plt.show()
    _legend((AMBER, "only in the lake"), (TEAL, "also in the 14-day index"))


def ranked(series, highlight: str, title: str) -> None:
    """Horizontal bars, largest first, with `highlight` in red and the value at the end."""
    print(f"\x1b[1m{title}{_RESET}")
    label_width = max(len(str(i)) for i in series.index)
    top = max(series) or 1
    for label, value in series.items():
        color = RED if str(label) == highlight else GREY
        bar = "█" * max(1, round(value / top * (WIDTH - label_width - 10)))
        print(f"{str(label):>{label_width}} {_fg(color)}{bar}{_RESET} {value:,}")


def rule_map(daily, users: int, ratio: float, flagged, skipped, title: str) -> None:
    """Each IP-day: accounts failed against failure ratio. The rule fires right of and above the lines."""
    _figure(15, title)
    flagged, skipped = list(flagged), list(skipped)
    rest = daily[~daily["src_ip"].isin(flagged + skipped)]
    plt.scatter(list(rest["users"]), list(rest["ratio"]), color=GREY, marker="·")
    for ips, color in ((skipped, AMBER), (flagged, RED)):
        part = daily[daily["src_ip"].isin(ips)]
        plt.scatter(list(part["users"]), list(part["ratio"]), color=color, marker="●")
    plt.vline(users, TEAL)
    plt.hline(ratio, TEAL)
    plt.yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0], ["0%", "20%", "40%", "60%", "80%", "100%"])
    top = int(daily["users"].max()) + 10
    plt.xticks(list(range(0, top, 10)))
    plt.show()
    note("x: accounts one IP failed in one day   y: share of that IP's sign-ins that failed")
    _legend((RED, f"flagged: {', '.join(flagged)}"), (AMBER, f"busy but skipped: {', '.join(skipped)}"),
            (GREY, "every other IP-day"))
    _legend((TEAL, f"rule: {users}+ accounts and {ratio:.0%}+ failed"))


def daily(series, threshold: float, title: str) -> None:
    _figure(11, title)
    labels = [f"{d:%b %d}" for d in series.index]
    _bars(list(series), [RED if v >= threshold else GREY for v in series], width=0.8)
    plt.hline(threshold, TEAL)
    _axes(list(series), labels, every=14)
    plt.show()
    _legend((RED, f"days over the rule's {threshold:g} accounts"), (TEAL, "rule threshold"))
