from __future__ import annotations

import logging
from typing import Any

import httpx
from django.conf import settings

from .config import WebhookConfigResolver, WebhookConfigSnapshot
from .types import MaxApiResult

logger = logging.getLogger(__name__)


class MaxApiClient:
    def __init__(self, config: WebhookConfigSnapshot | None = None) -> None:
        self.config = config or WebhookConfigResolver().resolve()

    def _headers(self) -> dict[str, str]:
        token = self.config.token.strip()
        return {
            "Authorization": token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def request(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> MaxApiResult:
        if not self.config.token.strip():
            logger.warning("max_api_request_skipped reason=missing_token")
            return MaxApiResult(
                ok=False,
                status_code=0,
                data={},
                error="Missing bot token in DB/ENV/fallback config",
            )

        base_url = self.config.base_url.rstrip("/")
        url = f"{base_url}{path}"
        try:
            with httpx.Client(timeout=settings.MAX_API_TIMEOUT) as client:
                response = client.request(
                    method,
                    url,
                    headers=self._headers(),
                    json=json_data,
                    params=params,
                )
            payload: dict[str, Any]
            try:
                payload = response.json()
            except ValueError:
                payload = {"raw": response.text}
            return MaxApiResult(
                ok=200 <= response.status_code < 300,
                status_code=response.status_code,
                data=payload,
                error="" if 200 <= response.status_code < 300 else str(payload),
            )
        except httpx.HTTPError as exc:
            logger.exception("max_api_request_failed method=%s path=%s", method, path)
            return MaxApiResult(ok=False, status_code=0, data={}, error=str(exc))

    def get_me(self) -> MaxApiResult:
        return self.request("GET", "/me")

    def get_subscriptions(self) -> MaxApiResult:
        return self.request("GET", "/subscriptions")

    def set_subscription(self, payload: dict[str, Any]) -> MaxApiResult:
        return self.request("POST", "/subscriptions", json_data=payload)

    def delete_subscription(self, url: str) -> MaxApiResult:
        return self.request("DELETE", "/subscriptions", params={"url": url})

    def send_message(
        self, payload: dict[str, Any], params: dict[str, Any] | None = None
    ) -> MaxApiResult:
        return self.request("POST", "/messages", json_data=payload, params=params)

    def answer_callback(self, payload: dict[str, Any]) -> MaxApiResult:
        return self.request("POST", "/answers", json_data=payload)

    def update_message(self, message_id: str, payload: dict[str, Any]) -> MaxApiResult:
        return self.request("PUT", "/messages", json_data=payload, params={"message_id": message_id})
