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
async def cb_menu(cb: types.CallbackQuery, storage: Storage) -> None:
    await cb.answer()
    link = storage.get_link(cb.from_user.id)
    await _show(cb, menu_text(link), main_menu())


@router.callback_query(MenuCB.filter(F.action == "status"))
async def cb_status(cb: types.CallbackQuery, storage: Storage) -> None:
    await cb.answer()
    link = storage.get_link(cb.from_user.id)
    await _show(cb, status_text(link), back_to_menu())


@router.callback_query(MenuCB.filter(F.action == "sync"))
async def cb_sync(cb: types.CallbackQuery, storage: Storage, github_app: GitHubApp) -> None:
    await cb.answer()
    user_id = cb.from_user.id
    chat_id = cb.message.chat.id if cb.message is not None else user_id
    storage.ensure_user(user_id, chat_id)
    text = await sync_user(github_app, storage, user_id)
    await _show(cb, text, back_to_menu())


@router.callback_query(MenuCB.filter(F.action == "install"))
async def cb_install(cb: types.CallbackQuery, storage: Storage, github_app: GitHubApp) -> None:
    await cb.answer()
    storage.ensure_user(cb.from_user.id, cb.message.chat.id if cb.message else cb.from_user.id)
    text = await install_text(github_app)
    await _show(cb, text, back_to_menu())


@router.callback_query(MenuCB.filter(F.action == "unlink"))
async def cb_unlink(cb: types.CallbackQuery, storage: Storage) -> None:
    link = storage.get_link(cb.from_user.id)
    if link is None or not link.github_login:
        await cb.answer("Nothing to unlink.", show_alert=True)
        return
    await cb.answer()
    await _show(
        cb,
        f"Unlink GitHub account @{link.github_login}?",
        confirm_unlink(),
    )


@router.callback_query(MenuCB.filter(F.action == "unlink_confirm"))
async def cb_unlink_confirm(cb: types.CallbackQuery, storage: Storage) -> None:
    storage.clear_link(cb.from_user.id)
    await cb.answer("Unlinked.")
    await _show(cb, "Unlinked.", main_menu())
