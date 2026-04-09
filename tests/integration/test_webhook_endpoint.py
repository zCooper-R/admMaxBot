import json

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from django.urls import reverse

from apps.bot.models import BotUser, UserSessionState, WebhookEvent, WebhookEventStatus
from apps.webhooks.services import (
    SAFE_PROCESSING_ERROR_CODE,
    SAFE_PROCESSING_ERROR_MESSAGE,
    WebhookProcessor,
)
from apps.webhooks.views import build_public_webhook_url


@pytest.mark.django_db
def test_webhook_secret_validation(client, bot_settings):
    bot_settings.webhook_secret = "secret123"
    bot_settings.save(update_fields=["webhook_secret", "updated_at"])
    url = reverse("webhooks:endpoint")
    response = client.post(url, data=json.dumps({"update_id": "1"}), content_type="application/json")
    assert response.status_code == 403


@pytest.mark.django_db
def test_webhook_idempotency(client, bot_settings):
    bot_settings.webhook_secret = "secret123"
    bot_settings.save(update_fields=["webhook_secret", "updated_at"])
    url = reverse("webhooks:endpoint")
    payload = {
        "update_id": "evt-1",
        "update_type": "message_created",
        "chat_id": 1001,
        "user": {"user_id": "u1", "name": "Test"},
    }
    response1 = client.post(
        url,
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_X_MAX_BOT_API_SECRET="secret123",
    )
    response2 = client.post(
        url,
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_X_MAX_BOT_API_SECRET="secret123",
    )
    assert response1.status_code == 200
    assert response2.status_code == 200
    assert WebhookEvent.objects.filter(external_event_id="evt-1").count() == 1


@pytest.mark.django_db
def test_webhook_rejects_unsupported_update_type_without_side_effects(client, bot_settings):
    bot_settings.webhook_secret = "secret123"
    bot_settings.save(update_fields=["webhook_secret", "updated_at"])

    url = reverse("webhooks:endpoint")
    payload = {
        "update_id": "evt-unsupported",
        "update_type": "unsupported_type",
        "chat_id": 1001,
        "user": {"user_id": "u1", "name": "Test"},
    }

    response = client.post(
        url,
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_X_MAX_BOT_API_SECRET="secret123",
    )

    assert response.status_code == 400
    assert WebhookEvent.objects.filter(external_event_id="evt-unsupported").count() == 0
    assert WebhookEvent.objects.count() == 0


@pytest.mark.django_db
def test_webhook_internal_failure_returns_retry_status(monkeypatch, client, bot_settings):
    bot_settings.webhook_secret = "secret123"
    bot_settings.is_enabled = True
    bot_settings.save(update_fields=["webhook_secret", "is_enabled", "updated_at"])

    def fake_process_business(self, payload, user, event):
        raise RuntimeError("token=secret123 upstream failure")

    monkeypatch.setattr(WebhookProcessor, "_process_business", fake_process_business)

    url = reverse("webhooks:endpoint")
    payload = {
        "update_id": "evt-fail-1",
        "update_type": "message_created",
        "chat_id": 1001,
        "user": {"user_id": "u1", "name": "Test"},
    }

    response = client.post(
        url,
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_X_MAX_BOT_API_SECRET="secret123",
    )

    assert response.status_code == 503
    event = WebhookEvent.objects.get(external_event_id="evt-fail-1")
    assert event.status == WebhookEventStatus.FAILED
    assert SAFE_PROCESSING_ERROR_CODE in event.error_message
    assert SAFE_PROCESSING_ERROR_MESSAGE in event.error_message
    assert "token=secret123" not in event.error_message


@pytest.mark.django_db
@override_settings(DEBUG=False, MAXBOT_ENV="production")
def test_webhook_rejects_empty_secret_in_production_mode(client, bot_settings):
    bot_settings.webhook_secret = ""
    bot_settings.save(update_fields=["webhook_secret", "updated_at"])

    url = reverse("webhooks:endpoint")
    response = client.post(
        url,
        data=json.dumps({"update_id": "evt-prod-1"}),
        content_type="application/json",
    )

    assert response.status_code == 503
    assert WebhookEvent.objects.filter(external_event_id="evt-prod-1").count() == 0


