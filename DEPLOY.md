# Деплой admMaxBot на Debian 13

Инструкция описывает production-развертывание на сервере `<server-private-ip>` с доменом `<domain>`.
ngrok в production не используется: публичный webhook задается переменной `WEBHOOK_URL`.

## Архитектура

- Внешний IP: `<public-ip>`.
- Домен: `<domain>`, при необходимости `www.<domain>`.
- OPNsense пробрасывает `WAN TCP 80` и `WAN TCP 443` на `<server-private-ip>`.
- На сервере работает nginx и проксирует HTTPS-запросы в Django-контейнер на `127.0.0.1:8000`.
- Web-панель и webhook endpoint обслуживаются одним Django-сервисом `web`.
- Периодические задачи выполняются через `celery_worker` и `celery_beat`, брокер — `redis`.
- Production webhook для MAX API: `https://<domain>/webhook`.
- Старый технический endpoint `/webhooks/max/` остается доступен для совместимости.

## Подготовка сервера

```bash
sudo apt update
sudo apt install -y git curl ca-certificates nginx certbot python3-certbot-nginx
```

Установите Docker Engine и Docker Compose plugin по официальной инструкции Docker для Debian.
После установки проверьте:

```bash
docker --version
docker compose version
```

## Получение проекта

```bash
git clone <repository>
cd <project>
cp .env.example .env
nano .env
```

В `.env` обязательно задайте реальные значения:

```env
SECRET_KEY=<strong-django-secret>
POSTGRES_PASSWORD=<strong-postgres-password>
MAX_BOT_TOKEN=<max-bot-token>
MAX_WEBHOOK_SECRET=<max-webhook-secret>
DATA_ENCRYPTION_KEY=<fernet-key>
```

Production URL должны остаться такими:

```env
APP_ENV=production
MAXBOT_ENV=production
DOMAIN=<domain>
BASE_URL=https://<domain>
PUBLIC_BASE_URL=https://<domain>
WEBHOOK_URL=https://<domain>/webhook
WEB_APP_HOST=127.0.0.1
WEB_APP_PORT=8000
ALLOWED_HOSTS=<domain>,www.<domain>
CSRF_TRUSTED_ORIGINS=https://<domain>,https://www.<domain>
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
CELERY_REFRESH_INTEGRATION_STATUS_INTERVAL_SECONDS=120
CELERY_SYNC_DAILY_STATS_INTERVAL_SECONDS=900
CELERY_CLEANUP_TECHNICAL_LOGS_INTERVAL_SECONDS=86400
DAILY_STATS_SYNC_WINDOW_DAYS=120
WEBHOOK_EVENT_RETENTION_DAYS=90
WEBHOOK_OPERATION_LOG_RETENTION_DAYS=90
```

## Запуск контейнеров

Сначала примените миграции:

```bash
docker compose --env-file .env -f docker-compose.prod.yml run --rm migrate
```

Затем запустите приложение:

```bash
docker compose --env-file .env -f docker-compose.prod.yml up -d --build
docker compose --env-file .env -f docker-compose.prod.yml ps
docker compose --env-file .env -f docker-compose.prod.yml logs -f
```

Сервисы `db`, `redis`, `web`, `celery_worker` и `celery_beat` имеют `restart: unless-stopped`, поэтому автоматически поднимаются после падения контейнера или перезагрузки сервера.

## Периодические задачи

В production включены две Celery-задачи:

- `apps.core.tasks.refresh_integration_status_task` — каждые `120` секунд обновляет кеш статуса интеграции с MAX API.
- `apps.analytics.tasks.sync_daily_stats_task` — каждые `900` секунд пересчитывает дневную аналитику за последние `120` дней.
- `apps.bot.tasks.cleanup_technical_logs_task` — раз в сутки удаляет старые webhook-события и журналы операций старше `90` дней.

Интервалы меняются через `.env`:

```env
CELERY_REFRESH_INTEGRATION_STATUS_INTERVAL_SECONDS=120
CELERY_SYNC_DAILY_STATS_INTERVAL_SECONDS=900
CELERY_CLEANUP_TECHNICAL_LOGS_INTERVAL_SECONDS=86400
DAILY_STATS_SYNC_WINDOW_DAYS=120
WEBHOOK_EVENT_RETENTION_DAYS=90
WEBHOOK_OPERATION_LOG_RETENTION_DAYS=90
```

Проверка логов периодики:

```bash
docker compose --env-file .env -f docker-compose.prod.yml logs -f celery_worker
docker compose --env-file .env -f docker-compose.prod.yml logs -f celery_beat
```

## Nginx и HTTPS

Скопируйте пример конфига:

```bash
sudo cp deploy/nginx/site.conf.example /etc/nginx/sites-available/<domain>.conf
sudo sed -i 's/example.com/<domain>/g' /etc/nginx/sites-available/<domain>.conf
sudo ln -s /etc/nginx/sites-available/<domain>.conf /etc/nginx/sites-enabled/<domain>.conf
sudo nginx -t
sudo systemctl reload nginx
```

Выпустите сертификат Let's Encrypt:

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
sudo certbot --nginx -d <domain> -d www.<domain>
```

После выпуска сертификата снова проверьте nginx:

```bash
sudo nginx -t
sudo systemctl status nginx
```

## OPNsense

Настройте NAT/Port Forward:

- `WAN TCP 80` -> `<server-private-ip>:80`
- `WAN TCP 443` -> `<server-private-ip>:443`

Проверьте, что DNS-записи `<domain>` и, если используется, `www.<domain>` указывают на `<public-ip>`.

## MAX API

В MAX API укажите webhook URL:

```text
https://<domain>/webhook
```

Секрет webhook должен совпадать со значением `MAX_WEBHOOK_SECRET` в `.env`.

## Проверки

```bash
curl -I http://127.0.0.1:8000
curl -I https://<domain>/
curl -I https://<domain>/webhook
sudo nginx -t
sudo systemctl status nginx
docker compose --env-file .env -f docker-compose.prod.yml ps
docker compose --env-file .env -f docker-compose.prod.yml logs -f
docker compose --env-file .env -f docker-compose.prod.yml logs -f celery_worker
docker compose --env-file .env -f docker-compose.prod.yml logs -f celery_beat
```

Ожидаемые признаки корректной настройки:

- `https://<domain>/` открывает web-панель.
- `https://<domain>/webhook` доступен через nginx и проксируется в Django.
- Внешние ссылки формируются от `https://<domain>`, без localhost, ngrok и http.
- Django получает `X-Forwarded-Proto: https` от nginx.
- В production не требуется `NGROK_URL`.
- `celery_worker`, `celery_beat` и `redis` находятся в статусе `running` или `healthy`.

## Локальный development с ngrok

Для локальной разработки можно оставить ngrok необязательным:

```env
APP_ENV=development
MAXBOT_ENV=development
DEBUG=True
NGROK_URL=https://example.ngrok-free.app
PUBLIC_BASE_URL=https://example.ngrok-free.app
WEBHOOK_URL=https://example.ngrok-free.app/webhook
```

Для production эти значения не используются.
