from __future__ import annotations

from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .models import UserRole


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    allowed_roles: set[str] = set()

    def test_func(self) -> bool:
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return bool(getattr(user, "role", None) in self.allowed_roles)


class AdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = {UserRole.ADMIN}


class EditorRequiredMixin(RoleRequiredMixin):
    allowed_roles = {UserRole.ADMIN, UserRole.EDITOR}


class ViewerRequiredMixin(RoleRequiredMixin):
    allowed_roles = {UserRole.ADMIN, UserRole.EDITOR, UserRole.VIEWER}

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["is_readonly"] = not self.request.user.is_editor_role
        return ctx

