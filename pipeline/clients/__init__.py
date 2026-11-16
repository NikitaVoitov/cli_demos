"""Client adapters: each turns one AI client's session log into neutral events."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Event:
    """One step of a recorded session, independent of the client that produced it."""

    kind: str                      # "user" | "agent" | "call"
    text: str = ""                 # user or agent text
    tool: str = ""                 # client tool name for calls, e.g. Shell, Read, CallMcpTool
    args: dict[str, Any] = field(default_factory=dict)
    result: str = ""
    by_user: bool = False          # a call the person ran directly (Cursor shell mode, Claude Code "!")
