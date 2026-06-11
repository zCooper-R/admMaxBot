from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(
    APP_ENV=(str, ""),
    DEBUG=(bool, False),
    MAXBOT_ENV=(str, ""),
    SECRET_KEY=(str, ""),
    ALLOWED_HOSTS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
    DATABASE_URL=(str, f"sqlite:///{(BASE_DIR / 'db.sqlite3').as_posix()}"),
    BASE_URL=(str, ""),
    WEBHOOK_URL=(str, ""),
    MAX_API_BASE_URL=(str, "https://platform-api.max.ru"),
    MAX_API_TIMEOUT=(int, 20),
    PUBLIC_BASE_URL=(str, ""),
    DATA_ENCRYPTION_KEY=(str, ""),
    SECURITY_SSL_REDIRECT=(bool, False),
    SECURITY_SESSION_COOKIE_SECURE=(bool, False),
    SECURITY_CSRF_COOKIE_SECURE=(bool, False),
    SECURITY_HSTS_SECONDS=(int, 0),
    SECURITY_HSTS_INCLUDE_SUBDOMAINS=(bool, True),
    SECURITY_HSTS_PRELOAD=(bool, False),
    INTEGRATION_STATUS_CACHE_TTL=(int, 60),
    CELERY_BROKER_URL=(str, "redis://redis:6379/0"),
    CELERY_RESULT_BACKEND=(str, "redis://redis:6379/1"),
    CELERY_TASK_ALWAYS_EAGER=(bool, False),
    CELERY_REFRESH_INTEGRATION_STATUS_INTERVAL_SECONDS=(int, 120),
    CELERY_SYNC_DAILY_STATS_INTERVAL_SECONDS=(int, 15 * 60),
    CELERY_CLEANUP_TECHNICAL_LOGS_INTERVAL_SECONDS=(int, 24 * 60 * 60),
    DAILY_STATS_SYNC_WINDOW_DAYS=(int, 120),
    WEBHOOK_EVENT_RETENTION_DAYS=(int, 90),
    WEBHOOK_OPERATION_LOG_RETENTION_DAYS=(int, 90),
    LOG_LEVEL=(str, "INFO"),
    DJANGO_LOG_LEVEL=(str, "INFO"),
    LOG_TO_FILES=(bool, False),
    LOG_DIR=(str, "logs"),
    LOG_ROTATION_MAX_BYTES=(int, 10 * 1024 * 1024),
    LOG_ROTATION_BACKUP_COUNT=(int, 10),
)

environ.Env.read_env(BASE_DIR / ".env")

MAXBOT_ENV = (env("MAXBOT_ENV").strip() or env("APP_ENV").strip() or "development").lower()
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

# Dev convenience: disable host restrictions for local/ngrok debugging only.
if DEBUG and MAXBOT_ENV != "production":
    ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core",
    "apps.accounts",
    "apps.bot",
    "apps.max_integration",
    "apps.menu_builder",
    "apps.webhooks",
    "apps.analytics",
    "apps.dashboard",
    "apps.audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.core.logging.RequestIDMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.global_status",
            ]
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {"default": env.db()}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

try:
    import whitenoise  # noqa: F401

    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
except Exception:  # noqa: BLE001
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "accounts:login"

MAX_API_BASE_URL = env("MAX_API_BASE_URL")
MAX_API_TIMEOUT = env("MAX_API_TIMEOUT")
BASE_URL = env("BASE_URL").strip()
WEBHOOK_URL = env("WEBHOOK_URL").strip()
PUBLIC_BASE_URL = (env("PUBLIC_BASE_URL").strip() or BASE_URL).rstrip("/")
if not PUBLIC_BASE_URL and WEBHOOK_URL:
    parsed_webhook_url = urlparse(WEBHOOK_URL)
    if parsed_webhook_url.scheme and parsed_webhook_url.netloc:
        PUBLIC_BASE_URL = f"{parsed_webhook_url.scheme}://{parsed_webhook_url.netloc}"
DATA_ENCRYPTION_KEY = env("DATA_ENCRYPTION_KEY").strip()
INTEGRATION_STATUS_CACHE_TTL = env("INTEGRATION_STATUS_CACHE_TTL")
DAILY_STATS_SYNC_WINDOW_DAYS = env("DAILY_STATS_SYNC_WINDOW_DAYS")
WEBHOOK_EVENT_RETENTION_DAYS = env("WEBHOOK_EVENT_RETENTION_DAYS")
WEBHOOK_OPERATION_LOG_RETENTION_DAYS = env("WEBHOOK_OPERATION_LOG_RETENTION_DAYS")
LOG_LEVEL = env("LOG_LEVEL")
DJANGO_LOG_LEVEL = env("DJANGO_LOG_LEVEL")
LOG_TO_FILES = env("LOG_TO_FILES")
LOG_DIR = env("LOG_DIR")
LOG_ROTATION_MAX_BYTES = env("LOG_ROTATION_MAX_BYTES")
LOG_ROTATION_BACKUP_COUNT = env("LOG_ROTATION_BACKUP_COUNT")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "default-cache",
    },
    "integration_status": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "integration-status-dev",
        "TIMEOUT": INTEGRATION_STATUS_CACHE_TTL,
    },
}

if MAXBOT_ENV == "production":
    CACHES["integration_status"] = {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "integration_status_cache",
        "TIMEOUT": INTEGRATION_STATUS_CACHE_TTL,
    }

CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND")
CELERY_TASK_ALWAYS_EAGER = env("CELERY_TASK_ALWAYS_EAGER")
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_TIME_LIMIT = 60
CELERY_TASK_SOFT_TIME_LIMIT = 45
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "refresh-integration-status": {
        "task": "apps.core.tasks.refresh_integration_status_task",
        "schedule": env("CELERY_REFRESH_INTEGRATION_STATUS_INTERVAL_SECONDS"),
    },
    "sync-daily-stats": {
        "task": "apps.analytics.tasks.sync_daily_stats_task",
        "schedule": env("CELERY_SYNC_DAILY_STATS_INTERVAL_SECONDS"),
    },
    "cleanup-technical-logs": {
        "task": "apps.bot.tasks.cleanup_technical_logs_task",
        "schedule": env("CELERY_CLEANUP_TECHNICAL_LOGS_INTERVAL_SECONDS"),
    },
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = env("SECURITY_SSL_REDIRECT", 0)
SESSION_COOKIE_SECURE = env("SECURITY_SESSION_COOKIE_SECURE", 0)
CSRF_COOKIE_SECURE = env("SECURITY_CSRF_COOKIE_SECURE", 0)
SECURE_HSTS_SECONDS = env("SECURITY_HSTS_SECONDS")
SECURE_HSTS_INCLUDE_SUBDOMAINS = env("SECURITY_HSTS_INCLUDE_SUBDOMAINS", 0)
SECURE_HSTS_PRELOAD = env("SECURITY_HSTS_PRELOAD", 0)

if MAXBOT_ENV == "production":
    if DEBUG:
        raise ImproperlyConfigured("DEBUG must be False in production")
    if not SECRET_KEY.strip() or SECRET_KEY == "change-me":
        raise ImproperlyConfigured("SECRET_KEY must be set in production")
    if not ALLOWED_HOSTS:
        raise ImproperlyConfigured("ALLOWED_HOSTS must be set in production")
    if not PUBLIC_BASE_URL:
        raise ImproperlyConfigured("PUBLIC_BASE_URL must be set in production")
    if not DATA_ENCRYPTION_KEY:
        raise ImproperlyConfigured("DATA_ENCRYPTION_KEY must be set in production")
    if not SECURE_SSL_REDIRECT:
        raise ImproperlyConfigured("SECURITY_SSL_REDIRECT must be true in production")
    if not SESSION_COOKIE_SECURE:
        raise ImproperlyConfigured("SECURITY_SESSION_COOKIE_SECURE must be true in production")
    if not CSRF_COOKIE_SECURE:
        raise ImproperlyConfigured("SECURITY_CSRF_COOKIE_SECURE must be true in production")
    if SECURE_HSTS_SECONDS <= 0:
        raise ImproperlyConfigured("SECURITY_HSTS_SECONDS must be greater than 0 in production")

_log_dir_path = Path(LOG_DIR)
if LOG_TO_FILES:
    _log_dir_path.mkdir(parents=True, exist_ok=True)

_handlers: dict[str, dict[str, object]] = {
    "console": {
        "class": "logging.StreamHandler",
        "filters": ["request_id"],
        "formatter": "structured",
    }
}

if LOG_TO_FILES:
    _handlers.update(
        {
            "app_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(_log_dir_path / "app.log"),
                "maxBytes": LOG_ROTATION_MAX_BYTES,
                "backupCount": LOG_ROTATION_BACKUP_COUNT,
                "encoding": "utf-8",
                "filters": ["request_id"],
                "formatter": "structured",
            },
            "webhooks_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(_log_dir_path / "webhooks.log"),
                "maxBytes": LOG_ROTATION_MAX_BYTES,
                "backupCount": LOG_ROTATION_BACKUP_COUNT,
                "encoding": "utf-8",
                "filters": ["request_id"],
                "formatter": "structured",
            },
            "integration_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(_log_dir_path / "integration.log"),
                "maxBytes": LOG_ROTATION_MAX_BYTES,
                "backupCount": LOG_ROTATION_BACKUP_COUNT,
                "encoding": "utf-8",
                "filters": ["request_id"],
                "formatter": "structured",
            },
            "errors_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(_log_dir_path / "errors.log"),
                "maxBytes": LOG_ROTATION_MAX_BYTES,
                "backupCount": LOG_ROTATION_BACKUP_COUNT,
                "encoding": "utf-8",
                "filters": ["request_id"],
                "formatter": "structured",
                "level": "WARNING",
            },
        }
    )

_app_handlers = ["console"] + (["app_file"] if LOG_TO_FILES else [])
_webhooks_handlers = ["console"] + (["webhooks_file"] if LOG_TO_FILES else [])
_integration_handlers = ["console"] + (["integration_file"] if LOG_TO_FILES else [])
_error_handlers = ["console"] + (["errors_file"] if LOG_TO_FILES else [])

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {"()": "apps.core.logging.RequestIDFilter"},
    },
    "formatters": {
        "structured": {
            "format": (
                "ts=%(asctime)s level=%(levelname)s logger=%(name)s "
                "request_id=%(request_id)s msg=%(message)s"
            )
        }
    },
    "handlers": _handlers,
    "loggers": {
        "": {"handlers": ["console"], "level": LOG_LEVEL},
        "django": {"handlers": _error_handlers, "level": DJANGO_LOG_LEVEL, "propagate": False},
        "apps": {"handlers": _app_handlers, "level": LOG_LEVEL, "propagate": False},
        "apps.webhooks": {"handlers": _webhooks_handlers, "level": LOG_LEVEL, "propagate": False},
        "apps.max_integration": {
            "handlers": _integration_handlers,
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "django.security": {"handlers": _error_handlers, "level": "WARNING", "propagate": False},
        "django.request": {"handlers": _error_handlers, "level": "ERROR", "propagate": False},
        "errors": {"handlers": _error_handlers, "level": "WARNING", "propagate": False},
    },
}
