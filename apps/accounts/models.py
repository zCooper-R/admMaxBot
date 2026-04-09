from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    ADMIN = "admin", "Администратор"
    EDITOR = "editor", "Редактор"
    VIEWER = "viewer", "Наблюдатель"


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.VIEWER)

    @property
    def is_admin_role(self) -> bool:
        return self.role == UserRole.ADMIN or self.is_superuser

    @property
    def is_editor_role(self) -> bool:
        return self.role in {UserRole.ADMIN, UserRole.EDITOR} or self.is_superuser

