from __future__ import annotations

from typing import Any

from apps.bot.models import BotSettings, WebhookOperationLog, WebhookOperationType

from .client import MaxApiClient
from .config import WebhookConfigResolver, WebhookConfigSnapshot
from .types import WebhookSubscriptionInfo


class SubscriptionService:
    def __init__(
        self,
        settings_obj: BotSettings | None = None,
        config: WebhookConfigSnapshot | None = None,
    ) -> None:
        self.settings_obj = settings_obj or BotSettings.objects.filter(id=1).first()
        self.config = config or WebhookConfigResolver(self.settings_obj).resolve()
        self.client = MaxApiClient(self.config)

    def fetch(self) -> WebhookSubscriptionInfo:
        result = self.client.get_subscriptions()
        data = result.data if isinstance(result.data, dict) else {}
        subs = data.get("subscriptions") if isinstance(data, dict) else []
        raw_subscriptions = subs if isinstance(subs, list) else []
        subscriptions = [self.normalize_subscription(item) for item in raw_subscriptions]
        return WebhookSubscriptionInfo(raw=data, subscriptions=subscriptions)

    def set_webhook(self, public_webhook_url: str, event_types: list[str] | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"url": public_webhook_url}
        secret = self.config.webhook_secret.strip()
        if secret:
            body["secret"] = secret
        if event_types:
            body["update_types"] = event_types
        result = self.client.set_subscription(body)
        self._log(WebhookOperationType.SET, body, result.data, "ok" if result.ok else "error")
        return {"ok": result.ok, "status_code": result.status_code, "data": result.data, "error": result.error}

    def delete_webhook(self, public_webhook_url: str) -> dict[str, Any]:
        request_payload = {"url": public_webhook_url}
        result = self.client.delete_subscription(public_webhook_url)
        self._log(
            WebhookOperationType.DELETE,
            request_payload,
            result.data,
            "ok" if result.ok else "error",
        )
        return {"ok": result.ok, "status_code": result.status_code, "data": result.data, "error": result.error}

    def check_connection(self) -> dict[str, Any]:
        result = self.client.get_me()
        self._log(WebhookOperationType.CHECK, {}, result.data, "ok" if result.ok else "error")
        return {"ok": result.ok, "status_code": result.status_code, "data": result.data, "error": result.error}

    def _log(
        self,
        operation_type: WebhookOperationType,
        request_payload: dict[str, Any],
        response_payload: dict[str, Any],
        status: str,
    ) -> None:
        WebhookOperationLog.objects.create(
            operation_type=operation_type,
            request_payload=self._sanitize_payload(request_payload),
            response_payload=self._sanitize_payload(response_payload),
            status=status,
        )

    @staticmethod
    def _sanitize_payload(payload: Any) -> Any:
        if payload is None:
            return None
        if isinstance(payload, dict):
            sanitized: dict[str, Any] = {}
            for key, value in payload.items():
                key_lower = str(key).lower()
                if any(token in key_lower for token in ("token", "secret", "authorization", "password")):
                    sanitized[key] = "***"
                else:
                    sanitized[key] = SubscriptionService._sanitize_payload(value)
            return sanitized
        if isinstance(payload, list):
            return [SubscriptionService._sanitize_payload(item) for item in payload]
        return payload

    @staticmethod
    def normalize_subscription(item: Any) -> dict[str, Any]:
        if not isinstance(item, dict):
            return {}

        normalized = dict(item)
        update_types = normalized.get("update_types")
        normalized["update_types"] = update_types if isinstance(update_types, list) else []
        normalized["has_secret"] = SubscriptionService._has_secret_marker(normalized)
        return normalized

    @staticmethod
    def _has_secret_marker(item: dict[str, Any]) -> bool:
        markers = (
            "secret",
            "has_secret",
            "secret_set",
            "is_secret_set",
            "hasSecret",
            "secretSet",
            "isSecretSet",
        )
        for key in markers:
            value = item.get(key)
            if isinstance(value, str):
                if value.strip():
                    return True
                continue
            if value:
                return True
        return False


class MessageService:
    def __init__(
        self,
        settings_obj: BotSettings | None = None,
        config: WebhookConfigSnapshot | None = None,
    ) -> None:
        self.settings_obj = settings_obj or BotSettings.objects.filter(id=1).first()
        self.config = config or WebhookConfigResolver(self.settings_obj).resolve()
        self.client = MaxApiClient(self.config)

    def send_text(
        self,
        chat_id: int | None,
        text: str,
        buttons: list[list[dict[str, Any]]] | None = None,
        edit_message_id: str | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"text": text}
        if buttons:
            body["attachments"] = [
                {
                    "type": "inline_keyboard",
                    "payload": {"buttons": buttons},
                }
            ]
        if edit_message_id:
            edit_result = self.client.update_message(edit_message_id, body)
            if edit_result.ok:
                return {
                    "ok": True,
                    "status_code": edit_result.status_code,
                    "data": edit_result.data,
                    "error": "",
                    "message_id": self._extract_message_id(edit_result.data) or edit_message_id,
                }
        params: dict[str, Any] = {}
        if chat_id is not None:
            params["chat_id"] = chat_id
        elif user_id is not None:
            params["user_id"] = user_id
        else:
            return {
                "ok": False,
                "status_code": 0,
                "data": {},
                "error": "Missing chat_id/user_id for outbound message",
                "message_id": None,
            }

        send_result = self.client.send_message(body, params=params)
        return {
            "ok": send_result.ok,
            "status_code": send_result.status_code,
            "data": send_result.data,
            "error": send_result.error,
            "message_id": self._extract_message_id(send_result.data),
        }

    @staticmethod
    def _extract_message_id(data: dict[str, Any]) -> str | None:
        if not isinstance(data, dict):
            return None
        direct = data.get("message_id") or data.get("mid")
        if isinstance(direct, str) and direct:
            return direct
        body = data.get("body")
        if isinstance(body, dict):
            body_mid = body.get("mid")
            if isinstance(body_mid, str) and body_mid:
                return body_mid
        message = data.get("message")
        if isinstance(message, dict):
            msg_mid = message.get("mid")
            if isinstance(msg_mid, str) and msg_mid:
                return msg_mid
            body = message.get("body")
            if isinstance(body, dict):
                mid = body.get("mid")
                if isinstance(mid, str) and mid:
                    return mid
        return None
