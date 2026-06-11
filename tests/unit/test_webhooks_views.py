import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, override_settings

from apps.webhooks.views import build_public_webhook_url


@pytest.mark.django_db
@override_settings(MAXBOT_ENV="production", PUBLIC_BASE_URL="https://example.com")
def test_build_public_webhook_url_uses_public_base_url_in_production(monkeypatch):
    request = RequestFactory().get("/webhooks/control/")

    def fail_if_called(*args, **kwargs):
        pytest.fail("request.build_absolute_uri should not be used in production")

    monkeypatch.setattr(request, "build_absolute_uri", fail_if_called)

    assert build_public_webhook_url(request, "/webhooks/max/") == "https://example.com/webhooks/max/"


@pytest.mark.django_db
@override_settings(
    MAXBOT_ENV="production",
    PUBLIC_BASE_URL="https://example.com",
    WEBHOOK_URL="https://example.com/webhook",
)
def test_build_public_webhook_url_prefers_configured_webhook_url(monkeypatch):
    request = RequestFactory().get("/webhooks/control/")

    def fail_if_called(*args, **kwargs):
        pytest.fail("request.build_absolute_uri should not be used when WEBHOOK_URL is configured")

    monkeypatch.setattr(request, "build_absolute_uri", fail_if_called)

    assert build_public_webhook_url(request, "/webhooks/max/") == "https://example.com/webhook"


@pytest.mark.django_db
@override_settings(MAXBOT_ENV="production", PUBLIC_BASE_URL="")
def test_build_public_webhook_url_requires_public_base_url_in_production():
    request = RequestFactory().get("/webhooks/control/")

    with pytest.raises(ImproperlyConfigured, match="PUBLIC_BASE_URL must be set in production"):
        build_public_webhook_url(request, "/webhooks/max/")
