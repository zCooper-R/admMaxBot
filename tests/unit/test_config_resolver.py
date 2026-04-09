import os

import pytest

from apps.bot.models import BotSettings
from apps.max_integration.config import WebhookConfigResolver


@pytest.mark.django_db
def test_resolver_prefers_db_over_env(monkeypatch):
    settings_obj = BotSettings.get_solo()
    settings_obj.token = "db-token"
    settings_obj.webhook_secret = "db-secret"
    settings_obj.base_url = "https://db.example"
    settings_obj.webhook_path = "/db-hook/"
    settings_obj.save()

    monkeypatch.setenv("MAX_BOT_TOKEN", "env-token")
    monkeypatch.setenv("MAX_WEBHOOK_SECRET", "env-secret")
    monkeypatch.setenv("MAX_API_BASE_URL", "https://env.example")
    monkeypatch.setenv("MAX_WEBHOOK_PATH", "/env-hook/")

    cfg = WebhookConfigResolver(settings_obj).resolve()
    assert cfg.token == "db-token"
    assert cfg.webhook_secret == "db-secret"
    assert cfg.base_url == "https://db.example"
    assert cfg.webhook_path == "/db-hook/"


@pytest.mark.django_db
def test_resolver_falls_back_to_env_when_db_empty(monkeypatch):
    settings_obj = BotSettings.get_solo()
    settings_obj.token = ""
    settings_obj.webhook_secret = ""
    settings_obj.webhook_path = ""
    settings_obj.save(update_fields=["token", "webhook_secret", "webhook_path", "updated_at"])

    monkeypatch.setenv("MAX_BOT_TOKEN", "env-token")
    monkeypatch.setenv("MAX_WEBHOOK_SECRET", "env-secret")
    monkeypatch.setenv("MAX_WEBHOOK_PATH", "/env-hook")

    cfg = WebhookConfigResolver(settings_obj).resolve()
    assert cfg.token == "env-token"
    assert cfg.webhook_secret == "env-secret"
    assert cfg.webhook_path == "/env-hook/"
