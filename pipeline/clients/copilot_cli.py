"""GitHub Copilot CLI adapter.

Copilot CLI writes one directory per session under ~/.copilot/session-state/<session-id>/, and its events.jsonl
holds every step in order: `user.message`, `assistant.message` (text and tool requests), `tool.execution_start`
and `tool.execution_complete` (arguments, full result, exit code), and `tool.user_requested` for a command the
person ran in shell mode (`!`). Tool output in the log is complete even where the TUI collapsed it.
"""

import json
import re
from pathlib import Path

from . import Event

# How the TUI shows the client is working, and how it shows it is ready for a prompt (for the capture driver).
TURN_STARTED = "ctrl\\+c interrupt"
READY = "open sidebar"
# The TUI redraws only changed cells, so transcript times come from the rendered screen (pipeline.transcript).
SCREEN_CLOCK = True
# Shell results end with a status line the TUI does not show.
_STATUS = re.compile(r"\n?<(?:shellId: \S+ completed|exited) with exit code \d+>\s*$")


def find_store(capture_home: Path, prompt: str) -> Path:
    """The session whose user messages contain the scenario prompt; newest wins."""
    logs = sorted((capture_home / ".copilot/session-state").glob("*/events.jsonl"),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    needle = json.dumps(prompt[:80])[1:-1]
    for log in logs:
        if needle in log.read_text(errors="replace"):
            return log
    raise FileNotFoundError(f"no Copilot session in {capture_home} contains the prompt")


def _result(data: dict) -> str:
    result = data.get("result") or {}
    text = result.get("content", "") if isinstance(result, dict) else str(result)
    return text if isinstance(text, str) else json.dumps(text)


def load_session(store: Path) -> list[Event]:
    events: list[Event] = []
    calls: dict[str, Event] = {}
    for line in store.read_text().splitlines():
        entry = json.loads(line)
        kind, data = entry.get("type"), entry.get("data") or {}
        if kind == "user.message" and data.get("content", "").strip():
            events.append(Event("user", text=data["content"].strip()))
        elif kind == "assistant.message" and (data.get("content") or "").strip():
            events.append(Event("agent", text=data["content"].strip()))
        elif kind in ("tool.execution_start", "tool.user_requested"):
            args = data.get("arguments") or {}
            call = Event("call", tool=data.get("toolName", ""), args=args if isinstance(args, dict) else {},
                         by_user=kind == "tool.user_requested")
            if data.get("mcpServerName"):
                call.args = {"__server": data["mcpServerName"], "__tool": data.get("mcpToolName") or call.tool,
                             "arguments": call.args}
                call.tool = "mcp"
            calls[data.get("toolCallId", "")] = call
            events.append(call)
        elif kind == "tool.execution_complete":
            call = calls.get(data.get("toolCallId", ""))
            if call is not None:
                call.result = _result(data)
                exit_code = (data.get("shellExecution") or {}).get("exitCode")
                if exit_code is not None:
                    call.args["__exit"] = exit_code
    return events


def normalize_call(call: Event) -> tuple[str, dict]:
    """Map a Copilot tool call to a neutral action: shell, mcp, read, skill, write, or plumbing."""
    if call.tool in ("bash", "local_shell"):
        return "shell", {"command": call.args.get("command", ""),
                         "output": {"exit": call.args.get("__exit"), "text": _STATUS.sub("", call.result).strip()}}
    if call.tool == "mcp":
        return "mcp", {"server": call.args["__server"], "tool": call.args["__tool"],
                       "args": call.args.get("arguments") or {}, "output": call.result}
    if call.tool == "skill":
        return "skill", {"name": call.args.get("skill", "")}
    if call.tool == "view":
        return "read", {"path": call.args.get("path", ""), "output": call.result}
    if call.tool in ("edit", "create", "apply_patch"):
        return "write", {"path": call.args.get("path", "")}
    return "plumbing", {}


def mcp_label(server: str, tool: str) -> str:
    """The text the TUI draws for an MCP call, for timing it on the cast."""
    return tool
