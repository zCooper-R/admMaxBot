from __future__ import annotations

import logging
from urllib.parse import urlparse

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.accounts.mixins import AdminRequiredMixin, ViewerRequiredMixin
from apps.bot.models import BotSettings, WebhookEvent, WebhookEventStatus, WebhookOperationLog
from apps.core.http import parse_json_request
from apps.core.integration_health import IntegrationHealthService
from apps.max_integration.config import WebhookConfigResolver
from apps.max_integration.services import SubscriptionService

from .forms import WebhookActionForm
from .services import WebhookProcessor

CONFIRMED_UPDATE_TYPES: tuple[tuple[str, str], ...] = (
    ("message_created", "message_created"),
    ("message_callback", "message_callback"),
    ("bot_started", "bot_started"),
)

security_logger = logging.getLogger("errors")


def build_public_webhook_url(request: HttpRequest, webhook_path: str) -> str:
    public_base_url = (getattr(settings, "PUBLIC_BASE_URL", "") or "").strip().rstrip("/")
    normalized_path = webhook_path if webhook_path.startswith("/") else f"/{webhook_path}"
    if public_base_url:
        return f"{public_base_url}{normalized_path}"
    if getattr(settings, "MAXBOT_ENV", "").strip().lower() == "production":
        raise ImproperlyConfigured("PUBLIC_BASE_URL must be set in production")
    return request.build_absolute_uri(normalized_path)


@method_decorator(csrf_exempt, name="dispatch")
class MaxWebhookEndpointView(View):
    def post(self, request: HttpRequest) -> HttpResponse:
        processor = WebhookProcessor()
        if not processor.is_secret_configured() and processor.is_production_mode():
            security_logger.error("webhook_rejected reason=missing_secret_config")
            return JsonResponse({"status": "misconfigured"}, status=503)
        if not processor.validate_secret(request.headers.get("X-Max-Bot-Api-Secret")):
            security_logger.warning("webhook_forbidden reason=invalid_secret")
            return JsonResponse({"status": "forbidden"}, status=403)

        payload, error = parse_json_request(request)
        if error is not None:
            security_logger.warning("webhook_bad_payload")
            return JsonResponse({"status": "bad_payload"}, status=400)

        result = processor.process(payload)
        status_code = 200
        if not result.ok:
            status_code = 400 if result.status == WebhookEventStatus.REJECTED else 503
        return JsonResponse({"status": result.status, "message": result.message}, status=status_code)


class WebhookControlView(ViewerRequiredMixin, View):
    template_name = "webhooks/control.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        settings_obj = BotSettings.objects.filter(id=1).first()
        resolved = WebhookConfigResolver(settings_obj).resolve()
        subscription_service = SubscriptionService(settings_obj, config=resolved)
        info = subscription_service.fetch()
        configured_url = build_public_webhook_url(request, resolved.webhook_path)

        IntegrationHealthService().update_from_subscription_info(
            is_enabled=resolved.is_enabled,
            is_active=info.is_active,
        )

        active_url = None
        subscriptions: list[dict[str, object]] = []
        for item in info.subscriptions:
            normalized = self._normalize_subscription_item(
                item,
                configured_url,
                resolved.webhook_path,
                resolved.webhook_secret,
            )
            subscriptions.append(normalized)
            if active_url is None and isinstance(normalized.get("url"), str) and normalized.get("url"):
                active_url = str(normalized["url"])

        default_url = active_url or configured_url
        context = {
            "settings": settings_obj,
            "info": info,
            "subscriptions": subscriptions,
            "default_url": default_url,
            "active_url": active_url,
            "events": WebhookEvent.objects.select_related("user", "related_node")[:20],
            "operations": WebhookOperationLog.objects.all()[:20],
            "update_type_choices": CONFIRMED_UPDATE_TYPES,
            "default_update_types": ["message_created", "message_callback", "bot_started"],
        }
        return render(request, self.template_name, context)

    @staticmethod
    def _normalize_subscription_item(
        item: object,
        configured_url: str,
        configured_path: str,
        configured_secret: str,
    ) -> dict[str, object]:
        normalized = SubscriptionService.normalize_subscription(item)
        if (
            not normalized.get("has_secret")
            and WebhookControlView._matches_configured_webhook(
                str(normalized.get("url") or ""),
                configured_url,
                configured_path,
            )
            and configured_secret.strip()
        ):
            normalized["has_secret"] = True
        normalized["secret"] = normalized.get("has_secret")
        return normalized

    @staticmethod
    def _matches_configured_webhook(subscription_url: str, configured_url: str, configured_path: str) -> bool:
        if not subscription_url:
            return False
        if subscription_url == configured_url:
            return True

        subscription_path = urlparse(subscription_url).path.rstrip("/")
        configured_url_path = urlparse(configured_url).path.rstrip("/")
        configured_path_only = configured_path.rstrip("/")
        return subscription_path in {configured_url_path, configured_path_only}


