#!/usr/bin/env python3
"""Build and check a capture profile for a Splunk stack other than the shared CO2 stack.

    python3 scripts/stack_profile.py init mdl      # write .captures/ce01/stacks/mdl/ from .env
    python3 scripts/stack_profile.py check mdl     # say what is present and what is missing; prints no values

A scenario selects a profile with `recording.stackProfile: mdl`; the capture then runs with CAPTURE_STACK=mdl, which
points `ce01_capture.py setup` and `splunk_web_login.mjs` at the profile instead of ~/.splunkctl and the CO2 secrets.

Keys read from .env, with the profile name upper-cased as the suffix (here _MDL):

    SPLUNK_WEB_BASE_MDL       https://<stack>.splunkcloud.com        Splunk Web, for the login and the MCP URL
    SPLUNK_REST_URL_MDL       https://<stack>.splunkcloud.com:8089   splunkctl's host
    SPLUNK_REST_TOKEN_MDL     a REST bearer token for splunkctl
    SPLUNK_MCP_TOKEN_MDL      the Splunk MCP Server token
    SPLUNK_WEB_USER_MDL       optional: the Splunk Web login (defaults to SPLUNK_WEB_USER)
    SPLUNK_WEB_PASSWORD_MDL   optional: its password (defaults to SPLUNK_WEB_PASSWORD)
    STACK_ID_MDL              optional: the stack's bare name, which the sanitizer masks; defaults to the first
                              label of the web host

The profile lives under .captures/, which git ignores. Values are never printed.
"""

import stat
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ["SPLUNK_WEB_BASE", "SPLUNK_REST_URL", "SPLUNK_REST_TOKEN", "SPLUNK_MCP_TOKEN"]


def dotenv() -> dict[str, str]:
    env = {}
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def write_private(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def init(name: str) -> int:
    env = dotenv()
    suffix = f"_{name.upper()}"
    missing = [f"{key}{suffix}" for key in REQUIRED if not env.get(f"{key}{suffix}")]
    if missing:
        print("missing from .env:", ", ".join(missing))
        return 1
    profile = ROOT / ".captures/ce01/stacks" / name
    web = env[f"SPLUNK_WEB_BASE{suffix}"].rstrip("/")
    host = urlparse(web).netloc
    token = "".join(env[f"SPLUNK_MCP_TOKEN{suffix}"].split())
    write_private(profile / "secrets/web_base", web + "\n")
    write_private(profile / "splunkctl.yaml", f"host: {env[f'SPLUNK_REST_URL{suffix}']}\ntoken: {env[f'SPLUNK_REST_TOKEN{suffix}']}\n")
    write_private(profile / "splunk-mcp.env", f'SPLUNK_MCP_AUTH="Bearer {token}"\n')
    write_private(profile / "stack_id", env.get(f"STACK_ID{suffix}") or host.split(".")[0])
    (profile / "secrets").chmod(0o700)
    print(f"profile {name} written; next: node scripts/splunk_web_login.mjs with CAPTURE_STACK={name} (the capture does it)")
    return 0


def check(name: str) -> int:
    profile = ROOT / ".captures/ce01/stacks" / name
    # secrets/web-state.json is saved by the capture's own Splunk Web login, so it is not required beforehand.
    parts = ["secrets/web_base", "splunkctl.yaml", "splunk-mcp.env", "stack_id"]
    missing = [part for part in parts if not (profile / part).exists()]
    for part in parts:
        print(f"{'ok     ' if part not in missing else 'MISSING'} {part}")
    return 1 if missing else 0


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] in ("init", "check"):
        sys.exit({"init": init, "check": check}[sys.argv[1]](sys.argv[2]))
    sys.exit(__doc__)
