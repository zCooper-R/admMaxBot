from django.contrib import admin
from django.urls import include, path

from apps.webhooks.views import MaxWebhookEndpointView

urlpatterns = [
    path("dj-admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("", include("apps.dashboard.urls")),
    path("settings/", include("apps.bot.urls")),
    path("webhook", MaxWebhookEndpointView.as_view(), name="max-webhook"),
    path("webhook/", MaxWebhookEndpointView.as_view(), name="max-webhook-slash"),
    path("webhooks/", include("apps.webhooks.urls")),
    path("menu/", include("apps.menu_builder.urls")),
    path("analytics/", include("apps.analytics.urls")),
    path("users/", include("apps.core.urls")),
    path("health/", include("apps.core.health_urls")),
]
