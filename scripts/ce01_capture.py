#!/usr/bin/env python3
"""CE-01 capture environment for Cursor CLI and GitHub Copilot CLI.

  python3 scripts/ce01_capture.py setup            # build the neutral capture HOME (idempotent)
  python3 scripts/ce01_capture.py jira             # after setup: add Jira (acli + Atlassian MCP) for SO-07
  python3 scripts/ce01_capture.py notebook A,B,C   # after setup: add the gated jpterm wrapper for SO-03; A,B,C are the held cells
  python3 scripts/ce01_capture.py n8n              # after setup: add the gated n8n-contain wrapper for SO-08
  python3 scripts/ce01_capture.py outlook          # after setup: load the Outlook plugin, read tools only, for SO-08
  python3 scripts/ce01_capture.py search-reads     # after setup: splunkctl runs read-only searches without confirmation
  python3 scripts/ce01_capture.py login            # one-time client login inside the capture HOME (Cursor or Copilot)
  python3 scripts/ce01_capture.py atlassian-login  # one-time Atlassian MCP OAuth, as the demo-site account
  python3 scripts/ce01_capture.py acli-login       # one-time acli login to the demo site with the .env token
  python3 scripts/ce01_capture.py shell            # open the pinned demo shell (dry runs, manual checks)

The capture HOME lives at /Users/Shared/splunk-demo so paths render as ~/payments and no
username appears. Secrets are copied in with 0600 permissions and never printed.

CAPTURE_STACK=<name> points setup at another Splunk stack: its web address and login state, splunkctl config, and
MCP token come from .captures/ce01/stacks/<name>/ (built by scripts/stack_profile.py) instead of the shared CO2 stack.

CAPTURE_CLIENT=copilot-cli builds the home for GitHub Copilot CLI instead of Cursor CLI (pipeline.capture sets it from
the scenario's client.name): ~/.copilot/ with the Splunk MCP server, the skills, the trusted workspace, and a `copilot`
launcher in ~/bin that fixes the flags every take runs with (recorder/clients/copilot-cli/copilot.tmpl).
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
# Templates both clients share (MCP bridge, workspace instructions, gated wrappers) live with Cursor's.
CLIENT = ROOT / "recorder/clients/cursor-cli"
COPILOT = ROOT / "recorder/clients/copilot-cli"
CLIENT_NAME = os.environ.get("CAPTURE_CLIENT", "cursor-cli")
STACK = os.environ.get("CAPTURE_STACK", "")
PROFILE = ROOT / ".captures/ce01/stacks" / STACK if STACK else None
SECRETS = PROFILE / "secrets" if PROFILE else ROOT / ".captures/ce01/secrets"
SPLUNKCTL_CONFIG = PROFILE / "splunkctl.yaml" if PROFILE else REAL_HOME / ".splunkctl/config.yaml"
MCP_ENV = PROFILE / "splunk-mcp.env" if PROFILE else REAL_HOME / ".cursor/mcp-secrets/splunk-mcp.env"
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
# Some stacks' MCP servers register tools that write; writes go through splunkctl's confirmation instead.
SPLUNK_MCP_WRITES = ["Mcp(splunk:search_create_splunk_alert)", "Mcp(splunk:search_record_containment_action)"]
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
# The notebook demo (SO-03): a gated jpterm and a plain euporie-preview over a private Python environment.
NOTEBOOK_SHIMS = ("jpterm", "euporie-preview")
NOTEBOOK_ALLOW = ["Shell(jpterm)", "Shell(euporie-preview)"]
NOTEBOOK_VENV = CAPTURE_HOME / "nb"
# The phishing demo (SO-08): containment goes through the gated n8n-contain wrapper to the n8n webhook.
N8N_SHIMS = ("n8n-contain",)
N8N_WEBHOOK_PATH = "webhook/contain-phishing"
# The Outlook plugin's MCP server is Cursor-hosted and signs in to Microsoft with `/mcp` > Log in in the capture
# HOME. Cursor CLI only loads a plugin passed with --plugin-dir, so an `agent` shim adds it. The agent reads the
# report; nothing in the story writes mail.
OUTLOOK_SERVER = "plugin-outlook-outlook"
OUTLOOK_READS = ["get_me", "list_mail_folders", "list_mail_messages", "get_mail_message", "get_next_page"]
OUTLOOK_WRITES = ["send_mail", "send_draft", "create_draft", "update_draft", "reply_to_mail_message",
                  "forward_mail_message", "move_mail_message", "update_mail_message", "delete_mail_message",
                  "create_mail_folder", "delete_mail_folder"]
OUTLOOK_SHIMS = ("agent",)
# Copilot CLI's deny rules for the same MCP write tools; the launcher reads them from ~/.config/copilot-deny.
COPILOT_DENY = ["splunk(search_create_splunk_alert)", "splunk(search_record_containment_action)"]


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
    for d in ("bin", "payments", ".config", ".cache/playwright-cli", ".playwright", ".cursor/skills", ".copilot/skills"):
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

    for path in (SPLUNKCTL_CONFIG, MCP_ENV):
        if not path.exists():
            raise SystemExit(f"{path.relative_to(ROOT) if path.is_relative_to(ROOT) else path.name} is missing"
                             + (f"; build the profile with scripts/stack_profile.py init {STACK}" if STACK else ""))
    private_copy(SPLUNKCTL_CONFIG, h / ".splunkctl/config.yaml")
    private_copy(MCP_ENV, h / ".config/splunk-mcp.env")
    web_state = SECRETS / "web-state.json"
    if web_state.exists():
        private_copy(web_state, h / ".config/splunk-web-state.json")
    else:
        # Demos without Splunk Web screenshots (SO-08 on an SSO stack) don't need a saved login.
        print("no saved Splunk Web login: playwright-cli opens Splunk Web logged out "
              f"(run scripts/splunk_web_login.mjs{f' with CAPTURE_STACK={STACK}' if STACK else ''} if the demo needs it)")
        (h / ".config/splunk-web-state.json").write_text('{"cookies": [], "origins": []}\n')
        (h / ".config/splunk-web-state.json").chmod(0o600)

    # Jira is opt-in per demo (`ce01_capture.py jira`); a plain setup leaves no trace of it.
    for name in (*JIRA_SHIMS, *NOTEBOOK_SHIMS, *N8N_SHIMS, *OUTLOOK_SHIMS, "copilot"):
        (h / "bin" / name).unlink(missing_ok=True)
    for name in ("jpterm-gates", "hunt.env", "n8n-contain.env"):
        (h / ".config" / name).unlink(missing_ok=True)
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
    # The skills CLI installs Cursor's skills here, so an earlier demo's skills would otherwise stay loaded.
    shutil.rmtree(h / ".agents/skills", ignore_errors=True)
    env = demo_env()
    extra_skills = [s for s in os.environ.get("CAPTURE_SKILLS", "").split(",") if s and s not in PUBLIC_SKILLS]
    for name in [*PUBLIC_SKILLS, *extra_skills]:
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

    if CLIENT_NAME == "copilot-cli":
        setup_copilot(skills)
        return

    # Cursor CLI hangs on a hand-written config, so only patch the one it generated on first run.
    cfg_path = h / ".cursor/cli-config.json"
    if not cfg_path.exists():
        print(f"capture home ready: {h}\nrun Cursor CLI once in the capture home, then rerun setup to pin settings")
        return
    cfg = json.loads(cfg_path.read_text())
    cfg.update({
        "permissions": {"allow": PERMISSIONS, "deny": SPLUNK_MCP_WRITES},
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


def _jsonc(path: Path) -> dict:
    """Copilot CLI's config.json starts with // comment lines."""
    if not path.exists():
        return {}
    return json.loads("\n".join(l for l in path.read_text().splitlines() if not l.lstrip().startswith("//")) or "{}")


