import pytest
from django.db import connection

from apps.bot.forms import BotSettingsForm
from apps.bot.models import BotSettings


def _fetch_raw_bot_settings_columns() -> tuple[str, str]:
    table = BotSettings._meta.db_table
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT token, webhook_secret FROM {table} WHERE id = 1")
        row = cursor.fetchone()
    assert row is not None
    return str(row[0] or ""), str(row[1] or "")


@pytest.mark.django_db
def test_bot_settings_secrets_are_encrypted_at_rest():
    settings_obj = BotSettings.get_solo()
    settings_obj.token = "plain-token"
    settings_obj.webhook_secret = "plain-secret"
    settings_obj.save()

    raw_token, raw_secret = _fetch_raw_bot_settings_columns()

    assert raw_token != "plain-token"
    assert raw_secret != "plain-secret"
    assert raw_token.startswith("enc::")
    assert raw_secret.startswith("enc::")

    reloaded = BotSettings.get_solo()
    assert reloaded.token == "plain-token"
    assert reloaded.webhook_secret == "plain-secret"


@pytest.mark.django_db
def test_legacy_plaintext_values_are_readable_and_reencrypted_on_save():
    settings_obj = BotSettings.get_solo()
    table = BotSettings._meta.db_table
    with connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {table} SET token = %s, webhook_secret = %s WHERE id = 1",
            ["legacy-token", "legacy-secret"],
        )

    reloaded = BotSettings.get_solo()
    assert reloaded.token == "legacy-token"
    assert reloaded.webhook_secret == "legacy-secret"

    reloaded.save(update_fields=["token", "webhook_secret", "updated_at"])
    raw_token, raw_secret = _fetch_raw_bot_settings_columns()
    assert raw_token.startswith("enc::")
    assert raw_secret.startswith("enc::")


@pytest.mark.django_db
def test_bot_settings_form_keeps_existing_encrypted_values_when_blank():
    settings_obj = BotSettings.get_solo()
    settings_obj.token = "saved-token"
    settings_obj.webhook_secret = "saved-secret"
    settings_obj.save(update_fields=["token", "webhook_secret", "updated_at"])

    form = BotSettingsForm(
        data={
            "token": "",
            "webhook_secret": "",
            "base_url": "https://platform-api.max.ru",
            "webhook_path": "/webhooks/max/",
            "is_enabled": "on",
            "debug_logging": "",
        },
        instance=settings_obj,
    )

    assert form.is_valid(), form.errors
    saved = form.save()
    assert saved.token == "saved-token"
    assert saved.webhook_secret == "saved-secret"
