import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model

from apps.accounts.admin import UserAdmin
from apps.accounts.models import UserRole


@pytest.mark.django_db
def test_accounts_admin_add_form_hashes_password():
    model_admin = UserAdmin(get_user_model(), AdminSite())
    form_class = model_admin.get_form(request=None, obj=None)
    form = form_class(
        data={
            "username": "new_admin_user",
            "password1": "StrongPass12345",
            "password2": "StrongPass12345",
            "role": UserRole.ADMIN,
        }
    )

    assert form.is_valid(), form.errors

    user = form.save()

    assert user.password != "StrongPass12345"
    assert user.check_password("StrongPass12345") is True
