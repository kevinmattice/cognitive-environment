from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PemStatusSnapshot:
    state: str  # active | inactive | unavailable | ambiguous
    reachable: bool
    active: bool
    message: str


def get_pem_status() -> PemStatusSnapshot:
    return PemStatusSnapshot(
        state="unavailable",
        reachable=False,
        active=False,
        message="PEM status is not wired into CCE yet.",
    )

