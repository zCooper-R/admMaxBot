from __future__ import annotations

import importlib
import sys

import environ
import pytest
from django.core.exceptions import ImproperlyConfigured


def _import_settings_without_env_file(monkeypatch):
    monkeypatch.setattr(environ.Env, "read_env", lambda *args, **kwargs: None)
    sys.modules.pop("config.settings", None)
    config_module = sys.modules.get("config")
    if config_module is not None and hasattr(config_module, "settings"):
        delattr(config_module, "settings")
    return importlib.import_module("config.settings")


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"DEBUG": "True", "MAXBOT_ENV": "production"}, "DEBUG must be False in production"),
        ({"MAXBOT_ENV": "production", "SECRET_KEY": None}, "SECRET_KEY must be set in production"),
        ({"MAXBOT_ENV": "production", "ALLOWED_HOSTS": None}, "ALLOWED_HOSTS must be set in production"),
        ({"MAXBOT_ENV": "production", "PUBLIC_BASE_URL": None}, "PUBLIC_BASE_URL must be set in production"),
        ({"MAXBOT_ENV": "production", "DATA_ENCRYPTION_KEY": None}, "DATA_ENCRYPTION_KEY must be set in production"),
        (
            {"MAXBOT_ENV": "production", "SECURITY_SSL_REDIRECT": "False"},
            "SECURITY_SSL_REDIRECT must be true in production",
        ),
    ],
)
def test_production_settings_fail_fast(monkeypatch, overrides, message):
    base_env = {
        "MAXBOT_ENV": "production",
        "DEBUG": "False",
        "SECRET_KEY": "prod-secret",
        "ALLOWED_HOSTS": "example.com",
        "PUBLIC_BASE_URL": "https://example.com",
        "DATA_ENCRYPTION_KEY": "2fx0fboi0VyfM0D9uLF3sK7m3P4j_Sca2S6R9CVqgLk=",
        "SECURITY_SSL_REDIRECT": "True",
        "SECURITY_SESSION_COOKIE_SECURE": "True",
        "SECURITY_CSRF_COOKIE_SECURE": "True",
        "SECURITY_HSTS_SECONDS": "3600",
    }
    for key, value in base_env.items():
        monkeypatch.setenv(key, value)
    for key, value in overrides.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)

    with pytest.raises(ImproperlyConfigured, match=message):
        _import_settings_without_env_file(monkeypatch)


def test_production_uses_database_cache_for_integration_status(monkeypatch):
    base_env = {
        "MAXBOT_ENV": "production",
        "DEBUG": "False",
        "SECRET_KEY": "prod-secret",
        "ALLOWED_HOSTS": "example.com",
        "PUBLIC_BASE_URL": "https://example.com",
        "DATA_ENCRYPTION_KEY": "2fx0fboi0VyfM0D9uLF3sK7m3P4j_Sca2S6R9CVqgLk=",
        "SECURITY_SSL_REDIRECT": "True",
        "SECURITY_SESSION_COOKIE_SECURE": "True",
        "SECURITY_CSRF_COOKIE_SECURE": "True",
        "SECURITY_HSTS_SECONDS": "3600",
    }
    for key, value in base_env.items():
        monkeypatch.setenv(key, value)

    imported = _import_settings_without_env_file(monkeypatch)

    assert imported.CACHES["integration_status"]["BACKEND"] == "django.core.cache.backends.db.DatabaseCache"
    assert imported.CACHES["integration_status"]["LOCATION"] == "integration_status_cache"


def test_app_env_alias_enables_production_settings(monkeypatch):
    base_env = {
        "APP_ENV": "production",
        "DEBUG": "False",
        "SECRET_KEY": "prod-secret",
        "ALLOWED_HOSTS": "example.com",
        "BASE_URL": "https://example.com",
        "DATA_ENCRYPTION_KEY": "2fx0fboi0VyfM0D9uLF3sK7m3P4j_Sca2S6R9CVqgLk=",
        "SECURITY_SSL_REDIRECT": "True",
        "SECURITY_SESSION_COOKIE_SECURE": "True",
        "SECURITY_CSRF_COOKIE_SECURE": "True",
        "SECURITY_HSTS_SECONDS": "3600",
    }
    for key, value in base_env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("MAXBOT_ENV", raising=False)
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)

    imported = _import_settings_without_env_file(monkeypatch)

    assert imported.MAXBOT_ENV == "production"
    assert imported.PUBLIC_BASE_URL == "https://example.com"
    assert imported.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
