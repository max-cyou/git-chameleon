from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from git_chameleon.storage import UserLink


class MenuCB(CallbackData, prefix="menu"):
    action: str


def main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Status", callback_data=MenuCB(action="status"))
    builder.button(text="Sync now", callback_data=MenuCB(action="sync"))
    builder.button(text="Install App", callback_data=MenuCB(action="install"))
    builder.button(text="Unlink", callback_data=MenuCB(action="unlink"))
    builder.adjust(2)
    return builder.as_markup()


def confirm_unlink() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Yes, unlink", callback_data=MenuCB(action="unlink_confirm"))
    builder.button(text="Cancel", callback_data=MenuCB(action="menu"))
    builder.adjust(2)
    return builder.as_markup()


def back_to_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Back to menu", callback_data=MenuCB(action="menu"))
    return builder.as_markup()


def menu_text(link: UserLink | None) -> str:
    title = "git-chameleon control panel"
    if link is None or not link.github_login:
        return f"{title}\nNot linked. Press Install App or send /link <github-username>."
    if link.installation_id is None:
        return f"{title}\nGitHub: @{link.github_login} (no installation yet, press Sync now)."
    return f"{title}\nGitHub: @{link.github_login}\nInstallation: #{link.installation_id}"


def status_text(link: UserLink | None) -> str:
    if link is None or not link.github_login:
        return "Not linked. Press Install App or send /link <github-username>."
    if link.installation_id is None:
        return f"GitHub: @{link.github_login}\nNo installation matched yet. Press Sync now."
    return f"GitHub: @{link.github_login}\nInstallation: #{link.installation_id}"
