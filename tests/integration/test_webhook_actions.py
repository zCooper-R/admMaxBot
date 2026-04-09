import pytest
from django.urls import reverse

from apps.max_integration.services import SubscriptionService
from apps.max_integration.types import WebhookSubscriptionInfo


@pytest.mark.django_db
@pytest.mark.parametrize("action", ["set", "update", "delete"])
def test_webhook_action_requires_url(client, admin_user, monkeypatch, action):
    client.force_login(admin_user)

    def fail_if_called(*args, **kwargs):
        pytest.fail("Subscription service should not be called for invalid webhook_url")

    monkeypatch.setattr(SubscriptionService, "set_webhook", fail_if_called)
    monkeypatch.setattr(SubscriptionService, "delete_webhook", fail_if_called)

    response = client.post(
        reverse("webhooks:action", kwargs={"action": action}),
        data={"webhook_url": ""},
    )

    assert response.status_code == 302


@pytest.mark.django_db
def test_webhook_control_shows_secret_as_set_for_configured_subscription(
    client,
    viewer_user,
    bot_settings,
    monkeypatch,
):
    client.force_login(viewer_user)
    bot_settings.webhook_secret = "secret123"
    bot_settings.webhook_path = "/webhooks/max/"
    bot_settings.save(update_fields=["webhook_secret", "webhook_path", "updated_at"])

    def fake_fetch(self):
        return WebhookSubscriptionInfo(
            raw={"subscriptions": [{"url": "http://testserver/webhooks/max/", "update_types": ["bot_started"]}]},
            subscriptions=[{"url": "http://testserver/webhooks/max/", "update_types": ["bot_started"]}],
        )

    monkeypatch.setattr(SubscriptionService, "fetch", fake_fetch)

    response = client.get(reverse("webhooks:control"))

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Установлен" in content


@pytest.mark.django_db
def test_webhook_control_shows_secret_as_set_when_host_differs_but_path_matches(
    client,
    viewer_user,
    bot_settings,
    monkeypatch,
):
    client.force_login(viewer_user)
    bot_settings.webhook_secret = "secret123"
    bot_settings.webhook_path = "/webhooks/max/"
    bot_settings.save(update_fields=["webhook_secret", "webhook_path", "updated_at"])

    def fake_fetch(self):
        return WebhookSubscriptionInfo(
            raw={
                "subscriptions": [
                    {
                        "url": "https://kerri-asdfasdf.ngrok-free.dev/webhooks/max/",
                        "update_types": ["message_callback", "message_created", "bot_started"],
                    }
                ]
            },
            subscriptions=[
                {
                    "url": "https://kerri-asdfasdf.ngrok-free.dev/webhooks/max/",
                    "update_types": ["message_callback", "message_created", "bot_started"],
                }
            ],
        )

    monkeypatch.setattr(SubscriptionService, "fetch", fake_fetch)

    response = client.get(reverse("webhooks:control"))

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Установлен" in content
