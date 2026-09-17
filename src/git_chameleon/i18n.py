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
            "<b>Hello! I'm git-chameleon.</b>\n\n"
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
        "menu.title": "<b>git-chameleon control panel</b>",
        "menu.not_linked": (
            "Not linked. Press Linking or send /link <github-username>."
        ),
        "menu.no_installation": (
            "GitHub: @{login} (no installation yet, press Linking)."
        ),
        "menu.linked": "GitHub: @{login}\nInstallation: #{installation_id}",
        "status.not_linked": (
            "Not linked. Press Linking or send /link <github-username>."
        ),
        "status.no_installation": (
            "GitHub: @{login}\nNo installation matched yet. Press Linking."
        ),
        "status.linked": "GitHub: @{login}\nInstallation: #{installation_id}",
        "btn.link": "Linking",
        "btn.settings": "Settings",
        "btn.repos": "Repositories",
        "btn.llm": "LLM",
        "btn.unlink": "Unlink",
        "btn.unlink_confirm": "Yes, unlink",
        "btn.cancel": "Cancel",
        "btn.back": "Back to menu",
        "btn.back_settings": "Back to settings",
        "settings.text": (
            "<b>Settings</b>\n\n"
            "Pick the repositories to receive news about, or unlink your account."
        ),
        "llm.text_configured": (
            "<b>LLM</b>\n\nProvider: {model}\nEnable the features you need:"
        ),
        "llm.text_unconfigured": (
            "<b>LLM</b>\n\nThe provider is not configured on the server "
            "(.env: LLM_BASE_URL, LLM_API_KEY, LLM_MODEL).\n"
            "You can flip the toggles now \u2014 they will work once the "
            "provider is set up."
        ),
        "btn.llm_chat": "Chat",
        "btn.llm_review": "Review",
        "llm.chat_disabled": (
            "Chat is disabled. Enable it in Settings \u2192 LLM."
        ),
        "llm.chat_error": "Failed to get an answer from the neural network.",
        "llm.empty": (
            "The LLM section is empty for now.\n"
            "Neural network setup will appear here later."
        ),
        "llm.not_configured": (
            "The neural network is not configured yet, so I can't reply to "
            "plain messages. See Settings \u2192 LLM."
        ),
        "repos.title": "<b>Repositories</b>",
        "repos.count": "Total: {total}",
        "repos.selected": "Selected: {selected}",
        "repos.page_info": "Page {page} of {pages}",
        "repos.page_label": "{page}/{pages}",
        "repos.hint": (
            "Tick the repositories you want news for.\n"
            "Until you select at least one, no news is sent."
        ),
        "repos.none": (
            "No repositories available yet.\n"
            "Install the app on some repositories and come back."
        ),
        "repos.not_linked": "Link your account first — press Linking.",
        "repos.prev": "\u25c0",
        "repos.next": "\u25b6",
        "install.text": (
            "Open this link and press the Install button:\n\n{url}\n\n"
            "Afterwards send /link <your-github-username>"
        ),
        "link.usage": "Usage: /link <github-username>",
        "link.no_installation": (
            "No installation for @{login} yet. Open /install to add it, then /sync."
        ),
        "link.linked": "Linked @{login} (installation #{installation_id}).",
        "link.notify_repos": (
            "One step left: pick repositories for your news in "
            "Settings \u2192 Repositories."
        ),
        "sync.not_linked": "Run /link <your-github-username> first.",
        "sync.no_installation": "No installation for @{login} yet. Open /install to add it.",
        "sync.linked_digest": "Linked to installation #{installation_id}.\n\n{digest}",
        "sync.linked_no_prs": "Linked to installation #{installation_id}. No open PRs.",
        "sync.no_repos": (
            "Linked to installation #{installation_id}.\n\n"
            "No repositories selected yet \u2014 pick them in "
            "Settings \u2192 Repositories to receive news."
        ),
        "unlink.done": "Unlinked.",
        "unlink.confirm": "Unlink GitHub account @{login}?",
        "unlink.nothing": "Nothing to unlink.",
        "digest.title": "<b>Open PRs!</b>",
        "digest.mention": "{mention}, you have open PRs:",
        "digest.no_llm": "LLM is not configured \u2014 no summaries will be generated.",
        "digest.draft": "[draft]",
    },
    "ru": {
        "start.greeting": (
            "<b>Привет! Я git-chameleon.</b>\n\n"
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
        "menu.title": "<b>Панель управления git-chameleon</b>",
        "menu.not_linked": (
            "Аккаунт не привязан. Нажми «Привязка» или отправь /link <имя-пользователя>."
        ),
        "menu.no_installation": (
            "GitHub: @{login} (установка ещё не найдена, нажми «Привязка»)."
        ),
        "menu.linked": "GitHub: @{login}\nУстановка: #{installation_id}",
        "status.not_linked": (
            "Аккаунт не привязан. Нажми «Привязка» или отправь /link <имя-пользователя>."
        ),
        "status.no_installation": (
            "GitHub: @{login}\nУстановка ещё не найдена. Нажми «Привязка»."
        ),
        "status.linked": "GitHub: @{login}\nУстановка: #{installation_id}",
        "btn.link": "Привязка",
        "btn.settings": "Настройки",
        "btn.repos": "Репозитории",
        "btn.llm": "LLM",
        "btn.unlink": "Отвязать",
        "btn.unlink_confirm": "Да, отвязать",
        "btn.cancel": "Отмена",
        "btn.back": "В меню",
        "btn.back_settings": "К настройкам",
        "settings.text": (
            "<b>Настройки</b>\n\n"
            "Выбери репозитории, по которым присылать новости, или отвяжи аккаунт."
        ),
        "llm.text_configured": (
            "<b>LLM</b>\n\nПровайдер: {model}\nВключи нужные функции:"
        ),
        "llm.text_unconfigured": (
            "<b>LLM</b>\n\nПровайдер не настроен на сервере "
            "(.env: LLM_BASE_URL, LLM_API_KEY, LLM_MODEL).\n"
            "Переключатели можно включить заранее — заработают после "
            "настройки провайдера."
        ),
        "btn.llm_chat": "Чат",
        "btn.llm_review": "Ревью",
        "llm.chat_disabled": (
            "Чат выключен. Включи его в Настройки \u2192 LLM."
        ),
        "llm.chat_error": "Не удалось получить ответ от нейросети.",
        "llm.empty": (
            "Раздел LLM пока пуст.\n"
            "Настройка нейросети появится здесь позже."
        ),
        "llm.not_configured": (
            "Нейросеть ещё не настроена, поэтому я не могу отвечать на обычные "
            "сообщения. Настройки \u2192 LLM."
        ),
        "repos.title": "<b>Репозитории</b>",
        "repos.count": "Всего: {total}",
        "repos.selected": "Выбрано: {selected}",
        "repos.page_info": "Страница {page} из {pages}",
        "repos.page_label": "{page}/{pages}",
        "repos.hint": (
            "Отметь галочкой репозитории, по которым присылать новости.\n"
            "Пока не выбран ни один — новости приходить не будут."
        ),
        "repos.none": (
            "Доступных репозиториев пока нет.\n"
            "Установи приложение на нужные репозитории и вернись."
        ),
        "repos.not_linked": "Сначала привяжи аккаунт — кнопка «Привязка».",
        "repos.prev": "\u25c0",
        "repos.next": "\u25b6",
        "install.text": (
            "Открой ссылку и нажми кнопку Install:\n\n{url}\n\n"
            "Затем отправь /link <имя-пользователя-github>"
        ),
        "link.usage": "Использование: /link <имя-пользователя-github>",
        "link.no_installation": (
            "Установка для @{login} ещё не найдена. Открой /install, затем /sync."
        ),
        "link.linked": "Привязано: @{login} (установка #{installation_id}).",
        "link.notify_repos": (
            "Остался последний шаг: выбери репозитории для новостей в "
            "«Настройки \u2192 Репозитории»."
        ),
        "sync.not_linked": "Сначала отправь /link <имя-пользователя-github>.",
        "sync.no_installation": "Установка для @{login} ещё не найдена. Открой /install.",
        "sync.linked_digest": "Привязано к установке #{installation_id}.\n\n{digest}",
        "sync.linked_no_prs": "Привязано к установке #{installation_id}. Открытых PR нет.",
        "sync.no_repos": (
            "Привязано к установке #{installation_id}.\n\n"
            "Репозитории не выбраны — выбери их в «Настройки \u2192 Репозитории», "
            "чтобы получать новости."
        ),
        "unlink.done": "Отвязано.",
        "unlink.confirm": "Отвязать аккаунт GitHub @{login}?",
        "unlink.nothing": "Нечего отвязывать.",
        "digest.title": "<b>Открытые PR!</b>",
        "digest.mention": "{mention}, у тебя есть открытые PR:",
        "digest.no_llm": "LLM не настроен — саммари не будет.",
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