def setup_copilot(installed_skills: Path) -> None:
    """The Copilot CLI half of setup: the skills, the MCP server, settings, a trusted workspace, and the launcher."""
    h = CAPTURE_HOME
    c = h / ".copilot"
    skills = c / "skills"
    shutil.rmtree(skills, ignore_errors=True)
    # The skills were installed the way Cursor finds them; Copilot reads ~/.copilot/skills.
    shutil.copytree(installed_skills, skills)
    for d in installed_skills.iterdir():
        shutil.rmtree(d)
    render(COPILOT / "mcp-config.json.tmpl", c / "mcp-config.json")
    (c / "settings.json").write_text(json.dumps({
        "banner": "never", "autoUpdate": False, "beep": False, "notifications": False,
        # The footer would show the account's AI credit use in every frame.
        "footer": {"showAiUsed": False, "showQuota": False},
    }, indent=2) + "\n")
    # Folder trust is CLI-managed state; without it the first prompt is a trust dialog. Sign-in state stays.
    cfg = _jsonc(c / "config.json")
    cfg["trustedFolders"] = [str(h / "payments")]
    cfg["askedSetupTerminals"] = sorted(set(cfg.get("askedSetupTerminals", [])) | {"vscode", "iterm2", "apple_terminal"})
    (c / "config.json").write_text(json.dumps(cfg, indent=2) + "\n")
    (c / "config.json").chmod(0o600)
    (h / ".config/copilot-deny").write_text("".join(f"{rule}\n" for rule in COPILOT_DENY))
    real = shutil.which("copilot", path=TOOL_PATH)
    if not real:
        raise SystemExit("GitHub Copilot CLI is not installed: brew install --cask copilot-cli")
    launcher = h / "bin/copilot"
    launcher.write_text((COPILOT / "copilot.tmpl").read_text().replace("__COPILOT_BIN__", real))
    launcher.chmod(0o755)
    signed_in = any(k in cfg for k in ("loggedInUsers", "lastLoggedInUser", "logged_in_users"))
    print(f"capture home ready for Copilot CLI: {h}"
          + ("" if signed_in else "\nif Copilot isn't signed in here yet: CAPTURE_CLIENT=copilot-cli python3 scripts/ce01_capture.py login"))


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


