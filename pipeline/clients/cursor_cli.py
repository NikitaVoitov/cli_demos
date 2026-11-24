"""Cursor CLI adapter.

Cursor CLI keeps each chat in ~/.cursor/chats/<workspace-hash>/<chat-id>/store.db: a `blobs`
table of content-addressed messages (JSON for user, assistant, and tool messages) and a `meta`
row whose `latestRootBlobId` points at a protobuf list of 32-byte blob IDs in message order.
agent-transcripts/*.jsonl holds only tool inputs, so the store is the source of tool results.
"""

import json
import re
import sqlite3
from pathlib import Path

from . import Event

SHELL_MODE = re.compile(r"^Run the following command: (.+)$", re.S)
USER_QUERY = re.compile(r"<user_query>\s*(.*?)\s*</user_query>", re.S)
# How the TUI shows the client is working, and how it shows it is ready for a prompt (for the capture driver).
TURN_STARTED = "ctrl\\+c to stop"
READY = "Plan, search, build anything"


def mcp_label(server: str, tool: str) -> str:
    """The text the TUI draws for an MCP call, for timing it on the cast."""
    return f"{server} {tool}"


def find_store(capture_home: Path, prompt: str) -> Path:
    """The chat whose user messages contain the scenario prompt; newest wins."""
    stores = sorted((capture_home / ".cursor/chats").glob("*/*/store.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    needle = prompt[:80].encode()
    for store in stores:
        db = sqlite3.connect(store)
        if any(needle in (d if isinstance(d, bytes) else str(d).encode()) for (d,) in db.execute("select data from blobs")):
            return store
    raise FileNotFoundError(f"no Cursor chat in {capture_home} contains the prompt")


def _ordered_messages(store: Path) -> list[dict]:
    db = sqlite3.connect(store)
    meta = json.loads(bytes.fromhex(db.execute("select value from meta where key='0'").fetchone()[0]))
    blobs = {i: (d if isinstance(d, bytes) else str(d).encode()) for i, d in db.execute("select id, data from blobs")}
    root = blobs[meta["latestRootBlobId"]]
    order: list[str] = []
    for i in range(len(root) - 31):
        ref = root[i : i + 32].hex()
        if ref in blobs and (not order or order[-1] != ref):
            order.append(ref)
    messages = []
    for ref in order:
        try:
            message = json.loads(blobs[ref])
        except ValueError:
            continue
        if isinstance(message, dict) and message.get("role") in ("user", "assistant", "tool"):
            messages.append(message)
    return messages


def _text(content) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(p.get("text", "") for p in content if p.get("type") == "text")


def _result(value) -> str:
    return value if isinstance(value, str) else json.dumps(value)


def load_session(store: Path) -> list[Event]:
    events: list[Event] = []
    calls: dict[str, Event] = {}
    pending_shell_mode = False
    for message in _ordered_messages(store):
        role, content = message["role"], message["content"]
        if role == "user":
            text = _text(content)
            if "<user_info>" in text:
                continue
            shell = SHELL_MODE.match(text.strip())
            if shell:
                pending_shell_mode = True
                continue
            query = USER_QUERY.search(text)
            events.append(Event("user", text=(query.group(1) if query else text).strip()))
        elif role == "assistant":
            for part in content if isinstance(content, list) else [{"type": "text", "text": content}]:
                if part.get("type") == "text" and part.get("text", "").strip():
                    events.append(Event("agent", text=part["text"].strip()))
                elif part.get("type") == "tool-call":
                    call = Event("call", tool=part["toolName"], args=part.get("args") or {}, by_user=pending_shell_mode)
                    pending_shell_mode = False
                    calls[part["toolCallId"]] = call
                    events.append(call)
        elif role == "tool":
            for part in content:
                call = calls.get(part.get("toolCallId"))
                if call is not None:
                    call.result = _result(part.get("result"))
    return events


def normalize_call(call: Event) -> tuple[str, dict]:
    """Map a Cursor tool call to a neutral action: shell, mcp, read, write, or plumbing."""
    if call.tool == "Shell":
        return "shell", {"command": call.args.get("command", ""), "output": shell_output(call.result)}
    if call.tool in ("CallDynamicTool", "CallMcpTool") and call.args.get("namespace") not in (None, "cursor"):
        return "mcp", {"server": call.args.get("namespace"), "tool": call.args.get("toolName"),
                       "args": call.args.get("arguments") or {}, "output": call.result}
    if call.tool == "Read":
        return "read", {"path": call.args.get("path", ""), "output": call.result}
    if call.tool in ("Write", "StrReplace", "Edit"):
        return "write", {"path": call.args.get("path", "")}
    return "plumbing", {}


def shell_output(result: str) -> dict:
    """Cursor wraps shell results as 'Exit code: N ... Command output: ```...```'."""
    code = re.search(r"Exit code: (\d+)", result)
    body = re.search(r"Command output:\s*```\n?(.*?)\n?```", result, re.S)
    return {"exit": int(code.group(1)) if code else None, "text": (body.group(1) if body else result).strip()}