@pytest.mark.django_db
def test_webhook_error_is_sanitized_in_db_and_ui(client, bot_settings, viewer_user, monkeypatch):
    bot_settings.webhook_secret = "secret123"
    bot_settings.is_enabled = True
    bot_settings.save(update_fields=["webhook_secret", "is_enabled", "updated_at"])
    raw_error = "token=super-secret upstream timeout"

    def fake_process_business(self, payload, user, event):
        raise RuntimeError(raw_error)

    monkeypatch.setattr(WebhookProcessor, "_process_business", fake_process_business)

    url = reverse("webhooks:endpoint")
    payload = {
        "update_id": "evt-sanitized",
        "update_type": "message_created",
        "chat_id": 1001,
        "user": {"user_id": "u1", "name": "Test"},
    }

    response = client.post(
        url,
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_X_MAX_BOT_API_SECRET="secret123",
    )

    assert response.status_code == 503
    event = WebhookEvent.objects.get(external_event_id="evt-sanitized")
    assert SAFE_PROCESSING_ERROR_CODE in event.error_message
    assert SAFE_PROCESSING_ERROR_MESSAGE in event.error_message
    assert raw_error not in event.error_message

    client.force_login(viewer_user)
    page = client.get(reverse("core:errors"))
    content = page.content.decode("utf-8")
    assert page.status_code == 200
    assert raw_error not in content
    assert SAFE_PROCESSING_ERROR_MESSAGE in content


@pytest.mark.django_db
def test_webhook_rejects_unsupported_update_type_without_side_effects(client, bot_settings):
    bot_settings.webhook_secret = "secret123"
    bot_settings.save(update_fields=["webhook_secret", "updated_at"])
    url = reverse("webhooks:endpoint")

    response = client.post(
        url,
        data=json.dumps(
            {
                "update_id": "evt-unsupported",
                "update_type": "unsupported_event",
                "chat_id": 1001,
                "user": {"user_id": "u1", "name": "Test"},
            }
        ),
        content_type="application/json",
        HTTP_X_MAX_BOT_API_SECRET="secret123",
    )

    assert response.status_code == 400
    assert response.json()["message"] == "unsupported_update_type"
    assert WebhookEvent.objects.filter(external_event_id="evt-unsupported").count() == 0
    assert BotUser.objects.filter(external_user_id="u1").count() == 0
    assert UserSessionState.objects.count() == 0


@pytest.mark.django_db
def test_webhook_rejects_malformed_payload_without_side_effects(client, bot_settings):
    bot_settings.webhook_secret = "secret123"
    bot_settings.save(update_fields=["webhook_secret", "updated_at"])
    url = reverse("webhooks:endpoint")

    response = client.post(
        url,
        data=json.dumps(
            {
                "update_id": "evt-malformed",
                "update_type": "message_created",
                "message": {"body": {"text": "hello"}},
            }
        ),
        content_type="application/json",
        HTTP_X_MAX_BOT_API_SECRET="secret123",
    )

    assert response.status_code == 400
    assert response.json()["message"] == "missing_user_id"
    assert WebhookEvent.objects.filter(external_event_id="evt-malformed").count() == 0
    assert BotUser.objects.count() == 0
    assert UserSessionState.objects.count() == 0


def test_build_public_webhook_url_requires_public_base_url_in_production(rf, settings):
    settings.MAXBOT_ENV = "production"
    settings.PUBLIC_BASE_URL = ""

    with pytest.raises(ImproperlyConfigured, match="PUBLIC_BASE_URL must be set in production"):
        build_public_webhook_url(rf.get("/webhooks/control/"), "/webhooks/max/")
