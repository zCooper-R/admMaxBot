from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from apps.accounts.mixins import ViewerRequiredMixin

from .services import DashboardService


class DashboardHomeView(ViewerRequiredMixin, View):
    def get(self, request: HttpRequest) -> HttpResponse:
        context = DashboardService().summary()
        return render(request, "dashboard/home.html", context)

