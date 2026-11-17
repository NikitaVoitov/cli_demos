#!/usr/bin/env python3
"""CE-01 capture environment for Cursor CLI.

  python3 scripts/ce01_capture.py setup            # build the neutral capture HOME (idempotent)
  python3 scripts/ce01_capture.py jira             # after setup: add Jira (acli + Atlassian MCP) for SO-07
  python3 scripts/ce01_capture.py login            # one-time Cursor CLI login inside the capture HOME
  python3 scripts/ce01_capture.py atlassian-login  # one-time Atlassian MCP OAuth, as the demo-site account
  python3 scripts/ce01_capture.py acli-login       # one-time acli login to the demo site with the .env token
  python3 scripts/ce01_capture.py shell            # open the pinned demo shell (dry runs, manual checks)

The capture HOME lives at /Users/Shared/splunk-demo so paths render as ~/payments and no
username appears. Secrets are copied in with 0600 permissions and never printed.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
REAL_HOME = Path.home()
CAPTURE_HOME = Path("/Users/Shared/splunk-demo")
CLIENT = ROOT / "recorder/clients/cursor-cli"
SECRETS = ROOT / ".captures/ce01/secrets"
TOOL_PATH = f"{REAL_HOME}/.local/bin:/opt/homebrew/bin:/usr/local/bin"
# Every published demo runs on the CLI default. A take recorded with `--model` is remembered by the CLI,
# so setup writes this back before each take.
AUTO_BALANCE = {
    "model": {"modelId": "auto-smart", "displayModelId": "auto-smart", "displayName": "Auto Balance",
              "displayNameShort": "Auto Balance", "aliases": [], "maxMode": False},
    "selectedModel": {"modelId": "auto-smart", "parameters": [{"id": "optimize_for", "value": "balanced"}]},
    "maxMode": False,
    "hasChangedDefaultModel": False,
    "modelSelectionHistory": ["auto-smart"],
}

PUBLIC_SKILLS = ["search-and-dashboard-troubleshooter"]
TOOL_SKILLS = {"playwright-cli": REAL_HOME / ".agents/skills/playwright-cli"}

PERMISSIONS = [
    "Shell(splunkctl)",
    "Shell(playwright-cli)",
    "Shell(ls)",
    "Shell(cat)",
    "Shell(jq)",
    "Shell(echo)",
    "Shell(head)",
    "Shell(tail)",
    "Shell(grep)",
    "Shell(wc)",
    "Shell(sleep)",
    "Read(**)",
    "Write(**)",
    "Mcp(splunk:*)",
]

ATLASSIAN_MCP = "https://mcp.atlassian.com/v1/mcp"
JIRA_READS = ["atlassianUserInfo", "getAccessibleAtlassianResources", "searchJiraIssuesUsingJql", "getJiraIssue",
              "listJiraIssueComments", "discover", "executeRead"]
# Jira writes go through the gated acli wrapper, so the MCP's own write tools are denied.
JIRA_WRITES = ["createJiraIssue", "editJiraIssue", "addOrEditJiraIssueComment", "transitionJiraIssue",
               "executeWrite", "executeDestructive"]
JIRA_SHIMS = ("acli", "atlassian-mcp")


def private_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    dst.chmod(stat.S_IRUSR | stat.S_IWUSR)


def web_host() -> str:
    return urlparse((SECRETS / "web_base").read_text().strip()).netloc


def render(template: Path, dst: Path) -> None:
    text = template.read_text().replace("__SPLUNK_WEB_HOST__", web_host()).replace("__HOME__", str(CAPTURE_HOME))
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text)


def setup(model: str = "") -> None:
    h = CAPTURE_HOME
    for d in ("bin", "payments", ".config", ".cache/playwright-cli", ".playwright", ".cursor/skills"):
        (h / d).mkdir(parents=True, exist_ok=True)
    h.chmod(0o700)

    # Cursor CLI keeps its SSO session in the login keychain, which macOS resolves through $HOME.
    keychains = h / "Library/Keychains"
    keychains.parent.mkdir(exist_ok=True)
    if not keychains.is_symlink():
        keychains.symlink_to(REAL_HOME / "Library/Keychains")

    shim = h / "bin/splunkctl"
    # The staging stack's CA is not in the system trust store.
    shim.write_text('#!/bin/sh\nexec /usr/local/bin/splunkctl --insecure "$@"\n')
    shim.chmod(0o755)

    private_copy(REAL_HOME / ".splunkctl/config.yaml", h / ".splunkctl/config.yaml")
    private_copy(REAL_HOME / ".cursor/mcp-secrets/splunk-mcp.env", h / ".config/splunk-mcp.env")
    private_copy(SECRETS / "web-state.json", h / ".config/splunk-web-state.json")

    # Jira is opt-in per demo (`ce01_capture.py jira`); a plain setup leaves no trace of it.
    for name in JIRA_SHIMS:
        (h / "bin" / name).unlink(missing_ok=True)
    render(CLIENT / "mcp.json.tmpl", h / ".cursor/mcp.json")
    render(CLIENT / "splunk-mcp.tmpl", h / "bin/splunk-mcp")
    (h / "bin/splunk-mcp").chmod(0o700)
    render(CLIENT / "workspace/AGENTS.md", h / "payments/AGENTS.md")

    (h / ".playwright/cli.config.json").write_text(json.dumps({
        "browser": {
            "browserName": "chromium",
            "isolated": True,
            "launchOptions": {"headless": True},
            "contextOptions": {
                "storageState": str(h / ".config/splunk-web-state.json"),
                "viewport": {"width": 1440, "height": 900},
                "ignoreHTTPSErrors": True,
            },
        },
        "outputDir": str(h / ".cache/playwright-cli"),
    }, indent=2))

    skills = h / ".cursor/skills"
    for d in skills.iterdir():
        shutil.rmtree(d)
    env = demo_env()
    for name in PUBLIC_SKILLS:
        subprocess.run(["npx", "-y", "skills@1.9.0", "add", "splunk/splunk-agent-skills", "--skill", name,
                        "--agent", "cursor", "--global", "--yes", "--copy"],
                       env=env, cwd=h, check=True, stdout=subprocess.DEVNULL)
    # splunkctl ships its own skill; it only knows Claude and Codex paths, so copy it across.
    subprocess.run(["/usr/local/bin/splunkctl", "--yes", "skill", "install", "--agent", "codex", "--global"],
                   env=env, cwd=h, check=True, stdout=subprocess.DEVNULL)
    shutil.copytree(h / ".agents/skills/splunkctl", skills / "splunkctl")
    shutil.rmtree(h / ".agents/skills/splunkctl")
    for name, src in TOOL_SKILLS.items():
        shutil.copytree(src, skills / name)

    # Cursor CLI hangs on a hand-written config, so only patch the one it generated on first run.
    cfg_path = h / ".cursor/cli-config.json"
    if not cfg_path.exists():
        print(f"capture home ready: {h}\nrun Cursor CLI once in the capture home, then rerun setup to pin settings")
        return
    cfg = json.loads(cfg_path.read_text())
    cfg.update({
        "permissions": {"allow": PERMISSIONS, "deny": []},
        # Run Everything: the only approval in the story is splunkctl's CONFIRMATION_REQUIRED.
        "approvalMode": "unrestricted",
        "hints": False,
        "suggestNextPrompt": False,
        "notifications": False,
        "attribution": {"attributeCommitsToAgent": False, "attributePRsToAgent": False},
    })
    if not model:
        cfg.update(AUTO_BALANCE)
    cfg_path.write_text(json.dumps(cfg, indent=2))
    cfg_path.chmod(0o600)
    print(f"capture home ready: {h} (model {cfg['model']['modelId']})")


def dotenv(key: str) -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"{key} missing from .env")


def jira_site() -> str:
    site = dotenv("JIRA_SITE").removeprefix("https://").rstrip("/")
    if site == "splunk.atlassian.net" or not site.endswith(".atlassian.net"):
        raise SystemExit("JIRA_SITE must be the personal demo site, not a corporate one")
    return site


def jira() -> None:
    """Add the gated acli wrapper and the Atlassian MCP server to a capture home that setup just built."""
    h = CAPTURE_HOME
    site = jira_site()
    acli = h / "bin/acli"
    acli.write_text((CLIENT / "acli.tmpl").read_text().replace("__JIRA_SITE__", site))
    acli.chmod(0o755)
    render(CLIENT / "atlassian-mcp.tmpl", h / "bin/atlassian-mcp")
    (h / "bin/atlassian-mcp").chmod(0o700)

    mcp_path = h / ".cursor/mcp.json"
    mcp = json.loads(mcp_path.read_text())
    mcp["mcpServers"]["atlassian"] = {"command": str(h / "bin/atlassian-mcp")}
    mcp_path.write_text(json.dumps(mcp, indent=2))

    cfg_path = h / ".cursor/cli-config.json"
    cfg = json.loads(cfg_path.read_text())
    allow = cfg["permissions"]["allow"]
    allow += [p for p in ["Shell(acli)", *(f"Mcp(atlassian:{t})" for t in JIRA_READS)] if p not in allow]
    cfg["permissions"]["deny"] = [f"Mcp(atlassian:{t})" for t in JIRA_WRITES]
    cfg_path.write_text(json.dumps(cfg, indent=2))
    cfg_path.chmod(0o600)

    status = subprocess.run(["/opt/homebrew/bin/acli", "jira", "auth", "status"], env=demo_env(),
                            capture_output=True, text=True).stdout
    if f"Site: {site}" not in status:
        raise SystemExit("acli in the capture home is not signed in to the demo site; run acli-login")
    if not any((h / ".mcp-auth").rglob("*tokens.json")):
        raise SystemExit("no Atlassian MCP token in the capture home; run atlassian-login")
    print(f"jira ready in {h}: acli wrapper, Atlassian MCP, MCP write tools denied")


def atlassian_login() -> None:
    sys.exit(subprocess.call(["npx", "-y", "-p", "mcp-remote@0.16.6", "mcp-remote-client", ATLASSIAN_MCP],
                             env=demo_env(), cwd=CAPTURE_HOME))


def acli_login() -> None:
    # acli keeps credentials in the login keychain, which the capture home shares with the real one, so this
    # replaces the real home's entry for the same site and email. Sign the real home in with the same token.
    site = jira_site()
    proc = subprocess.run(["/opt/homebrew/bin/acli", "jira", "auth", "login", "--site", site,
                           "--email", dotenv("JIRA_EMAIL"), "--token"],
                          input=dotenv("JIRA_TOKEN"), text=True, env=demo_env(), capture_output=True)
    print("acli signed in to the demo site" if proc.returncode == 0 else f"acli login failed: {proc.stderr.strip()[:200]}")
    sys.exit(proc.returncode)


def demo_env() -> dict:
    keep = {k: os.environ[k] for k in ("USER", "LOGNAME", "LANG", "TMPDIR") if k in os.environ}
    return {
        **keep,
        "HOME": str(CAPTURE_HOME),
        "ZDOTDIR": str(ROOT / "recorder/zsh"),
        "DEMO_TOOL_PATH": TOOL_PATH,
        "PATH": f"{CAPTURE_HOME}/bin:{TOOL_PATH}:/usr/bin:/bin",
        "SHELL": "/bin/zsh",
        "TERM": "xterm-256color",
        "COLORTERM": "truecolor",
        "LANG": keep.get("LANG", "en_US.UTF-8"),
        "PLAYWRIGHT_BROWSERS_PATH": str(REAL_HOME / "Library/Caches/ms-playwright"),
    }


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "setup":
        setup(os.environ.get("MODEL", ""))
    elif cmd == "jira":
        jira()
    elif cmd == "login":
        sys.exit(subprocess.call(["agent", "login"], env=demo_env(), cwd=CAPTURE_HOME / "payments"))
    elif cmd == "atlassian-login":
        atlassian_login()
    elif cmd == "acli-login":
        acli_login()
    elif cmd == "shell":
        os.execve("/bin/zsh", ["zsh", "-i"], demo_env())
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
