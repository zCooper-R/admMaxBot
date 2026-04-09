from django.urls import path

from .views import MaxWebhookEndpointView, WebhookActionView, WebhookControlView, WebhookEventsView

app_name = "webhooks"

urlpatterns = [
    path("max/", MaxWebhookEndpointView.as_view(), name="endpoint"),
    path("control/", WebhookControlView.as_view(), name="control"),
    path("action/<str:action>/", WebhookActionView.as_view(), name="action"),
    path("events/", WebhookEventsView.as_view(), name="events"),
]

