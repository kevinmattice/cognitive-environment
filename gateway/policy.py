from __future__ import annotations

import re
from dataclasses import dataclass


POLICY_CONVERSATION_ONLY = "conversation_only"
POLICY_READ_ONLY_PROJECT = "read_only_project"
POLICY_PEM_REQUIRED = "pem_required"
POLICY_PEM_GOVERNED_EXECUTION = "pem_governed_execution"
POLICY_PEM_UNAVAILABLE_BLOCKED = "pem_unavailable_blocked"

_TRUST_AFFECTING_PATTERNS = (
    r"\bfix\b",
    r"\bimplement\b",
    r"\bchange\b",
    r"\bpatch\b",
    r"\bupdate\b",
    r"\bedit\b",
    r"\brewrite\b",
    r"\brefactor\b",
    r"\bdebug\b",
    r"\binvestigate\b",
    r"\breview\b",
    r"\brun the tests?\b",
    r"\brun tests?\b",
    r"\btest this\b",
    r"\bverify\b",
    r"\bconfirm\b",
    r"\bvalidate\b",
    r"\bprove\b",
    r"\brestart\b",
    r"\bdeploy\b",
    r"\bbuild\b",
)

_PROJECT_READ_PATTERNS = (
    r"\bworkspace\b",
    r"\bsources?\b",
    r"\breadme\b",
    r"\bnotes?\b",
    r"\bdocs?\b",
    r"\bfile\b",
    r"\.md\b",
    r"\.txt\b",
    r"\.pdf\b",
)

_PROJECT_READ_VERBS = (
    r"\bwhat is in\b",
    r"\bwhat's in\b",
    r"\bsummarize\b",
    r"\bexplain\b",
    r"\bread\b",
    r"\bshow\b",
    r"\bwhat does\b",
)


@dataclass(frozen=True)
class PolicyDecision:
    state: str
    reason: str
    requires_pem: bool
    allow_model_answer: bool
    allow_grounded_read: bool
    allow_execution: bool


def classify_policy(message: str) -> PolicyDecision:
    text = (message or "").strip()
    lowered = text.lower()

    if not lowered:
        return PolicyDecision(
            state=POLICY_CONVERSATION_ONLY,
            reason="blank_message",
            requires_pem=False,
            allow_model_answer=True,
            allow_grounded_read=False,
            allow_execution=False,
        )

    if any(re.search(pattern, lowered) for pattern in _TRUST_AFFECTING_PATTERNS):
        return PolicyDecision(
            state=POLICY_PEM_REQUIRED,
            reason="trust_affecting_request",
            requires_pem=True,
            allow_model_answer=False,
            allow_grounded_read=False,
            allow_execution=False,
        )

    has_project_read_signal = any(re.search(pattern, lowered) for pattern in _PROJECT_READ_PATTERNS)
    has_project_read_verb = any(re.search(pattern, lowered) for pattern in _PROJECT_READ_VERBS)
    if has_project_read_signal and has_project_read_verb:
        return PolicyDecision(
            state=POLICY_READ_ONLY_PROJECT,
            reason="read_only_project_request",
            requires_pem=False,
            allow_model_answer=True,
            allow_grounded_read=True,
            allow_execution=False,
        )

    return PolicyDecision(
        state=POLICY_CONVERSATION_ONLY,
        reason="ordinary_conversation",
        requires_pem=False,
        allow_model_answer=True,
        allow_grounded_read=False,
        allow_execution=False,
    )


def pem_required_message() -> str:
    return "This request affects project work or verification, so I need PEM-governed execution before I can do it."


def pem_activation_needed_message() -> str:
    return (
        "This request affects project work or verification, and PEM is reachable but inactive, "
        "so it needs activation before I can do it."
    )


def pem_governed_execution_message() -> str:
    return (
        "This request requires PEM-governed execution. PEM is active, so this would transition into "
        "pem_governed_execution, but that execution path is not wired into CCE Lite yet."
    )


def pem_unavailable_message() -> str:
    return (
        "This request requires PEM-governed execution, and PEM is not available right now, "
        "so I’m not going to do the work outside governance."
    )
