from django.contrib.auth.forms import AuthenticationForm


class RussianAuthenticationForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Неверный логин или пароль.",
        "inactive": "Пользователь отключен.",
    }

