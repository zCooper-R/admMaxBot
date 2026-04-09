from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class AuditLog(TimeStampedModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs"
    )
    action = models.CharField("Действие", max_length=64)
    entity_type = models.CharField("Тип сущности", max_length=64)
    entity_id = models.CharField("ID сущности", max_length=128)
    before_data = models.JSONField("До", blank=True, null=True)
    after_data = models.JSONField("После", blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Аудит"
        verbose_name_plural = "Аудит"

