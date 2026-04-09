import pytest

from apps.max_integration.client import MaxApiClient
from apps.max_integration.services import SubscriptionService


@pytest.mark.django_db
def test_subscription_fetch(monkeypatch, bot_settings):
    def fake_get(self):
        class Obj:
            ok = True
            status_code = 200
            data = {"subscriptions": [{"url": "https://example.com/webhook"}]}
            error = ""

        return Obj()

    monkeypatch.setattr(MaxApiClient, "get_subscriptions", fake_get)
    info = SubscriptionService(bot_settings).fetch()
    assert info.is_active
    assert info.subscriptions[0]["url"] == "https://example.com/webhook"


@pytest.mark.django_db
def test_subscription_fetch_marks_secret_when_api_returns_flag(monkeypatch, bot_settings):
    def fake_get(self):
        class Obj:
            ok = True
            status_code = 200
            data = {
                "subscriptions": [
                    {
                        "url": "https://example.com/webhook",
                        "update_types": ["message_created"],
                        "secret_set": True,
                    }
                ]
            }
            error = ""

        return Obj()

    monkeypatch.setattr(MaxApiClient, "get_subscriptions", fake_get)

    info = SubscriptionService(bot_settings).fetch()

    assert info.subscriptions[0]["has_secret"] is True
