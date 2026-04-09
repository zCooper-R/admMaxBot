import pytest
from django.urls import reverse

from apps.analytics.services import DailyStatsSyncService
from apps.max_integration.services import SubscriptionService


@pytest.mark.django_db
def test_dashboard_home_uses_cached_integration_status_without_external_fetch(client, viewer_user, monkeypatch):
    client.force_login(viewer_user)

    def fail_if_called(*args, **kwargs):
        pytest.fail("SubscriptionService.fetch should not run on dashboard read-path")

    monkeypatch.setattr(SubscriptionService, "fetch", fail_if_called)

    response = client.get(reverse("dashboard:home"))

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Дашборд" in content
    assert "Аналитика" in content


@pytest.mark.django_db
def test_analytics_overview_does_not_sync_daily_stats_on_get(client, viewer_user, monkeypatch):
    client.force_login(viewer_user)

    def fail_if_called(*args, **kwargs):
        pytest.fail("DailyStats sync should not run in analytics GET view")

    monkeypatch.setattr(DailyStatsSyncService, "ensure_recent", fail_if_called)

    response = client.get(reverse("analytics:overview"))

    assert response.status_code == 200
