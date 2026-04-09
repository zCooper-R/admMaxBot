from django import forms

from .models import BotSettings


class BotSettingsForm(forms.ModelForm):
    token = forms.CharField(
        label="Токен бота",
        required=False,
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password"}),
        help_text="Оставьте пустым, чтобы сохранить текущее значение.",
    )
    webhook_secret = forms.CharField(
        label="Webhook secret",
        required=False,
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password"}),
        help_text="Оставьте пустым, чтобы сохранить текущее значение.",
    )

    class Meta:
        model = BotSettings
        fields = [
            "token",
            "webhook_secret",
            "base_url",
            "webhook_path",
            "is_enabled",
            "debug_logging",
        ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        token = (self.instance.token or "").strip() if self.instance and self.instance.pk else ""
        secret = (self.instance.webhook_secret or "").strip() if self.instance and self.instance.pk else ""
        if token:
            self.fields["token"].help_text = "Сохранено в базе. Оставьте пустым, чтобы не менять."
            self.fields["token"].widget.attrs["placeholder"] = self._mask(token)
        else:
            self.fields["token"].help_text = "Пока не задано."
        if secret:
            self.fields["webhook_secret"].help_text = "Сохранено в базе. Оставьте пустым, чтобы не менять."
            self.fields["webhook_secret"].widget.attrs["placeholder"] = self._mask(secret)
        else:
            self.fields["webhook_secret"].help_text = "Пока не задано."

    def clean_webhook_path(self) -> str:
        value = self.cleaned_data["webhook_path"].strip()
        if not value.startswith("/"):
            raise forms.ValidationError("Путь webhook должен начинаться с /")
        if not value.endswith("/"):
            value = f"{value}/"
        return value

    def clean_token(self) -> str:
        incoming = (self.cleaned_data.get("token") or "").strip()
        if self._looks_masked(incoming):
            return self.instance.token if self.instance and self.instance.pk else ""
        if incoming:
            return incoming
        if self.instance and self.instance.pk:
            return self.instance.token
        return ""

    def clean_webhook_secret(self) -> str:
        incoming = (self.cleaned_data.get("webhook_secret") or "").strip()
        if self._looks_masked(incoming):
            return self.instance.webhook_secret if self.instance and self.instance.pk else ""
        if incoming:
            return incoming
        if self.instance and self.instance.pk:
            return self.instance.webhook_secret
        return ""

    @staticmethod
    def _looks_masked(value: str) -> bool:
        if not value:
            return False
        mask_chars = {"*", "•", "●", "·", "."}
        if set(value) <= mask_chars:
            return True
        return "***" in value or "•••" in value

    @staticmethod
    def _mask(value: str) -> str:
        if len(value) <= 7:
            return "*" * len(value)
        return f"{value[:4]}***{value[-3:]}"