class WebhookActionView(AdminRequiredMixin, View):
    def post(self, request: HttpRequest, action: str) -> HttpResponse:
        settings_obj = BotSettings.objects.filter(id=1).first()
        resolved = WebhookConfigResolver(settings_obj).resolve()
        service = SubscriptionService(settings_obj, config=resolved)

        action_form = WebhookActionForm(request.POST)
        action_form.fields["webhook_url"].required = action in {"set", "update", "delete"}
        if action != "check" and not action_form.is_valid():
            messages.error(request, "Введите корректный URL webhook")
            return redirect("webhooks:control")

        public_url = (
            action_form.cleaned_data["webhook_url"]
            if action != "check"
            else build_public_webhook_url(request, resolved.webhook_path)
        )
        selected_update_types = request.POST.getlist("update_types")
        info = service.fetch()
        active_urls = {
            item.get("url")
            for item in info.subscriptions
            if isinstance(item, dict) and isinstance(item.get("url"), str)
        }

        if action == "set":
            if public_url in active_urls:
                messages.warning(request, "Webhook с таким URL уже активен. Используйте 'Обновить'.")
                return redirect("webhooks:control")
            if not resolved.webhook_secret.strip():
                messages.error(
                    request,
                    "Невозможно установить webhook: задайте webhook secret в разделе 'Настройки бота'.",
                )
                return redirect("webhooks:control")
            result = service.set_webhook(
                public_url,
                selected_update_types or ["message_created", "message_callback", "bot_started"],
            )
        elif action == "update":
            if public_url not in active_urls:
                messages.warning(request, "Webhook с таким URL не найден. Используйте 'Установить'.")
                return redirect("webhooks:control")
            if not resolved.webhook_secret.strip():
                messages.error(
                    request,
                    "Невозможно обновить webhook: задайте webhook secret в разделе 'Настройки бота'.",
                )
                return redirect("webhooks:control")
            result = service.set_webhook(
                public_url,
                selected_update_types or ["message_created", "message_callback", "bot_started"],
            )
        elif action == "delete":
            if public_url not in active_urls:
                messages.warning(request, "Webhook с таким URL не найден в активных подписках.")
                return redirect("webhooks:control")
            result = service.delete_webhook(public_url)
        elif action == "check":
            result = service.check_connection()
        else:
            messages.error(request, "Неизвестная операция")
            return redirect("webhooks:control")

        if result["ok"]:
            try:
                IntegrationHealthService().refresh_status()
            except Exception:  # noqa: BLE001
                IntegrationHealthService.invalidate()
            messages.success(request, f"Операция '{action}' выполнена успешно")
        else:
            messages.error(request, f"Ошибка '{action}': {result['error']}")
        return redirect("webhooks:control")


class WebhookEventsView(ViewerRequiredMixin, View):
    template_name = "logs/events.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        qs = WebhookEvent.objects.select_related("user", "related_node")
        status = request.GET.get("status", "").strip()
        event_type = request.GET.get("event_type", "").strip()
        valid_statuses = {choice for choice, _ in WebhookEventStatus.choices}
        if status in valid_statuses:
            qs = qs.filter(status=status)
        if event_type:
            qs = qs.filter(event_type=event_type)
        return render(request, self.template_name, {"events": qs[:200], "status": status, "event_type": event_type})
