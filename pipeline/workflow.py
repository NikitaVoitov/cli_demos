"""Sanitize an exported n8n workflow into a scenario's workflow artifact, and check the scenario's steps against it.

  .captures/venv/bin/python -m pipeline.workflow scenarios/<id> <export.json>
  .captures/venv/bin/python -m pipeline.workflow scenarios/<id> --check

The hub draws the artifact on the real n8n canvas (§0.12) and shows it as importable JSON in the transcript, so it
keeps each node's full configuration: names, types, positions, connections, and parameters. Credentials, webhook
IDs, pinned data, and instance metadata are dropped; URLs keep only their path, and resource IDs picked in n8n
(a Slack channel, a sheet) are masked while their display names stay.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from . import sanitize

ROOT = Path(__file__).resolve().parent.parent
STICKY = "n8n-nodes-base.stickyNote"
PLACEHOLDER_HOST = "service.example.com"
URL = re.compile(r"https?://[^\s\"'<>]+")


def _url(match: re.Match) -> str:
    parts = urlsplit(match.group(0))
    if (parts.hostname or "").endswith(("example.com", "example.net", "example.org", ".example")):
        return match.group(0)
    return f"{parts.scheme}://{PLACEHOLDER_HOST}{parts.path}"


def _clean(value):
    """URLs keep their path on a placeholder host; resource-locator IDs are masked, their display names kept."""
    if isinstance(value, str):
        return URL.sub(_url, value)
    if isinstance(value, list):
        return [_clean(v) for v in value]
    if isinstance(value, dict):
        out = {k: _clean(v) for k, v in value.items()}
        if out.get("__rl") and out.get("mode") in ("id", "list") and isinstance(out.get("value"), str):
            out["value"] = re.sub(r"[A-Za-z0-9]", "0", out["value"])
        return out
    return value


def _parameters(node: dict) -> dict:
    return _clean(node.get("parameters") or {})


def sanitize_workflow(export: dict) -> dict:
    data = export.get("workflow") or export.get("data") or export
    nodes = []
    for node in data["nodes"]:
        # An empty sticky note draws a blank box on the published canvas.
        if node["type"] == STICKY and not str(node.get("parameters", {}).get("content", "")).strip():
            continue
        clean = {k: node[k] for k in ("id", "name", "type", "typeVersion", "position") if k in node}
        clean["parameters"] = _parameters(node)
        if node.get("disabled"):
            clean["disabled"] = True
        nodes.append(clean)
    workflow = {
        "name": data.get("name", "Workflow"),
        "nodes": nodes,
        "connections": data.get("connections", {}),
        "settings": {k: v for k, v in (data.get("settings") or {}).items() if k == "executionOrder"},
        "pinData": {},
    }
    text = json.dumps(workflow, ensure_ascii=False)
    return json.loads(sanitize.apply(text, sanitize.find_replacements(text)))


def problems(workflow: dict, scenario: dict, content: dict) -> list[str]:
    """Everything the hub would refuse to load, plus identifiers the sanitizer still finds."""
    found = []
    nodes = workflow["nodes"]
    ids, names = [n.get("id") for n in nodes], [n["name"] for n in nodes]
    if None in ids or len(set(ids)) != len(ids):
        found.append("every node needs a unique id")
    if len(set(names)) != len(names):
        found.append("node names must be unique")
    for source, outputs in workflow["connections"].items():
        targets = [c["node"] for kind in outputs.values() for out in kind for c in (out or [])]
        for name in [source, *targets]:
            if name not in names:
                found.append(f"connection refers to unknown node {name!r}")
    block = scenario.get("workflow") or {}
    callouts = ((content.get("workflow") or {}).get("callouts")) or {}
    for i, step in enumerate(block.get("steps", [])):
        if step.get("node") not in names:
            found.append(f"workflow step {i + 1} names unknown node {step.get('node')!r}")
        if step.get("callout") and step["callout"] not in callouts:
            found.append(f"workflow step {i + 1} callout {step['callout']!r} has no text in content.yaml")
    text = json.dumps(workflow)
    if sanitize.leftovers(text):
        found.append(f"identifiers left after sanitizing: {sanitize.leftovers(text)}")
    if re.search(r'"(?:credentials|webhookId|pinData)":\s*\{(?!\})', text):
        found.append("credentials, webhook IDs, or pinned data survived")
    return found


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("scenario", type=Path)
    p.add_argument("export", type=Path, nargs="?", help="workflow JSON exported from n8n")
    p.add_argument("--check", action="store_true", help="only validate the existing artifact and steps")
    args = p.parse_args()

    scenario = yaml.safe_load((args.scenario / "scenario.yaml").read_text())
    content_file = args.scenario / "content.yaml"
    content = yaml.safe_load(content_file.read_text()) if content_file.exists() else {}
    src = (scenario.get("workflow") or {}).get("src", "artifacts/workflow.json")
    dest = args.scenario / src

    if args.check or args.export is None:
        workflow = json.loads(dest.read_text())
    else:
        workflow = sanitize_workflow(json.loads(args.export.read_text()))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {dest}")

    for node in workflow["nodes"]:
        if node["type"] != STICKY:
            print(f"  {node['name']:<36} {node['type']}")
    found = problems(workflow, scenario, content)
    for line in found:
        print(f"  ✗ {line}")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
