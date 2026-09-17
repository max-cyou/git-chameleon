from __future__ import annotations

import re

from aiogram import Router, types
from aiogram.filters import Command

from git_chameleon.handlers.keyboards import main_menu, menu_text, status_text
from git_chameleon.i18n import Strings
from git_chameleon.scheduler import digest_text
from git_chameleon.services.github_app import GitHubApp, Installation
from git_chameleon.storage import Storage

router = Router()

GITHUB_LOGIN_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37})$")


def _extract_login(text: str) -> str | None:
    parts = text.strip().split()
    if len(parts) < 2:
        return None
    login = parts[1].lstrip("@")
    return login if GITHUB_LOGIN_RE.match(login) else None


def _user_id(message: types.Message) -> int:
    user = message.from_user
    if user is None:
        raise ValueError("Message has no sender")
    return user.id


async def _find_installation(github_app: GitHubApp, login: str) -> Installation | None:
    installations = await github_app.list_installations()
    return next(
        (inst for inst in installations if inst.account_login.lower() == login.lower()),
        None,
    )


async def install_text(github_app: GitHubApp, strings: Strings) -> str:
    slug = await github_app.get_slug()
    return strings.get("install.text", url=github_app.install_url(slug))


async def link_user(
    github_app: GitHubApp, storage: Storage, user_id: int, login: str, strings: Strings
) -> str:
    storage.set_github_login(user_id, login)

    installation = await _find_installation(github_app, login)
    if installation is None:
        return strings.get("link.no_installation", login=login)

    storage.set_installation(user_id, installation.id)
    text = strings.get("link.linked", login=login, installation_id=installation.id)
    if not storage.selected_repo_ids(user_id):
        text += "\n\n" + strings.get("link.notify_repos")
    return text


async def sync_user(
    github_app: GitHubApp, storage: Storage, user_id: int, strings: Strings
) -> str:
    link = storage.get_link(user_id)
    if link is None or not link.github_login:
        return strings.get("sync.not_linked")

    installation = await _find_installation(github_app, link.github_login)
    if installation is None:
        return strings.get("sync.no_installation", login=link.github_login)

    storage.set_installation(user_id, installation.id)
    selected = storage.selected_repo_ids(user_id)
    if not selected:
        return strings.get("sync.no_repos", installation_id=installation.id)

    link = storage.get_link(user_id)
    digest = await digest_text(github_app, link, strings, selected) if link else None
    if digest:
        return strings.get(
            "sync.linked_digest", installation_id=installation.id, digest=digest
        )
    return strings.get("sync.linked_no_prs", installation_id=installation.id)


@router.message(Command("install"))
async def on_install(
    message: types.Message, storage: Storage, github_app: GitHubApp, strings: Strings
) -> None:
    storage.ensure_user(_user_id(message), message.chat.id)
    text = await install_text(github_app, strings)
    await message.answer(text, reply_markup=main_menu(strings))


@router.message(Command("link"))
async def on_link(
    message: types.Message, storage: Storage, github_app: GitHubApp, strings: Strings
) -> None:
    user_id = _user_id(message)
    storage.ensure_user(user_id, message.chat.id)

    login = _extract_login(message.text or "")
    if login is None:
        await message.answer(strings.get("link.usage"))
        return

    text = await link_user(github_app, storage, user_id, login, strings)
    await message.answer(text, reply_markup=main_menu(strings))


@router.message(Command("sync"))
async def on_sync(
    message: types.Message, storage: Storage, github_app: GitHubApp, strings: Strings
) -> None:
    user_id = _user_id(message)
    storage.ensure_user(user_id, message.chat.id)
    text = await sync_user(github_app, storage, user_id, strings)
    await message.answer(text, reply_markup=main_menu(strings))


@router.message(Command("unlink"))
async def on_unlink(message: types.Message, storage: Storage, strings: Strings) -> None:
    user_id = _user_id(message)
    storage.ensure_user(user_id, message.chat.id)
    storage.clear_link(user_id)
    await message.answer(strings.get("unlink.done"), reply_markup=main_menu(strings))


@router.message(Command("status"))
async def on_status(
    message: types.Message, storage: Storage, github_app: GitHubApp, strings: Strings
) -> None:
    user_id = _user_id(message)
    storage.ensure_user(user_id, message.chat.id)
    link = storage.get_link(user_id)
    await message.answer(status_text(strings, link), reply_markup=main_menu(strings))


@router.message(Command("menu"))
async def on_menu(message: types.Message, storage: Storage, strings: Strings) -> None:
    user_id = _user_id(message)
    storage.ensure_user(user_id, message.chat.id)
    link = storage.get_link(user_id)
    await message.answer(menu_text(strings, link), reply_markup=main_menu(strings))
