from __future__ import annotations

from aiogram import Bot, F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup

from git_chameleon.handlers.github import install_text, sync_user
from git_chameleon.handlers.keyboards import (
    REPOS_PER_PAGE,
    GroupCB,
    MenuCB,
    RepoCB,
    add_group_url,
    back_to_menu,
    back_to_settings,
    confirm_unlink,
    groups_keyboard,
    llm_menu,
    llm_screen_text,
    main_menu,
    menu_text,
    repos_keyboard,
    settings_menu,
)
from git_chameleon.i18n import Strings
from git_chameleon.services.github_app import GitHubApp
from git_chameleon.services.llm import LLMClient
from git_chameleon.storage import Storage

router = Router()


async def _show(cb: types.CallbackQuery, text: str, keyboard: InlineKeyboardMarkup) -> None:
    """Edit the original menu message, or send a fresh one if it is inaccessible."""
    message = cb.message
    if isinstance(message, types.Message):
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as exc:
            if "message is not modified" not in str(exc):
                raise
    elif cb.bot is not None:
        await cb.bot.send_message(cb.from_user.id, text, reply_markup=keyboard)


async def _repos_view(
    github_app: GitHubApp,
    storage: Storage,
    user_id: int,
    strings: Strings,
    page: int,
) -> tuple[str, InlineKeyboardMarkup]:
    link = storage.get_link(user_id)
    if link is None or not link.installation_id:
        return strings.get("repos.not_linked"), back_to_settings(strings)

    token = await github_app.installation_token(link.installation_id)
    repos = sorted(
        await github_app.list_repositories(token),
        key=lambda repo: repo["full_name"].lower(),
    )
    if not repos:
        return strings.get("repos.none"), back_to_settings(strings)

    pages = -(-len(repos) // REPOS_PER_PAGE)
    page = max(0, min(page, pages - 1))
    selected = storage.selected_repo_ids(user_id)
    chunk = repos[page * REPOS_PER_PAGE : (page + 1) * REPOS_PER_PAGE]
    rows = [(repo["id"], repo["full_name"], repo["id"] in selected) for repo in chunk]

    text = "\n".join(
        (
            strings.get("repos.title"),
            strings.get("repos.count", total=len(repos)),
            strings.get("repos.selected", selected=len(selected)),
            strings.get("repos.page_info", page=page + 1, pages=pages),
            "",
            strings.get("repos.hint"),
        )
    )
    return text, repos_keyboard(strings, rows, page, pages)


@router.callback_query(MenuCB.filter(F.action == "menu"))
async def cb_menu(
    cb: types.CallbackQuery, storage: Storage, strings: Strings, bot: Bot
) -> None:
    await cb.answer()
    link = storage.get_link(cb.from_user.id)
    await _show(
        cb, menu_text(strings, link), main_menu(strings, await add_group_url(bot))
    )


@router.callback_query(MenuCB.filter(F.action == "link"))
async def cb_link(
    cb: types.CallbackQuery,
    storage: Storage,
    github_app: GitHubApp,
    strings: Strings,
    llm: LLMClient | None,
) -> None:
    await cb.answer()
    user_id = cb.from_user.id
    chat_id = cb.message.chat.id if cb.message is not None else user_id
    storage.ensure_user(user_id, chat_id)

    link = storage.get_link(user_id)
    if link is None or not link.github_login:
        text = await install_text(github_app, strings)
    else:
        text = await sync_user(github_app, storage, user_id, strings, llm)
    await _show(cb, text, back_to_menu(strings))


@router.callback_query(MenuCB.filter(F.action == "settings"))
async def cb_settings(cb: types.CallbackQuery, strings: Strings) -> None:
    await cb.answer()
    await _show(cb, strings.get("settings.text"), settings_menu(strings))


def _groups_view(
    storage: Storage, user_id: int, strings: Strings, page: int
) -> tuple[str, InlineKeyboardMarkup]:
    groups = storage.groups_for_user(user_id)
    if not groups:
        return strings.get("groups.none"), back_to_settings(strings)

    pages = -(-len(groups) // REPOS_PER_PAGE)
    page = max(0, min(page, pages - 1))
    chunk = groups[page * REPOS_PER_PAGE : (page + 1) * REPOS_PER_PAGE]
    rows = [(g.chat_id, g.title or str(g.chat_id), g.mention_prs) for g in chunk]
    on_count = sum(1 for g in groups if g.mention_prs)
    text = "\n".join(
        (
            strings.get("groups.title"),
            strings.get("groups.count", total=len(groups)),
            strings.get("groups.on", on=on_count),
            "",
            strings.get("groups.hint"),
        )
    )
    return text, groups_keyboard(strings, rows, page, pages)


@router.callback_query(MenuCB.filter(F.action == "groups"))
async def cb_groups(cb: types.CallbackQuery, storage: Storage, strings: Strings) -> None:
    await cb.answer()
    text, keyboard = _groups_view(storage, cb.from_user.id, strings, page=0)
    await _show(cb, text, keyboard)


@router.callback_query(GroupCB.filter(F.action == "page"))
async def cb_group_page(
    cb: types.CallbackQuery, callback_data: GroupCB, storage: Storage, strings: Strings
) -> None:
    await cb.answer()
    text, keyboard = _groups_view(
        storage, cb.from_user.id, strings, page=callback_data.page
    )
    await _show(cb, text, keyboard)


@router.callback_query(GroupCB.filter(F.action == "toggle"))
async def cb_group_toggle(
    cb: types.CallbackQuery, callback_data: GroupCB, storage: Storage, strings: Strings
) -> None:
    await cb.answer()
    if callback_data.chat_id:
        storage.toggle_group_mentions(callback_data.chat_id)
    text, keyboard = _groups_view(
        storage, cb.from_user.id, strings, page=callback_data.page
    )
    await _show(cb, text, keyboard)


@router.callback_query(MenuCB.filter(F.action == "llm"))
async def cb_llm(
    cb: types.CallbackQuery,
    storage: Storage,
    llm: LLMClient | None,
    strings: Strings,
) -> None:
    await cb.answer()
    link = storage.get_link(cb.from_user.id)
    await _show(
        cb,
        llm_screen_text(strings, llm is not None, llm.model if llm else ""),
        llm_menu(strings, link, llm is not None),
    )


@router.callback_query(MenuCB.filter(F.action == "llm_chat"))
async def cb_llm_chat(
    cb: types.CallbackQuery, storage: Storage, llm: LLMClient | None, strings: Strings
) -> None:
    await cb.answer()
    storage.ensure_user(cb.from_user.id, cb.message.chat.id if cb.message else cb.from_user.id)
    storage.toggle_llm_chat(cb.from_user.id)
    link = storage.get_link(cb.from_user.id)
    await _show(
        cb,
        llm_screen_text(strings, llm is not None, llm.model if llm else ""),
        llm_menu(strings, link, llm is not None),
    )


@router.callback_query(MenuCB.filter(F.action == "llm_review"))
async def cb_llm_review(
    cb: types.CallbackQuery, storage: Storage, llm: LLMClient | None, strings: Strings
) -> None:
    await cb.answer()
    storage.ensure_user(cb.from_user.id, cb.message.chat.id if cb.message else cb.from_user.id)
    storage.toggle_llm_review(cb.from_user.id)
    link = storage.get_link(cb.from_user.id)
    await _show(
        cb,
        llm_screen_text(strings, llm is not None, llm.model if llm else ""),
        llm_menu(strings, link, llm is not None),
    )


@router.callback_query(MenuCB.filter(F.action == "repos"))
async def cb_repos(
    cb: types.CallbackQuery, storage: Storage, github_app: GitHubApp, strings: Strings
) -> None:
    await cb.answer()
    text, keyboard = await _repos_view(
        github_app, storage, cb.from_user.id, strings, page=0
    )
    await _show(cb, text, keyboard)


@router.callback_query(RepoCB.filter(F.action == "page"))
async def cb_repo_page(
    cb: types.CallbackQuery,
    callback_data: RepoCB,
    storage: Storage,
    github_app: GitHubApp,
    strings: Strings,
) -> None:
    await cb.answer()
    text, keyboard = await _repos_view(
        github_app, storage, cb.from_user.id, strings, page=callback_data.page
    )
    await _show(cb, text, keyboard)


@router.callback_query(RepoCB.filter(F.action == "toggle"))
async def cb_repo_toggle(
    cb: types.CallbackQuery,
    callback_data: RepoCB,
    storage: Storage,
    github_app: GitHubApp,
    strings: Strings,
) -> None:
    await cb.answer()
    if callback_data.repo_id:
        storage.toggle_repo(cb.from_user.id, callback_data.repo_id)
    text, keyboard = await _repos_view(
        github_app, storage, cb.from_user.id, strings, page=callback_data.page
    )
    await _show(cb, text, keyboard)


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
