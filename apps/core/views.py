from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from apps.accounts.mixins import ViewerRequiredMixin
from apps.audit.models import AuditLog
from apps.bot.models import BotUser, WebhookEvent, WebhookEventStatus


class BotUsersView(ViewerRequiredMixin, View):
    template_name = "users/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        query = request.GET.get("q", "").strip()
        users = BotUser.objects.all().order_by("-last_seen_at")
        if query:
            users = users.filter(external_user_id__icontains=query)
        return render(request, self.template_name, {"users": users[:300], "query": query})


class ErrorsView(ViewerRequiredMixin, View):
    template_name = "logs/errors.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        errors = WebhookEvent.objects.filter(status=WebhookEventStatus.FAILED)[:200]
        return render(request, self.template_name, {"errors": errors})


class AuditView(ViewerRequiredMixin, View):
    template_name = "logs/audit.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        logs = AuditLog.objects.select_related("actor")[:200]
        return render(request, self.template_name, {"logs": logs})

