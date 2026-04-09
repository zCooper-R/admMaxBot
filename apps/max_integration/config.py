from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from django.conf import settings

from apps.bot.models import BotSettings

logger = logging.getLogger(__name__)


def _mask_secret(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        return "<empty>"
    if len(trimmed) <= 7:
        return "*" * len(trimmed)
    return f"{trimmed[:4]}***{trimmed[-3:]}"


def _to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


@dataclass(frozen=True, slots=True)
class WebhookConfigSnapshot:
    token: str
    webhook_secret: str
    base_url: str
    webhook_path: str
    is_enabled: bool
    debug_logging: bool
    source_map: dict[str, str]


class WebhookConfigResolver:
    """
    Resolves runtime webhook configuration with strict priority:
    1) DB
    2) ENV
    3) Django settings/model defaults
    """

    ENV_TOKEN = "MAX_BOT_TOKEN"
    ENV_WEBHOOK_SECRET = "MAX_WEBHOOK_SECRET"
    ENV_BASE_URL = "MAX_API_BASE_URL"
    ENV_WEBHOOK_PATH = "MAX_WEBHOOK_PATH"
    ENV_IS_ENABLED = "MAX_BOT_ENABLED"
    ENV_DEBUG_LOGGING = "MAX_DEBUG_LOGGING"

    def __init__(self, db_settings: BotSettings | None = None) -> None:
        self.db_settings = db_settings

    def resolve(self) -> WebhookConfigSnapshot:
        db_settings = self.db_settings or BotSettings.objects.filter(id=1).first()
        source_map: dict[str, str] = {}

        token = self._resolve_str(
            db_value=db_settings.token if db_settings else "",
            env_key=self.ENV_TOKEN,
            fallback="",
            source_key="token",
            source_map=source_map,
        )
        webhook_secret = self._resolve_str(
            db_value=db_settings.webhook_secret if db_settings else "",
            env_key=self.ENV_WEBHOOK_SECRET,
            fallback="",
            source_key="webhook_secret",
            source_map=source_map,
        )
        base_url = self._resolve_str(
            db_value=db_settings.base_url if db_settings else "",
            env_key=self.ENV_BASE_URL,
            fallback=getattr(settings, "MAX_API_BASE_URL", "https://platform-api.max.ru"),
            source_key="base_url",
            source_map=source_map,
        ).rstrip("/")
        webhook_path = self._resolve_webhook_path(
            db_value=db_settings.webhook_path if db_settings else "",
            env_key=self.ENV_WEBHOOK_PATH,
            fallback="/webhooks/max/",
            source_map=source_map,
        )

        is_enabled = self._resolve_bool(
            db_value=db_settings.is_enabled if db_settings else None,
            env_key=self.ENV_IS_ENABLED,
            fallback=True,
            source_key="is_enabled",
            source_map=source_map,
        )
        debug_logging = self._resolve_bool(
            db_value=db_settings.debug_logging if db_settings else None,
            env_key=self.ENV_DEBUG_LOGGING,
            fallback=False,
            source_key="debug_logging",
            source_map=source_map,
        )

        snapshot = WebhookConfigSnapshot(
            token=token,
            webhook_secret=webhook_secret,
            base_url=base_url,
            webhook_path=webhook_path,
            is_enabled=is_enabled,
            debug_logging=debug_logging,
            source_map=source_map,
        )
        self._log_snapshot(snapshot)
        return snapshot

    def _resolve_str(
        self,
        *,
        db_value: str | None,
        env_key: str,
        fallback: str,
        source_key: str,
        source_map: dict[str, str],
    ) -> str:
        if isinstance(db_value, str) and db_value.strip():
            value = db_value.strip()
            source_map[source_key] = "db"
            return value
        env_value = os.getenv(env_key)
        if isinstance(env_value, str) and env_value.strip():
            value = env_value.strip()
            source_map[source_key] = "env"
            return value
        source_map[source_key] = "fallback"
        return fallback

    def _resolve_bool(
        self,
        *,
        db_value: bool | None,
        env_key: str,
        fallback: bool,
        source_key: str,
        source_map: dict[str, str],
    ) -> bool:
        if db_value is not None:
            source_map[source_key] = "db"
            return bool(db_value)
        env_value = os.getenv(env_key)
        if env_value is not None:
            source_map[source_key] = "env"
            return _to_bool(env_value, fallback)
        source_map[source_key] = "fallback"
        return fallback

    def _resolve_webhook_path(
        self,
        *,
        db_value: str | None,
        env_key: str,
        fallback: str,
        source_map: dict[str, str],
    ) -> str:
        raw = self._resolve_str(
            db_value=db_value,
            env_key=env_key,
            fallback=fallback,
            source_key="webhook_path",
            source_map=source_map,
        )
        if not raw.startswith("/"):
            raw = f"/{raw}"
        if not raw.endswith("/"):
            raw = f"{raw}/"
        return raw

    def _log_snapshot(self, snapshot: WebhookConfigSnapshot) -> None:
        if not snapshot.debug_logging:
            return
        logger.info(
            "bot_token source=%s masked=%s length=%s",
            snapshot.source_map.get("token"),
            _mask_secret(snapshot.token),
            len(snapshot.token),
        )
        logger.info(
            "webhook_secret source=%s masked=%s length=%s",
            snapshot.source_map.get("webhook_secret"),
            _mask_secret(snapshot.webhook_secret),
            len(snapshot.webhook_secret),
        )
        logger.info(
            "base_url source=%s value=%s",
            snapshot.source_map.get("base_url"),
            snapshot.base_url,
        )
        logger.info(
            "webhook_path source=%s value=%s",
            snapshot.source_map.get("webhook_path"),
            snapshot.webhook_path,
        )
        logger.info(
            "is_enabled source=%s value=%s",
            snapshot.source_map.get("is_enabled"),
            snapshot.is_enabled,
        )
