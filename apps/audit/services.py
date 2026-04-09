from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Model, QuerySet

from .models import AuditLog


User = get_user_model()


def _to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _to_jsonable(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, Model):
        return {
            "_model": value.__class__.__name__,
            "id": value.pk,
            "repr": str(value),
        }
    if isinstance(value, QuerySet):
        return [_to_jsonable(item) for item in value]
    return str(value)


def audit_action(
    actor: Any,
    action: str,
    entity_type: str,
    entity_id: str,
    before_data: dict[str, Any] | None,
    after_data: dict[str, Any] | None,
) -> None:
    if actor is not None and getattr(actor, "is_authenticated", False):
        user = actor
    else:
        user = None
    AuditLog.objects.create(
        actor=user,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_data=_to_jsonable(before_data),
        after_data=_to_jsonable(after_data),
    )
