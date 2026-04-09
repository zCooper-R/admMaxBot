from django.http import HttpRequest

from apps.core.integration_health import IntegrationHealthService


def global_status(request: HttpRequest) -> dict[str, str]:
    service = IntegrationHealthService()
    app_name = getattr(getattr(request, "resolver_match", None), "app_name", "")
    if app_name not in {"dashboard", "analytics"}:
        return service.get_status(allow_refresh=True)
    return service.get_status()
