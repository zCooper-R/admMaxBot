# CODEx_SETUP_GUIDE.md

## 1. Зачем нужна папка `Example/`
`Example/` — это эталонная библиотека универсальных шаблонов для Django-проектов.
Она нужна, чтобы:
- быстро поднимать одинаково качественную агентную инфраструктуру в новых репозиториях;
- хранить базовые, переносимые инструкции отдельно от проектной адаптации;
- исключить дрейф шаблонов при работе в конкретном проекте.

## 2. Что в `Example/` универсальное и переносимое
Универсальные файлы:
- `Example/AGENTS.md`
- `Example/PLANS.md`
- `Example/.codex/config.toml`
- `Example/.codex/agents/architect.toml`
- `Example/.codex/agents/reviewer.toml`
- `Example/.codex/agents/backend_implementer.toml`
- `Example/.codex/agents/ui_admin_panel.toml`
- `Example/.codex/agents/docker_devops.toml`
- `Example/.codex/agents/security_auditor.toml`
- `Example/.codex/agents/test_engineer.toml`
- `Example/.codex/skills/django-change/SKILL.md`
- `Example/.codex/skills/review-playbook/SKILL.md`
- `Example/.codex/skills/release-readiness/SKILL.md`
- `Example/README.md`

Эти файлы не завязаны на конкретный домен или имена сервисов текущего репозитория.

## 3. Что нельзя редактировать внутри `Example/`
В рамках адаптации проекта нельзя изменять содержимое файлов `Example/`.
Правильный подход:
- оставить `Example/` как baseline;
- работать только с проектными копиями вне `Example/`.

## 4. Какие файлы являются рабочими проектными копиями
Рабочие файлы текущего репозитория:
- `AGENTS.md`
- `PLANS.md`
- `.codex/config.toml`
- `.codex/agents/*.toml`
- `.codex/skills/*/SKILL.md`

Именно эти файлы редактируются по мере развития проекта.

## 5. Какие файлы использовать в текущем проекте
Для ежедневной работы Codex/Cursor использовать:
1. `AGENTS.md` — репозиторные правила и Definition of Done.
2. `.codex/config.toml` — параметры выполнения и приоритеты фокуса.
3. `.codex/agents/*.toml` — роль-специфичные профили.
4. `.codex/skills/*/SKILL.md` — процедурные playbook-ы под задачи.
5. `PLANS.md` — шаблон структурирования больших задач.

## 6. Что копировать в другой Django-проект
Копировать нужно только `Example/` (целиком), затем создавать новые рабочие копии под новый проект.

## 7. Последовательность переноса в другой проект
1. Скопировать `Example/AGENTS.md` в `AGENTS.md`.
2. Скопировать `Example/.codex/config.toml` в `.codex/config.toml`.
3. Скопировать `Example/.codex/agents/*.toml` в `.codex/agents/`.
4. Скопировать `Example/.codex/skills/*` в `.codex/skills/`.
5. Скопировать `Example/PLANS.md` в `PLANS.md`.

После копирования выполнить проектную адаптацию только в копиях.

## 8. Как адаптировать проектные копии под конкретный проект
Рекомендуемый порядок:
1. Проанализировать структуру репозитория (apps/services/templates/tests/infra).
2. Обновить `AGENTS.md` под реальные контуры проекта.
3. Настроить `.codex/config.toml` под локальные правила среды и CI.
4. Уточнить роли `.codex/agents/*.toml` под фактические рисковые зоны.
5. Дополнить skills конкретными чек-листами проекта.
6. Зафиксировать шаблон планирования в `PLANS.md`.

## 9. Для чего использовать каждого агента
- `architect`: границы изменений, архитектурные решения, снижение риска.
- `reviewer`: ревью correctness/security/regressions/performance/tests.
- `backend_implementer`: реализация backend задач в Django.
- `ui_admin_panel`: templates, UX админ-панели, формы и таблицы.
- `docker_devops`: Docker/compose/env/healthchecks/startup flow.
- `security_auditor`: auth/permissions/csrf/webhook trust/secrets.
- `test_engineer`: регрессионные, интеграционные и критичные тест-сценарии.

## 10. Примеры запросов к Codex/Cursor
### Большое ревью
"Проведи полное ревью репозитория по skill review-playbook: найди P0/P1/P2, архитектурные и инфраструктурные риски, и дай пошаговый fix plan."

### Фикс бага
"Исправь баг с выходом из аккаунта, добавь регрессионный тест и проверь через .venv."

### UI-задача
"Улучши форму редактирования узла меню: сохрани текущие JS hooks, улучши отображение ошибок и адаптивность."

### Docker/prod-задача
"Проверь docker-compose.prod.yml и entrypoint на release readiness: startup flow, healthchecks, env safety, writable dirs."

### Security review
"Проведи security-аудит webhook endpoint: секрет, idempotency, обработка невалидных payload и утечки в логах."

### Release readiness check
"Выполни release readiness по соответствующему skill и дай статус READY / READY WITH CONDITIONS / NOT READY с блокерами."

## Карта текущей реализации в этом репозитории
- `Example/` — неизменяемая эталонная база.
- Корневые и `.codex/` файлы — рабочий, адаптированный под MaxBotV3 слой.
- Адаптация уже учитывает:
  - монолит с набором Django apps;
  - webhook + integration контур;
  - docker-compose dev/prod;
  - локальный SQLite и Docker Postgres;
  - русскоязычный интерфейс и шаблоны панели;
  - существующую тестовую структуру.
