from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Chat, TelegramObject, User

from git_chameleon.storage import Storage

DEFAULT_LOCALE = "en"

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "start.greeting": (
            "Hello! I'm git-chameleon.\n\n"
            "I watch your GitHub repositories and report open pull requests.\n"
            "Use the buttons below or /help to see the commands."
        ),
        "help.text": (
            "I connect Telegram to your GitHub repositories.\n\n"
            "Commands:\n"
            "/menu - open the control panel\n"
            "/install - link to install the GitHub App\n"
            "/link <username> - bind your GitHub account\n"
            "/sync - refresh installations and report open PRs\n"
            "/status - show your current binding\n"
            "/unlink - remove the binding\n"
            "/help - show this help"
        ),
        "menu.title": "git-chameleon control panel",
        "menu.not_linked": (
            "Not linked. Press Install App or send /link <github-username>."
        ),
        "menu.no_installation": (
            "GitHub: @{login} (no installation yet, press Sync now)."
        ),
        "menu.linked": "GitHub: @{login}\nInstallation: #{installation_id}",
        "status.not_linked": (
            "Not linked. Press Install App or send /link <github-username>."
        ),
        "status.no_installation": (
            "GitHub: @{login}\nNo installation matched yet. Press Sync now."
        ),
        "status.linked": "GitHub: @{login}\nInstallation: #{installation_id}",
        "btn.status": "Status",
        "btn.sync": "Sync now",
        "btn.install": "Install App",
        "btn.unlink": "Unlink",
        "btn.unlink_confirm": "Yes, unlink",
        "btn.cancel": "Cancel",
        "btn.back": "Back to menu",
        "install.text": (
            "Open this link and press the Install button:\n\n{url}\n\n"
            "Afterwards send /link <your-github-username>"
        ),
        "link.usage": "Usage: /link <github-username>",
        "link.no_installation": (
            "No installation for @{login} yet. Open /install to add it, then /sync."
        ),
        "link.linked": "Linked @{login} (installation #{installation_id}).",
        "sync.not_linked": "Run /link <your-github-username> first.",
        "sync.no_installation": "No installation for @{login} yet. Open /install to add it.",
        "sync.linked_digest": "Linked to installation #{installation_id}.\n\n{digest}",
        "sync.linked_no_prs": "Linked to installation #{installation_id}. No open PRs.",
        "unlink.done": "Unlinked.",
        "unlink.confirm": "Unlink GitHub account @{login}?",
        "unlink.nothing": "Nothing to unlink.",
        "digest.title": "Open PRs:",
        "digest.draft": "[draft]",
    },
    "ru": {
        "start.greeting": (
            "Привет! Я git-chameleon.\n\n"
            "Я слежу за репозиториями на GitHub и сообщаю об открытых pull request'ах.\n"
            "Пользуйся кнопками ниже или командой /help."
        ),
        "help.text": (
            "Я связываю Telegram с твоими репозиториями на GitHub.\n\n"
            "Команды:\n"
            "/menu - открыть панель управления\n"
            "/install - ссылка на установку GitHub App\n"
            "/link <username> - привязать аккаунт GitHub\n"
            "/sync - обновить установки и показать открытые PR\n"
            "/status - показать текущую привязку\n"
            "/unlink - отвязать аккаунт\n"
            "/help - показать эту справку"
        ),
        "menu.title": "Панель управления git-chameleon",
        "menu.not_linked": (
            "Аккаунт не привязан. Нажми «Установить приложение» или отправь "
            "/link <имя-пользователя>."
        ),
        "menu.no_installation": (
            "GitHub: @{login} (установка ещё не найдена, нажми «Синхронизировать»)."
        ),
        "menu.linked": "GitHub: @{login}\nУстановка: #{installation_id}",
        "status.not_linked": (
            "Аккаунт не привязан. Нажми «Установить приложение» или отправь "
            "/link <имя-пользователя>."
        ),
        "status.no_installation": (
            "GitHub: @{login}\nУстановка ещё не найдена. Нажми «Синхронизировать»."
        ),
        "status.linked": "GitHub: @{login}\nУстановка: #{installation_id}",
        "btn.status": "Статус",
        "btn.sync": "Синхронизировать",
        "btn.install": "Установить приложение",
        "btn.unlink": "Отвязать",
        "btn.unlink_confirm": "Да, отвязать",
        "btn.cancel": "Отмена",
        "btn.back": "В меню",
        "install.text": (
            "Открой ссылку и нажми кнопку Install:\n\n{url}\n\n"
            "Затем отправь /link <имя-пользователя-github>"
        ),
        "link.usage": "Использование: /link <имя-пользователя-github>",
        "link.no_installation": (
            "Установка для @{login} ещё не найдена. Открой /install, затем /sync."
        ),
        "link.linked": "Привязано: @{login} (установка #{installation_id}).",
        "sync.not_linked": "Сначала отправь /link <имя-пользователя-github>.",
        "sync.no_installation": "Установка для @{login} ещё не найдена. Открой /install.",
        "sync.linked_digest": "Привязано к установке #{installation_id}.\n\n{digest}",
        "sync.linked_no_prs": "Привязано к установке #{installation_id}. Открытых PR нет.",
        "unlink.done": "Отвязано.",
        "unlink.confirm": "Отвязать аккаунт GitHub @{login}?",
        "unlink.nothing": "Нечего отвязывать.",
        "digest.title": "Открытые PR:",
        "digest.draft": "[черновик]",
    },
}


def normalize_locale(language_code: str | None) -> str:
    """Map a Telegram language_code ("ru-RU", "en") to a supported locale."""
    if not language_code:
        return DEFAULT_LOCALE
    base = language_code.replace("_", "-").split("-")[0].lower()
    return base if base in STRINGS else DEFAULT_LOCALE


class Strings:
    """Locale-aware lookup of user-facing texts."""

    def __init__(self, locale: str | None = None) -> None:
        self.locale = normalize_locale(locale)

    def get(self, key: str, **kwargs: object) -> str:
        text = STRINGS[self.locale].get(key) or STRINGS[DEFAULT_LOCALE].get(key) or key
        return text.format(**kwargs) if kwargs else text


class I18nMiddleware(BaseMiddleware):
    """Detect the user's Telegram locale and inject localized strings."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        chat: Chat | None = data.get("event_chat")
        storage: Storage | None = data.get("storage")

        locale = normalize_locale(user.language_code if user else None)
        if user is not None and chat is not None and isinstance(storage, Storage):
            storage.set_locale(user.id, chat.id, locale)

        data["strings"] = Strings(locale)
        return await handler(event, data)
