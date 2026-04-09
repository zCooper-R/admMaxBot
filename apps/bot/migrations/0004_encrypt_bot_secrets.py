from django.db import migrations, models


def encrypt_existing_bot_secrets(apps, schema_editor):
    from apps.core.crypto import encrypt_value, is_encrypted_value

    BotSettings = apps.get_model("bot", "BotSettings")

    for settings_obj in BotSettings.objects.exclude(token="", webhook_secret=""):
        changed_fields: list[str] = []
        if settings_obj.token and not is_encrypted_value(settings_obj.token):
            settings_obj.token = encrypt_value(settings_obj.token)
            changed_fields.append("token")
        if settings_obj.webhook_secret and not is_encrypted_value(settings_obj.webhook_secret):
            settings_obj.webhook_secret = encrypt_value(settings_obj.webhook_secret)
            changed_fields.append("webhook_secret")
        if changed_fields:
            settings_obj.save(update_fields=changed_fields + ["updated_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("bot", "0003_usersessionstate_chat_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="botsettings",
            name="token",
            field=models.CharField(blank=True, max_length=2048, verbose_name="Токен бота"),
        ),
        migrations.AlterField(
            model_name="botsettings",
            name="webhook_secret",
            field=models.CharField(blank=True, max_length=1024, verbose_name="Webhook secret"),
        ),
        migrations.RunPython(encrypt_existing_bot_secrets, reverse_code=migrations.RunPython.noop),
    ]
