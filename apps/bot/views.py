from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views import View

from apps.accounts.mixins import AdminRequiredMixin
from apps.audit.services import audit_action
from apps.core.integration_health import IntegrationHealthService

from .forms import BotSettingsForm
from .models import BotSettings


class BotSettingsView(AdminRequiredMixin, View):
    template_name = "settings/bot_settings.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        settings_obj = BotSettings.get_solo()
        form = BotSettingsForm(instance=settings_obj)
        return render(request, self.template_name, {"form": form, "settings": settings_obj})

    def post(self, request: HttpRequest) -> HttpResponse:
        settings_obj = BotSettings.get_solo()
        token_before = settings_obj.token or ""
        secret_before = settings_obj.webhook_secret or ""
        before = {
            "base_url": settings_obj.base_url,
            "webhook_path": settings_obj.webhook_path,
            "is_enabled": settings_obj.is_enabled,
            "debug_logging": settings_obj.debug_logging,
            "token_meta": {"length": len(token_before), "masked": self._mask(token_before)},
            "webhook_secret_meta": {"length": len(secret_before), "masked": self._mask(secret_before)},
        }
        form = BotSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            saved = form.save()
            token_after = saved.token or ""
            secret_after = saved.webhook_secret or ""
            after = {
                "base_url": saved.base_url,
                "webhook_path": saved.webhook_path,
                "is_enabled": saved.is_enabled,
                "debug_logging": saved.debug_logging,
                "token_meta": {"length": len(token_after), "masked": self._mask(token_after)},
                "webhook_secret_meta": {
                    "length": len(secret_after),
                    "masked": self._mask(secret_after),
                },
            }
            audit_action(request.user, "update", "BotSettings", str(saved.id), before, after)
            IntegrationHealthService.invalidate()
            messages.success(request, "Настройки бота сохранены")
            return redirect("bot:settings")
        messages.error(request, "Проверьте форму: есть ошибки")
        return render(request, self.template_name, {"form": form, "settings": settings_obj})

    @staticmethod
    def _mask(value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            return "<empty>"
        if len(trimmed) <= 7:
            return "*" * len(trimmed)
        return f"{trimmed[:4]}***{trimmed[-3:]}"

