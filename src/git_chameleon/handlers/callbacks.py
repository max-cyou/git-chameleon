from __future__ import annotations

from aiogram import F, Router, types
from aiogram.types import InlineKeyboardMarkup

from git_chameleon.handlers.github import install_text, sync_user
from git_chameleon.handlers.keyboards import (
    MenuCB,
    back_to_menu,
    confirm_unlink,
    main_menu,
    menu_text,
    status_text,
)
from git_chameleon.i18n import Strings
from git_chameleon.services.github_app import GitHubApp
from git_chameleon.storage import Storage

router = Router()


async def _show(cb: types.CallbackQuery, text: str, keyboard: InlineKeyboardMarkup) -> None:
    """Edit the original menu message, or send a fresh one if it is inaccessible."""
    message = cb.message
    if isinstance(message, types.Message):
        await message.edit_text(text, reply_markup=keyboard)
    elif cb.bot is not None:
        await cb.bot.send_message(cb.from_user.id, text, reply_markup=keyboard)


@router.callback_query(MenuCB.filter(F.action == "menu"))
async def cb_menu(cb: types.CallbackQuery, storage: Storage, strings: Strings) -> None:
    await cb.answer()
    link = storage.get_link(cb.from_user.id)
    await _show(cb, menu_text(strings, link), main_menu(strings))


@router.callback_query(MenuCB.filter(F.action == "status"))
async def cb_status(cb: types.CallbackQuery, storage: Storage, strings: Strings) -> None:
    await cb.answer()
    link = storage.get_link(cb.from_user.id)
    await _show(cb, status_text(strings, link), back_to_menu(strings))


@router.callback_query(MenuCB.filter(F.action == "sync"))
async def cb_sync(
    cb: types.CallbackQuery, storage: Storage, github_app: GitHubApp, strings: Strings
) -> None:
    await cb.answer()
    user_id = cb.from_user.id
    chat_id = cb.message.chat.id if cb.message is not None else user_id
    storage.ensure_user(user_id, chat_id)
    text = await sync_user(github_app, storage, user_id, strings)
    await _show(cb, text, back_to_menu(strings))


@router.callback_query(MenuCB.filter(F.action == "install"))
async def cb_install(
    cb: types.CallbackQuery, storage: Storage, github_app: GitHubApp, strings: Strings
) -> None:
    await cb.answer()
    user_id = cb.from_user.id
    chat_id = cb.message.chat.id if cb.message is not None else user_id
    storage.ensure_user(user_id, chat_id)
    text = await install_text(github_app, strings)
    await _show(cb, text, back_to_menu(strings))


@router.callback_query(MenuCB.filter(F.action == "unlink"))
async def cb_unlink(cb: types.CallbackQuery, storage: Storage, strings: Strings) -> None:
    link = storage.get_link(cb.from_user.id)
    if link is None or not link.github_login:
        await cb.answer(strings.get("unlink.nothing"), show_alert=True)
        return
    await cb.answer()
    await _show(
        cb,
        strings.get("unlink.confirm", login=link.github_login),
        confirm_unlink(strings),
    )


@router.callback_query(MenuCB.filter(F.action == "unlink_confirm"))
async def cb_unlink_confirm(
    cb: types.CallbackQuery, storage: Storage, strings: Strings
) -> None:
    storage.clear_link(cb.from_user.id)
    await cb.answer(strings.get("unlink.done"))
    await _show(cb, strings.get("unlink.done"), main_menu(strings))