def notebook(gated: list[str]) -> None:
    """Add the notebook tools to a capture home that setup just built: the environment, the gated jpterm, the viewer."""
    h = CAPTURE_HOME
    if not (NOTEBOOK_VENV / "bin/jpterm").exists():
        subprocess.run(["uv", "venv", "--python", "3.12", str(NOTEBOOK_VENV)], check=True)
        subprocess.run(["uv", "pip", "install", "--python", str(NOTEBOOK_VENV / "bin/python"), "-q",
                        "-r", str(ROOT / "recorder/notebook/requirements.txt")], check=True)
    for name in NOTEBOOK_SHIMS:
        shim = h / "bin" / name
        shim.write_text((CLIENT / f"{name}.tmpl").read_text().replace("__NB_VENV__", str(NOTEBOOK_VENV)))
        shim.chmod(0o755)
    (h / ".config/jpterm-gates").write_text("".join(f"{cell}\n" for cell in gated))

    cfg_path = h / ".cursor/cli-config.json"
    if CLIENT_NAME == "cursor-cli" and cfg_path.exists():
        cfg = json.loads(cfg_path.read_text())
        allow = cfg["permissions"]["allow"]
        allow += [p for p in NOTEBOOK_ALLOW if p not in allow]
        cfg_path.write_text(json.dumps(cfg, indent=2))
        cfg_path.chmod(0o600)
    print(f"notebook tools ready; held cells: {', '.join(gated)}")


def n8n() -> None:
    """Add the gated n8n-contain wrapper to a capture home that setup just built."""
    h = CAPTURE_HOME
    shim = h / "bin/n8n-contain"
    shim.write_text((CLIENT / "n8n-contain.tmpl").read_text())
    shim.chmod(0o755)
    env = h / ".config/n8n-contain.env"
    env.write_text(f"N8N_CONTAIN_URL={dotenv('N8N_URL').rstrip('/')}/{N8N_WEBHOOK_PATH}\n"
                   f"N8N_WEBHOOK_TOKEN={dotenv('N8N_WEBHOOK_TOKEN')}\n")
    env.chmod(stat.S_IRUSR | stat.S_IWUSR)

    cfg_path = h / ".cursor/cli-config.json"
    if CLIENT_NAME == "cursor-cli":
        cfg = json.loads(cfg_path.read_text())
        allow = cfg["permissions"]["allow"]
        allow += [p for p in ["Shell(n8n-contain)"] if p not in allow]
        cfg_path.write_text(json.dumps(cfg, indent=2))
        cfg_path.chmod(0o600)
    print(f"n8n ready in {h}: gated n8n-contain wrapper")


