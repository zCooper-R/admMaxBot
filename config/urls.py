from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("dj-admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("", include("apps.dashboard.urls")),
    path("settings/", include("apps.bot.urls")),
    path("webhooks/", include("apps.webhooks.urls")),
    path("menu/", include("apps.menu_builder.urls")),
    path("analytics/", include("apps.analytics.urls")),
    path("users/", include("apps.core.urls")),
    path("health/", include("apps.core.health_urls")),
]

