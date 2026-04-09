from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class MaxApiResult:
    ok: bool
    status_code: int
    data: dict[str, Any]
    error: str = ""


@dataclass(slots=True)
class WebhookSubscriptionInfo:
    raw: dict[str, Any]
    subscriptions: list[dict[str, Any]]

    @property
    def is_active(self) -> bool:
        return len(self.subscriptions) > 0

