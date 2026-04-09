from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy

from .forms import RussianAuthenticationForm


class AppLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = RussianAuthenticationForm


class AppLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")