def search_reads() -> None:
    """Swap the splunkctl shim for one that confirms read-only searches, for demos gated somewhere else.

    SO-08 runs the Agent Launchpad agent with `| aiagent` through splunkctl: the run takes over a minute, longer
    than Cursor CLI waits for an MCP tool call."""
    shim = CAPTURE_HOME / "bin/splunkctl"
    shim.write_text((CLIENT / "splunkctl-reads.tmpl").read_text())
    shim.chmod(0o755)
    print(f"search-reads ready in {CAPTURE_HOME}: splunkctl confirms searches without write commands")


def outlook() -> None:
    """Load the Outlook plugin in a capture home that setup just built, with only its read tools allowed."""
    if CLIENT_NAME != "cursor-cli":
        raise SystemExit("the Outlook plugin is Cursor-hosted; record this demo with cursor-cli")
    h = CAPTURE_HOME
    cached = sorted((REAL_HOME / ".cursor/plugins/cache/cursor-public/outlook").glob("*/.cursor-plugin"),
                    key=lambda p: p.stat().st_mtime)
    if not cached:
        raise SystemExit("install the Outlook plugin in Cursor first; its folder is copied from the plugin cache")
    plugin = h / ".cursor/plugins-local/outlook"
    shutil.rmtree(plugin, ignore_errors=True)
    shutil.copytree(cached[-1].parent, plugin)
    shim = h / "bin/agent"
    shim.write_text(f'#!/bin/sh\nexec {REAL_HOME}/.local/bin/agent --plugin-dir "$HOME/.cursor/plugins-local/outlook" "$@"\n')
    shim.chmod(0o755)

    cfg_path = h / ".cursor/cli-config.json"
    cfg = json.loads(cfg_path.read_text())
    allow, deny = cfg["permissions"]["allow"], cfg["permissions"]["deny"]
    allow += [p for p in (f"Mcp({OUTLOOK_SERVER}:{t})" for t in OUTLOOK_READS) if p not in allow]
    deny += [p for p in (f"Mcp({OUTLOOK_SERVER}:{t})" for t in OUTLOOK_WRITES) if p not in deny]
    cfg_path.write_text(json.dumps(cfg, indent=2))
    cfg_path.chmod(0o600)
    print(f"outlook ready in {h}: plugin loaded through the agent shim, MCP write tools denied; "
          "sign in once with `/mcp` > Outlook > Log in if it reports needsAuth")


def jira() -> None:
    """Add the gated acli wrapper and the Atlassian MCP server to a capture home that setup just built."""
    if CLIENT_NAME != "cursor-cli":
        raise SystemExit("the Jira integration is wired for Cursor CLI only so far")
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
    # Dry runs only: a Copilot CLI take against your own model (BYOK) instead of the signed-in account.
    # Never set these for a published take; the model name would show in Copilot's footer.
    keep |= {k: v for k, v in os.environ.items() if k.startswith("COPILOT_PROVIDER_") or k in ("COPILOT_MODEL", "COPILOT_OFFLINE")}
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
    elif cmd == "n8n":
        n8n()
    elif cmd == "outlook":
        outlook()
    elif cmd == "search-reads":
        search_reads()
    elif cmd == "notebook":
        notebook([c for c in (sys.argv[2] if len(sys.argv) > 2 else "").split(",") if c])
    elif cmd == "login":
        # The real copilot binary, not the capture home's launcher, which puts its flags before the subcommand.
        login = [shutil.which("copilot", path=TOOL_PATH) or "copilot", "login"] if CLIENT_NAME == "copilot-cli" \
            else ["agent", "login"]
        # Extra flags pass through, e.g. `login --device-code` to approve with a chosen GitHub account.
        sys.exit(subprocess.call(login + sys.argv[2:], env=demo_env(), cwd=CAPTURE_HOME / "payments"))
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
