from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings


@pytest.mark.django_db
@override_settings(MAXBOT_ENV="production")
def test_seed_demo_requires_confirm_outside_dev():
    with pytest.raises(CommandError, match="seed_demo"):
        call_command("seed_demo", stdout=StringIO())


@pytest.mark.django_db
@override_settings(MAXBOT_ENV="production")
def test_seed_demo_allows_confirm_flag_outside_dev():
    out = StringIO()
    call_command("seed_demo", "--confirm", stdout=out)
    assert "Демо-данные готовы" in out.getvalue()
