# admMaxBot

`admMaxBot` — Django-монолит для управления ботом MAX через русскоязычную web-панель.

Проект включает:
- конструктор меню и предпросмотр кнопок;
- webhook-интеграцию с проверкой секрета и обработкой событий;
- панель аналитики и служебные журналы;
- управление настройками бота и webhook-подписками.

## Стек

- Python
- Django
- SQLite для локальной разработки
- Postgres для Docker-окружения
- pytest для unit и integration тестов

## Структура приложений

- `apps/accounts` — пользователи и доступы
- `apps/analytics` — аналитика и агрегаты
- `apps/audit` — аудит действий
- `apps/bot` — модели и доменная логика бота
- `apps/core` — общие сервисы, контекст и утилиты
- `apps/dashboard` — главная панель
- `apps/max_integration` — работа с внешним API MAX
- `apps/menu_builder` — конструктор меню
- `apps/webhooks` — webhook endpoint и обработка событий

## Локальный запуск

1. Создать и активировать виртуальное окружение.
2. Установить зависимости проекта.
3. Применить миграции:

```powershell
.\.venv\Scripts\python manage.py migrate
```

4. Запустить сервер:

```powershell
.\.venv\Scripts\python manage.py runserver
```

## Проверки

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python manage.py check
```

## Docker

Для контейнерного запуска в репозитории есть:
- `Dockerfile`
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `docker/entrypoint.sh`

## Назначение проекта

Проект помогает администрировать бот, собирать меню без ручного редактирования кода, отслеживать webhook-состояние и поддерживать интеграцию с платформой MAX в одном интерфейсе.
