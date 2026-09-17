from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from git_chameleon.i18n import Strings
from git_chameleon.storage import UserLink


class MenuCB(CallbackData, prefix="menu"):
    action: str


def main_menu(strings: Strings) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=strings.get("btn.status"), callback_data=MenuCB(action="status"))
    builder.button(text=strings.get("btn.sync"), callback_data=MenuCB(action="sync"))
    builder.button(text=strings.get("btn.install"), callback_data=MenuCB(action="install"))
    builder.button(text=strings.get("btn.unlink"), callback_data=MenuCB(action="unlink"))
    builder.adjust(2)
    return builder.as_markup()


def confirm_unlink(strings: Strings) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=strings.get("btn.unlink_confirm"), callback_data=MenuCB(action="unlink_confirm")
    )
    builder.button(text=strings.get("btn.cancel"), callback_data=MenuCB(action="menu"))
    builder.adjust(2)
    return builder.as_markup()


def back_to_menu(strings: Strings) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=strings.get("btn.back"), callback_data=MenuCB(action="menu"))
    return builder.as_markup()


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
