from django.urls import path

from .views import BotSettingsView

app_name = "bot"

urlpatterns = [
    path("", BotSettingsView.as_view(), name="settings"),
]

