from django.urls import path

from .health import healthcheck

urlpatterns = [
    path("", healthcheck, name="health"),
]

