#!/usr/bin/env python3
"""Render a notebook with euporie into an asciinema cast, and a local page that plays it, for review before a take.

    .captures/venv/bin/python scripts/notebook_preview.py <notebook.ipynb> [--cols 110] [--euporie <euporie-preview>]
        [--out .captures/notebook-preview] [--open]

The cast is one frame: the whole notebook, rendered the way the hub's notebook pane shows it (euporie-preview, 24-bit
colour, dark scheme, images as text art). The page loads the asciinema player from apps/hub/node_modules, so run
`npm ci` in apps/hub once. `--euporie` defaults to the capture home's notebook environment.
"""

import argparse
import json
import shutil
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline.notebook_pane import render  # noqa: E402
PLAYER = ROOT / "apps/hub/node_modules/asciinema-player/dist/bundle"
DEFAULT_EUPORIE = Path("/Users/Shared/splunk-demo/nb/bin/euporie-preview")


def to_cast(text: str, cols: int, title: str) -> str:
    """A single-frame cast tall enough to hold every line."""
    lines = text.rstrip("\n").split("\n")
    header = {"version": 2, "width": cols, "height": len(lines) + 1, "title": title,
              "env": {"TERM": "xterm-256color"}}
    frame = "\x1b[H\x1b[2J" + "\r\n".join(lines)
    return json.dumps(header) + "\n" + json.dumps([0.0, "o", frame]) + "\n"


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>{title}</title>
<link rel="stylesheet" href="asciinema-player.css">
<style>body{{margin:0;background:#0b0f14;color:#ccc;font:14px system-ui}} header{{padding:8px 12px}}
#p{{max-width:{max_px}px;margin:0 auto}}</style></head>
<body><header>{title} · {rows} rows × {cols} cols · use the player's fullscreen button, or zoom the page</header>
<div id="p"></div>
<script src="asciinema-player.min.js"></script>
<script>AsciinemaPlayer.create("{cast}", document.getElementById("p"), {{fit: "width", theme: "asciinema",
  controls: true, autoPlay: true, poster: "npt:0:0.1"}});</script></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("notebook", type=Path)
    parser.add_argument("--cols", type=int, default=110)
    parser.add_argument("--euporie", type=Path, default=DEFAULT_EUPORIE)
    parser.add_argument("--out", type=Path, default=ROOT / ".captures/notebook-preview")
    parser.add_argument("--open", action="store_true", help="open the page in the default browser")
    args = parser.parse_args()
    if not (PLAYER / "asciinema-player.min.js").exists():
        sys.exit("run `npm ci` in apps/hub first: the page uses its asciinema player")

    text = render(args.notebook, args.cols, args.euporie)
    args.out.mkdir(parents=True, exist_ok=True)
    cast = args.out / f"{args.notebook.stem}.cast"
    cast.write_text(to_cast(text, args.cols, args.notebook.name))
    for name in ("asciinema-player.css", "asciinema-player.min.js"):
        shutil.copy(PLAYER / name, args.out / name)
    rows = text.count("\n") + 1
    page = args.out / f"{args.notebook.stem}.html"
    page.write_text(PAGE.format(title=args.notebook.name, cast=cast.name, rows=rows, cols=args.cols, max_px=args.cols * 10))
    print(f"{rows} lines; page {page}")
    if args.open:
        # The player fetches the cast, which file:// pages can't; serve the folder.
        print(f"serve it: python3 -m http.server -d {args.out} 8765, then open http://localhost:8765/{page.name}")
        webbrowser.open(f"http://localhost:8765/{page.name}")


if __name__ == "__main__":
    main()
