from io import StringIO

import pytest
from django.core.management import call_command

from apps.analytics.services import DailyStatsSyncService


@pytest.mark.django_db
def test_sync_daily_stats_command_calls_service(monkeypatch):
    called: list[int] = []

    def fake_ensure_recent(self, window_days):
        called.append(window_days)

    monkeypatch.setattr(DailyStatsSyncService, "ensure_recent", fake_ensure_recent)

    out = StringIO()
    call_command("sync_daily_stats", "--window-days", "30", stdout=out)

    assert called == [30]
    assert "30" in out.getvalue()
