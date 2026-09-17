# 🦎 Git Chameleon

Telegram-бот: следит за открытыми PR в твоих репозиториях на GitHub, умеет ревью через LLM и чат (в личке и группах). А так же общается как сельский житель!

> Прежде чем перейдем к настройке: этот бот был создан за 4 часа просто так ради совместной разработки другого проекта. Данный код можете использовать в любых целях.

## **Задеплоенный TG инстанс:** [@git_ch_bot](https://t.me/git_ch_bot)

## Настройка

### 1. GitHub App (для авторизации)

1. GitHub → Settings → Developer settings → GitHub Apps → **New GitHub App**
2. Webhook → **Disable**
3. Permissions: **Pull requests — Read-only**, **Repository metadata — Read-only**
4. Скачай private key (`.pem`), запомни Client ID

### 2. Бот в Telegram

1. [@BotFather](https://t.me/BotFather) → `/newbot` → токен
2. `/setprivacy` → **Disable** (см. тонкости ниже)

### 3. Запуск

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env  # заполни
python -m git_chameleon
```

`.env`:

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | токен из BotFather |
| `GITHUB_APP_CLIENT_ID` | Client ID приложения |
| `GITHUB_APP_PRIVATE_KEY_PATH` | путь к `.pem` |
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | любой OpenAI-совместимый API (необязательно) |
| `DATABASE_PATH` | SQLite-файл, по умолчанию `data/bot.db` |

## Первый запуск в Telegram

1. `/start` → кнопка **Привязка** → установи приложение на репозитории
2. `/link <github-логин>`
3. Настройки → Репозитории → отметь, по каким слать новости (без выбора новостей нет)

## Тонкости

- **Privacy mode.** Даже после `/setprivacy` → Disable в BotFather Telegram продолжает фильтровать сообщения, пока бота не **убрать и добавить в группу заново** (или сделать его админом). Иначе бот не видит сообщения в группе.
- **Группы.** Бот отвечает на `@git_ch_bot` и слова «юз», «хамелеон», «chameleon». Группа и участники запоминаются после первого сообщения в ней.
- **Дайджесты без спама.** Уведомление приходит один раз на новый PR; повторно — только по новым.
- **LLM.** Reasoning-модели (deepseek и т.п.) сжигают `max_tokens` на рассуждения — лимиты уже выставлены большими. Ревью пишется строго по реальным файлам и патчам PR, без выдумок.
- **Язык.** Автоматически по языку Telegram-клиента (ru / en).
- **HTML.** Все сообщения парсятся как HTML: `<...>` в текстах экранирован как `&lt;...&gt;`.
- **Тесты:** `pytest`, линтер: `ruff check src tests`, типы: `mypy src`.

## Деплой (systemd)

```ini
# /etc/systemd/system/git-chameleon.service
[Service]
WorkingDirectory=/opt/git-chameleon
EnvironmentFile=/etc/git-chameleon/.env
ExecStart=/opt/git-chameleon/.venv/bin/python -m git_chameleon
```

`systemctl enable --now git-chameleon`, логи: `journalctl -u git-chameleon -f`.
