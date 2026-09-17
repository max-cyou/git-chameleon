from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from git_chameleon.i18n import Strings
from git_chameleon.storage import UserLink

REPOS_PER_PAGE = 5


class MenuCB(CallbackData, prefix="menu"):
    action: str


class RepoCB(CallbackData, prefix="repo"):
    action: str
    page: int
    repo_id: int = 0


def main_menu(strings: Strings) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=strings.get("btn.link"), callback_data=MenuCB(action="link"))
    builder.button(text=strings.get("btn.settings"), callback_data=MenuCB(action="settings"))
    builder.adjust(2)
    return builder.as_markup()


def settings_menu(strings: Strings) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=strings.get("btn.repos"), callback_data=MenuCB(action="repos"))
    builder.button(text=strings.get("btn.llm"), callback_data=MenuCB(action="llm"))
    builder.button(text=strings.get("btn.unlink"), callback_data=MenuCB(action="unlink"))
    builder.button(text=strings.get("btn.back"), callback_data=MenuCB(action="menu"))
    builder.adjust(2)
    return builder.as_markup()


def confirm_unlink(strings: Strings) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=strings.get("btn.unlink_confirm"), callback_data=MenuCB(action="unlink_confirm")
    )
    builder.button(text=strings.get("btn.cancel"), callback_data=MenuCB(action="settings"))
    builder.adjust(2)
    return builder.as_markup()


def back_to_menu(strings: Strings) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=strings.get("btn.back"), callback_data=MenuCB(action="menu"))
    return builder.as_markup()


def back_to_settings(strings: Strings) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=strings.get("btn.back_settings"), callback_data=MenuCB(action="settings")
    )
    return builder.as_markup()


def repos_keyboard(
    strings: Strings, rows: list[tuple[int, str, bool]], page: int, pages: int
) -> InlineKeyboardMarkup:
    """Repository picker: one toggle button per repo plus a pagination row."""
    keyboard: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=("✅ " if selected else "") + name,
                callback_data=RepoCB(
                    action="toggle", page=page, repo_id=repo_id
                ).pack(),
            )
        ]
        for repo_id, name, selected in rows
    ]
    keyboard.append(
        [
            InlineKeyboardButton(
                text=strings.get("repos.prev"),
                callback_data=RepoCB(
                    action="page", page=max(0, page - 1), repo_id=0
                ).pack(),
            ),
            InlineKeyboardButton(
                text=strings.get("repos.page_label", page=page + 1, pages=pages),
                callback_data=RepoCB(action="page", page=page, repo_id=0).pack(),
            ),
            InlineKeyboardButton(
                text=strings.get("repos.next"),
                callback_data=RepoCB(
                    action="page", page=min(pages - 1, page + 1), repo_id=0
                ).pack(),
            ),
        ]
    )
    keyboard.append(
        [
            InlineKeyboardButton(
                text=strings.get("btn.back_settings"),
                callback_data=MenuCB(action="settings").pack(),
            ),
            InlineKeyboardButton(
                text=strings.get("btn.back"),
                callback_data=MenuCB(action="menu").pack(),
            ),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def llm_menu(strings: Strings, link: UserLink | None, provider_configured: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=("✅ " if link and link.llm_chat else "") + strings.get("btn.llm_chat"),
        callback_data=MenuCB(action="llm_chat"),
    )
    builder.button(
        text=("✅ " if link and link.llm_review else "") + strings.get("btn.llm_review"),
        callback_data=MenuCB(action="llm_review"),
    )
    builder.button(
        text=strings.get("btn.back_settings"), callback_data=MenuCB(action="settings")
    )
    builder.button(text=strings.get("btn.back"), callback_data=MenuCB(action="menu"))
    builder.adjust(2)
    return builder.as_markup()


def llm_screen_text(
    strings: Strings, provider_configured: bool, model: str = ""
) -> str:
    if provider_configured:
        return strings.get("llm.text_configured", model=model)
    return strings.get("llm.text_unconfigured")


def menu_text(strings: Strings, link: UserLink | None) -> str:
    title = strings.get("menu.title")
    if link is None or not link.github_login:
        return title + "\n" + strings.get("menu.not_linked")
    if link.installation_id is None:
        return title + "\n" + strings.get("menu.no_installation", login=link.github_login)
    return title + "\n" + strings.get(
        "menu.linked", login=link.github_login, installation_id=link.installation_id
    )


def status_text(strings: Strings, link: UserLink | None) -> str:
    if link is None or not link.github_login:
        return strings.get("status.not_linked")
    if link.installation_id is None:
        return strings.get("status.no_installation", login=link.github_login)
    return strings.get(
        "status.linked", login=link.github_login, installation_id=link.installation_id
    )
