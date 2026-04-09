from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from apps.accounts.mixins import ViewerRequiredMixin
from apps.analytics.models import DailyStats


class AnalyticsOverviewView(ViewerRequiredMixin, View):
    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, "dashboard/analytics.html", {"stats": DailyStats.objects.all()[:60]})

