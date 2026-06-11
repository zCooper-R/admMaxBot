# Changelog

Все заметные изменения проекта фиксируются в этом файле.

Формат ориентирован на Keep a Changelog, а версионирование следует SemVer.

## [0.3.4] - 2026-06-11

### Added

- Расписание Celery переведено в `django-celery-beat`, чтобы периодические задачи были видны и редактируемы в Django admin.
- Добавлены ежедневный и еженедельный backup базы данных через Celery с автоочисткой старых дампов.
- Добавлена команда `sync_periodic_tasks` для синхронизации стандартных periodic tasks после миграций.

## [0.3.3] - 2026-06-11

### Fixed

- Docker healthcheck теперь отправляет production-домен в заголовке `Host`, чтобы проверка `/health/` не конфликтовала с `ALLOWED_HOSTS`.

## [0.3.2] - 2026-06-11

### Fixed

- Production Docker-образ теперь заранее создаёт `/app/staticfiles`, чтобы `collectstatic` мог писать в volume от non-root пользователя `app`.

## [0.3.1] - 2026-06-11

### Added

- Инструкция по проверке автоматического продления HTTPS-сертификатов через `certbot.timer`.
- Команды для `certbot renew --dry-run`, просмотра таймеров и проверки срока действия сертификата.

## [0.3.0] - 2026-06-11

### Added

- Production Docker Compose-профиль с Redis, Celery worker и Celery beat.
- Периодические задачи для обновления статуса интеграции MAX, синхронизации дневной аналитики и очистки технических логов.
- Универсальные example-файлы для переменных окружения, nginx и Docker override.
- Инструкция деплоя для HTTPS reverse proxy, миграций, health checks и мониторинга периодических задач.

### Changed

- Публичный webhook URL можно задавать явно через `WEBHOOK_URL`.
- Django-настройки proxy теперь доверяют `X-Forwarded-Proto: https` для production-развертывания за reverse proxy.
- Production-привязка web-порта настраивается через `WEB_APP_HOST` и `WEB_APP_PORT`.

## [0.2.0] - 2026-04-10

### Added

- GitHub Actions pipeline для CI с `manage.py check` и `pytest`.
- Release pipeline по тегам `vX.Y.Z` с публикацией Docker-образа в GHCR.
- Единые include-шаблоны для сайдбара и хлебных крошек.
- Явные правила версионирования и релизного процесса в `README.md`.

### Changed

- Хлебные крошки приведены к единому более выразительному стилю.
- Для всех `select` добавлено единообразное отображение стрелки, включая состояние фокуса.
- `.gitignore` больше не исключает `templates/logs` из Git по совпадению имени папки.
