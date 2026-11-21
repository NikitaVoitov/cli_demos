#!/usr/bin/env python3
"""Build the static n8n canvas the hub serves at /n8n-preview/ from the pinned image in recorder/n8n-preview.yaml.

  .captures/venv/bin/python scripts/n8n_preview_snapshot.py

Starts the image in preview mode, copies its prebuilt editor (base path already applied), and freezes the few
responses the read-only demo page reads: the public settings, the node types the demo workflows use, and their
icons. Nothing of n8n runs when the hub is viewed. The output, apps/hub/public/n8n-preview/, is git-ignored.
"""

import json
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from glob import glob
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "recorder/n8n-preview.yaml"
ASSETS = ROOT / "recorder/n8n-preview"
OUT = ROOT / "apps/hub/public/n8n-preview"
CACHE = "/home/node/.cache/n8n/public"
ENV = {
    "N8N_PREVIEW_MODE": "true",
    "N8N_DIAGNOSTICS_ENABLED": "false",
    "N8N_VERSION_NOTIFICATIONS_ENABLED": "false",
    "N8N_TEMPLATES_ENABLED": "false",
    "N8N_PERSONALIZATION_ENABLED": "false",
    "N8N_HIRING_BANNER_ENABLED": "false",
    # Without this the community-node list waits about 40 s on a registry the container can't always reach.
    "N8N_COMMUNITY_PACKAGES_ENABLED": "false",
}


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def get(port: int, path: str) -> bytes:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/{path.lstrip('/')}", timeout=60) as r:
        return r.read()


def wait_ready(container: str, port: int, timeout: float = 180) -> None:
    """The API answers a few seconds before n8n has written the editor files it serves."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            get(port, "rest/settings")
            if subprocess.run(["docker", "exec", container, "test", "-f", f"{CACHE}/index.html"]).returncode == 0:
                return
        except OSError:
            pass
        time.sleep(1)
    raise SystemExit(f"n8n was not ready on port {port} within {timeout:.0f} s")


def node_catalog(port: int, timeout: float = 90) -> list[dict]:
    """n8n writes the 18 MB catalog after it starts answering, so a read can catch it half written."""
    deadline = time.time() + timeout
    while True:
        try:
            return json.loads(get(port, "types/nodes.json"))
        except (OSError, ValueError):
            if time.time() > deadline:
                raise
            time.sleep(2)


def workflow_node_types(patterns: list[str]) -> set[str]:
    types: set[str] = set()
    for pattern in patterns:
        for path in glob(str(ROOT / pattern)):
            types |= {node["type"] for node in json.loads(Path(path).read_text())["nodes"]}
    if not types:
        raise SystemExit(f"no workflow artifacts match {patterns}; write one with python -m pipeline.workflow first")
    return types


def icon_paths(node_type: dict) -> list[str]:
    url = node_type.get("iconUrl")
    return [url] if isinstance(url, str) else list((url or {}).values())


def scrub_settings(raw: bytes, port: int) -> bytes:
    """Public settings say preview mode is on; drop the container's own URLs and turn community nodes off."""
    text = re.sub(rf"https?://(?:localhost|127\.0\.0\.1):(?:5678|{port})[^\"]*", "", raw.decode())
    settings = json.loads(text)
    settings["data"]["communityNodesEnabled"] = False
    return json.dumps(settings, separators=(",", ":")).encode()


def main() -> None:
    config = yaml.safe_load(CONFIG.read_text())
    keep = workflow_node_types(config["workflows"])
    image = f"{config['image']}@{config['digest']}"
    port = free_port()
    env = [arg for key, value in {**ENV, "N8N_PATH": config["basePath"]}.items() for arg in ("-e", f"{key}={value}")]
    container = subprocess.run(["docker", "run", "-d", "--rm", "-p", f"127.0.0.1:{port}:5678", *env, image],
                               check=True, capture_output=True, text=True).stdout.strip()
    try:
        wait_ready(container, port)
        version = subprocess.run(["docker", "exec", container, "n8n", "--version"],
                                 check=True, capture_output=True, text=True).stdout.strip()
        shutil.rmtree(OUT, ignore_errors=True)
        OUT.mkdir(parents=True)
        subprocess.run(["docker", "cp", f"{container}:{CACHE}/.", str(OUT)], check=True, capture_output=True)
        # n8n serves fonts from the editor's own dist, not the cache; without them a static host answers the CSS's
        # font requests with its HTML fallback.
        fonts = subprocess.run(["docker", "exec", container, "sh", "-c",
                                "find /usr/local/lib/node_modules/n8n -path '*n8n-editor-ui/dist/assets/*' "
                                "\\( -name '*.woff2' -o -name '*.woff' -o -name '*.ttf' \\)"],
                               check=True, capture_output=True, text=True).stdout.split()
        for font in fonts:
            if not (OUT / "assets" / Path(font).name).exists():
                subprocess.run(["docker", "cp", f"{container}:{font}", str(OUT / "assets")], check=True, capture_output=True)

        # The page is served without n8n's per-request CSP header, so its nonce placeholders go.
        page = re.sub(r'\s+nonce="\{\{CSP_NONCE\}\}"', "", (OUT / "index.html").read_text())
        (OUT / "workflows").mkdir()
        (OUT / "workflows/demo.html").write_text(page)
        (OUT / "index.html").unlink()

        # Node types: only the ones the demo workflows use (the full file is about 18 MB), with brand icons.
        all_types = node_catalog(port)
        kept = [t for t in all_types if t["name"] in keep]
        missing = keep - {t["name"] for t in kept}
        if missing:
            raise SystemExit(f"n8n {version} has no node type {sorted(missing)}")
        for t in kept:
            override = config.get("icons", {}).get(t["name"])
            if override:
                name = Path(override).name
                (OUT / "icons/brand").mkdir(parents=True, exist_ok=True)
                shutil.copy(ASSETS / override, OUT / "icons/brand" / name)
                t["iconUrl"] = f"icons/brand/{name}"
                continue
            for path in icon_paths(t):
                dest = OUT / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(get(port, path))
        (OUT / "types/nodes.json").write_text(json.dumps(kept, separators=(",", ":")))
        for unused in ("credentials.json", "node-versions.json"):
            (OUT / "types" / unused).unlink(missing_ok=True)

        (OUT / "rest").mkdir()
        (OUT / "rest/settings").write_bytes(scrub_settings(get(port, "rest/settings"), port))
        (OUT / "rest/community-node-types").write_text('{"data":[]}')
        (OUT / "manifest.json").write_text(json.dumps({
            "n8n": version, "image": image, "basePath": config["basePath"],
            "nodeTypes": sorted(keep), "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }, indent=2) + "\n")
    finally:
        subprocess.run(["docker", "stop", container], capture_output=True)

    files = [p for p in OUT.rglob("*") if p.is_file()]
    size = sum(p.stat().st_size for p in files)
    print(f"wrote {OUT.relative_to(ROOT)}: n8n {version}, {len(files)} files, {size / 1e6:.1f} MB, "
          f"{len(kept)} node type versions for {len(keep)} types")


if __name__ == "__main__":
    sys.exit(main())
