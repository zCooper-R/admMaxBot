import pytest
from django.test import RequestFactory

from apps.bot.models import BotSettings
from apps.core.context_processors import global_status
from apps.core.integration_health import IntegrationHealthService
from apps.max_integration.services import SubscriptionService


@pytest.mark.django_db
def test_get_status_returns_default_without_network_when_cache_is_empty(bot_settings, monkeypatch):
    IntegrationHealthService.invalidate()
    bot_settings.is_enabled = True
    bot_settings.save(update_fields=["is_enabled", "updated_at"])

    def fail_if_called(*args, **kwargs):
        pytest.fail("Integration status read should not trigger external fetch")

    monkeypatch.setattr(SubscriptionService, "fetch", fail_if_called)

    status = IntegrationHealthService().get_status()

    assert status == {"bot_enabled": "Включен", "webhook_badge": "Неизвестно"}


@pytest.mark.django_db
def test_update_from_subscription_info_warms_cached_status(bot_settings):
    bot_settings.is_enabled = False
    bot_settings.save(update_fields=["is_enabled", "updated_at"])
    service = IntegrationHealthService()

    service.update_from_subscription_info(is_enabled=False, is_active=True)

    assert service.get_status() == {"bot_enabled": "Отключен", "webhook_badge": "Активен"}


@pytest.mark.django_db
def test_global_status_refreshes_cache_outside_dashboard_when_token_exists(bot_settings, monkeypatch):
    IntegrationHealthService.invalidate()
    bot_settings.token = "token-123"
    bot_settings.is_enabled = True
    bot_settings.save(update_fields=["token", "is_enabled", "updated_at"])

    def fake_fetch(self):
        class Info:
            is_active = True

        return Info()

    monkeypatch.setattr(SubscriptionService, "fetch", fake_fetch)

    request = RequestFactory().get("/menu/")
    request.resolver_match = type("ResolverMatch", (), {"app_name": "menu_builder"})()

    status = global_status(request)

    assert status["webhook_badge"] == "Активен"
