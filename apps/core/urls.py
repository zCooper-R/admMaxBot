from django.urls import path

from .views import AuditView, BotUsersView, ErrorsView

app_name = "core"

urlpatterns = [
    path("", BotUsersView.as_view(), name="users"),
    path("errors/", ErrorsView.as_view(), name="errors"),
    path("audit/", AuditView.as_view(), name="audit"),
]

