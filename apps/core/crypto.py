from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

ENCRYPTED_PREFIX = "enc::"


def _derive_non_production_key() -> str:
    seed = (getattr(settings, "SECRET_KEY", "") or "maxbot-dev-fallback-key").encode("utf-8")
    return base64.urlsafe_b64encode(hashlib.sha256(seed).digest()).decode("ascii")


def get_data_encryption_key() -> str:
    explicit_key = (getattr(settings, "DATA_ENCRYPTION_KEY", "") or "").strip()
    if explicit_key:
        try:
            Fernet(explicit_key.encode("ascii"))
        except Exception as exc:  # noqa: BLE001
            raise ImproperlyConfigured("DATA_ENCRYPTION_KEY must be a valid Fernet key") from exc
        return explicit_key

    if getattr(settings, "MAXBOT_ENV", "development").strip().lower() == "production":
        raise ImproperlyConfigured("DATA_ENCRYPTION_KEY must be set in production")

    return _derive_non_production_key()


def get_fernet() -> Fernet:
    return Fernet(get_data_encryption_key().encode("ascii"))


def is_encrypted_value(value: str | None) -> bool:
    return bool(value and isinstance(value, str) and value.startswith(ENCRYPTED_PREFIX))


def encrypt_value(value: str) -> str:
    if not value:
        return ""
    if is_encrypted_value(value):
        return value
    token = get_fernet().encrypt(value.encode("utf-8")).decode("ascii")
    return f"{ENCRYPTED_PREFIX}{token}"


def decrypt_value(value: str) -> str:
    if not value:
        return ""
    if not is_encrypted_value(value):
        return value
    token = value[len(ENCRYPTED_PREFIX) :]
    try:
        return get_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ImproperlyConfigured("Unable to decrypt stored secret with DATA_ENCRYPTION_KEY") from exc
