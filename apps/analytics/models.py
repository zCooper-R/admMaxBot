from django.db import models


class DailyStats(models.Model):
    date = models.DateField(unique=True)
    users_total = models.PositiveIntegerField(default=0)
    active_users = models.PositiveIntegerField(default=0)
    events_total = models.PositiveIntegerField(default=0)
    button_clicks_total = models.PositiveIntegerField(default=0)
    errors_total = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-date"]
        verbose_name = "Дневная статистика"
        verbose_name_plural = "Дневная статистика"

