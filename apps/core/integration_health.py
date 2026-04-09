from __future__ import annotations

import logging

from django.conf import settings
from django.core.cache import caches

from apps.bot.models import BotSettings
from apps.max_integration.config import WebhookConfigResolver
from apps.max_integration.services import SubscriptionService

logger = logging.getLogger(__name__)


class IntegrationHealthService:
    CACHE_ALIAS = "integration_status"
    CACHE_KEY = "integration-health-v1"
    DEFAULT_WEBHOOK_BADGE = "Неизвестно"
    ACTIVE_WEBHOOK_BADGE = "Активен"
    INACTIVE_WEBHOOK_BADGE = "Не активен"

    @classmethod
    def _cache(cls):
        return caches[cls.CACHE_ALIAS]

    @staticmethod
    def _bot_enabled_badge(is_enabled: bool) -> str:
        return "Включен" if is_enabled else "Отключен"

    def _default_payload(self) -> dict[str, str]:
        settings_obj = BotSettings.objects.filter(id=1).only("is_enabled").first()
        return {
            "bot_enabled": self._bot_enabled_badge(bool(getattr(settings_obj, "is_enabled", False))),
            "webhook_badge": self.DEFAULT_WEBHOOK_BADGE,
        }

    def get_status(self, *, allow_refresh: bool = False) -> dict[str, str]:
        cached: dict[str, str] | None = self._cache().get(self.CACHE_KEY)
        payload = self._default_payload()
        if cached is None:
            if allow_refresh and self._can_refresh():
                return self.refresh_status()
            return payload
        payload["webhook_badge"] = str(cached.get("webhook_badge") or self.DEFAULT_WEBHOOK_BADGE)
        return payload

    def refresh_status(self) -> dict[str, str]:
        settings_obj = BotSettings.objects.filter(id=1).first()
        resolved = WebhookConfigResolver(settings_obj).resolve()
        webhook_badge = self.DEFAULT_WEBHOOK_BADGE
        try:
            subscription = SubscriptionService(settings_obj, config=resolved).fetch()
            webhook_badge = self.ACTIVE_WEBHOOK_BADGE if subscription.is_active else self.INACTIVE_WEBHOOK_BADGE
        except Exception:  # noqa: BLE001
            logger.exception("Failed to refresh integration health")

        payload = {
            "bot_enabled": self._bot_enabled_badge(resolved.is_enabled),
            "webhook_badge": webhook_badge,
        }
        self._cache().set(self.CACHE_KEY, payload, timeout=int(getattr(settings, "INTEGRATION_STATUS_CACHE_TTL", 60)))
        return payload

    def update_from_subscription_info(self, *, is_enabled: bool, is_active: bool | None) -> dict[str, str]:
        if is_active is True:
            webhook_badge = self.ACTIVE_WEBHOOK_BADGE
        elif is_active is False:
            webhook_badge = self.INACTIVE_WEBHOOK_BADGE
        else:
            webhook_badge = self.DEFAULT_WEBHOOK_BADGE
        payload = {
            "bot_enabled": self._bot_enabled_badge(is_enabled),
            "webhook_badge": webhook_badge,
        }
        self._cache().set(self.CACHE_KEY, payload, timeout=int(getattr(settings, "INTEGRATION_STATUS_CACHE_TTL", 60)))
        return payload

    @classmethod
    def invalidate(cls) -> None:
        cls._cache().delete(cls.CACHE_KEY)

    @staticmethod
    def _can_refresh() -> bool:
        settings_obj = BotSettings.objects.filter(id=1).only("token", "is_enabled").first()
        if settings_obj is None:
            return False
        resolved = WebhookConfigResolver(settings_obj).resolve()
        return bool(resolved.token.strip())
