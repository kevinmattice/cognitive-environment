from __future__ import annotations

from dataclasses import dataclass


SAFE_COMMAND_HELP = "Unknown command. Supported commands: status, workspace list, workspace open <id>, workspace status, sources, read <source>, ask <question>"


COMMAND_LIKE_PREFIXES = {
    "workspace",
    "read",
    "source",
    "sources",
    "open",
    "close",
    "delete",
    "run",
    "shell",
    "exec",
    "tool",
    "config",
    "model",
    "pem",
}


@dataclass(frozen=True)
class RouteDecision:
    action: str  # "ignore" | "command" | "ask" | "help"
    question: str | None = None


def decide_route(message: str, *, has_active_workspace: bool) -> RouteDecision:
    text = (message or "").strip()
    if not text:
        return RouteDecision(action="ignore")

    lowered = text.lower()

    # Explicit ask path always wins.
    if lowered == "ask":
        return RouteDecision(action="command")
    if lowered.startswith("ask "):
        return RouteDecision(action="ask", question=text[4:].strip())

    # Known commands stay commands.
    if lowered == "status":
        return RouteDecision(action="command")
    if lowered.startswith("workspace ") or lowered == "workspace":
        return RouteDecision(action="command")
    if lowered == "sources" or lowered.startswith("sources "):
        return RouteDecision(action="command")
    if lowered.startswith("read ") or lowered == "read":
        return RouteDecision(action="command")

    # Command-like unknowns remain safe and do not route to the model.
    first = lowered.split()[0]
    if first in COMMAND_LIKE_PREFIXES:
        return RouteDecision(action="help")

    # Ordinary text: route to grounded QA only if a workspace is active.
    if has_active_workspace:
        return RouteDecision(action="ask", question=text)
    return RouteDecision(action="help")

