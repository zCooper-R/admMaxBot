# Памятка: как работать с Git между домом и работой

Эта памятка рассчитана на обычный повседневный режим:

- дома что-то поменял;
- запушил в GitHub;
- пришёл на работу, подтянул изменения;
- всё запустил;
- доработал;
- снова запушил;
- дома продолжил с последнего состояния.

## Главная идея

GitHub в этом процессе — центральная точка обмена.

Схема очень простая:

1. На одном компьютере сделал изменения.
2. Закоммитил.
3. Запушил в GitHub.
4. На другом компьютере сделал `git pull`.
5. Продолжил работу.

Если коротко:

- `commit` — сохранить логический кусок работы у себя;
- `push` — отправить его в GitHub;
- `pull` — забрать из GitHub к себе.

## Базовое правило

Перед началом работы на любом компьютере всегда делай:

```powershell
git checkout main
git pull
```

Это главное правило, которое спасает от большинства проблем.

## Рекомендуемый рабочий цикл

### 1. Начинаешь новую задачу

На любом компьютере:

```powershell
git checkout main
git pull
git checkout -b fix-short-description
```

Примеры названий веток:

- `fix-webhook-errors`
- `menu-ui-improvements`
- `bot-settings-validation`

## 2. Работаешь и периодически сохраняешься

Посмотреть, что изменилось:

```powershell
git status
```

Сохранить изменения:

```powershell
git add .
git commit -m "Fix webhook UI"
```

Если хочешь отправить изменения в GitHub, чтобы потом продолжить на другом компьютере:

```powershell
git push -u origin fix-webhook-errors
```

После первого пуша обычно достаточно:

```powershell
git push
```

## 3. Пришёл на другой компьютер

Если ветка уже существует в GitHub и ты хочешь продолжить именно её:

```powershell
git fetch --all
git checkout fix-webhook-errors
git pull
```

Если локально такой ветки ещё нет:

```powershell
git fetch --all
git checkout -b fix-webhook-errors origin/fix-webhook-errors
```

## 4. Поднять проект после `pull`

Обычно после подтягивания изменений достаточно:

```powershell
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py check
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python manage.py runserver
```

Если миграций не было, `migrate` просто быстро отработает и ничего страшного не сделает.

## 5. Закончил задачу

Когда работа по ветке готова:

1. Пушишь ветку.
2. Делаешь PR в `main`.
3. После merge обновляешь `main` у себя:

```powershell
git checkout main
git pull
```

4. Старую ветку можно удалить:

```powershell
git branch -d fix-webhook-errors
git push origin --delete fix-webhook-errors
```

## Самый частый сценарий: дом → работа → дом

### Дома

```powershell
git checkout main
git pull
git checkout -b menu-ui-improvements
```

Поработал:

```powershell
git add .
git commit -m "Improve menu UI"
git push -u origin menu-ui-improvements
```

### На работе

```powershell
git fetch --all
git checkout menu-ui-improvements
git pull
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py runserver
```

Поработал ещё:

```powershell
git add .
git commit -m "Continue menu UI improvements"
git push
```

### Снова дома

```powershell
git fetch --all
git checkout menu-ui-improvements
git pull
```

И продолжаешь.

## Если забыл, в какой ветке находишься

```powershell
git branch
```

Текущая ветка будет отмечена звёздочкой.

## Если забыл, есть ли несохранённые изменения

```powershell
git status
```

Если там чисто, увидишь что рабочее дерево чистое.

## Если нужно просто обновить main

```powershell
git checkout main
git pull
```

## Если случайно начал править не в той ветке

Если изменения ещё не коммитил, лучше остановиться и посмотреть `git status`.

Самый безопасный путь:

1. Не делать `reset --hard`.
2. Не удалять ничего руками.
3. Либо закоммитить как временный черновик в текущую ветку, либо перенести изменения аккуратно отдельно.

Если такое случится, лучше сначала посмотреть:

```powershell
git status
git branch
```

И уже потом решать.

## Что делать нельзя без уверенности

Не используй это без необходимости:

- `git reset --hard`
- `git push --force`
- удаление веток, если не уверен, что всё уже влито
- перестановку тегов релиза без понимания последствий

## Как понимать, что у тебя уже всё хорошо

Минимально нормальное состояние перед пушем:

```powershell
.\.venv\Scripts\python manage.py check
.\.venv\Scripts\python -m pytest -q
git status
```

Если:

- проверки зелёные;
- `git status` показывает только нужные файлы;
- ты понимаешь, в какой ветке находишься,

значит всё идёт нормально.

## Как у нас сейчас устроено CI/CD

В проекте уже есть:

- `CI`: проверяет Django и тесты;
- `Lint`: проверяет изменённые Python-файлы в PR;
- `Release`: срабатывает по тегу вида `vX.Y.Z`.

Практически это значит:

- обычную работу делаешь через ветки и PR;
- релиз делаешь тегом после merge в `main`.

## Релизы простыми словами

Когда готова новая версия:

1. В `pyproject.toml` обновляется версия.
2. В `CHANGELOG.md` записывается, что вошло в релиз.
3. Всё мержится в `main`.
4. На `main` ставится тег:

```powershell
git checkout main
git pull
git tag -a v0.2.1 -m "Release v0.2.1"
git push origin v0.2.1
```

После этого GitHub Actions запускает release-процесс.

## Самая короткая памятка

Если запомнить только 5 команд, то вот они:

```powershell
git checkout main
git pull
git checkout -b my-task
git add .
git commit -m "My task"
git push -u origin my-task
```

На другом компьютере:

```powershell
git fetch --all
git checkout my-task
git pull
```
