from __future__ import annotations

import re

from aiogram import Router, types
from aiogram.filters import Command

from git_chameleon.scheduler import digest_text
from git_chameleon.services.github_app import GitHubApp
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


async def _find_installation(github_app: GitHubApp, login: str):
    installations = await github_app.list_installations()
    return next(
        (inst for inst in installations if inst.account_login.lower() == login.lower()),
        None,
    )


@router.message(Command("install"))
async def on_install(message: types.Message, storage: Storage, github_app: GitHubApp) -> None:
    storage.ensure_user(_user_id(message), message.chat.id)
    slug = await github_app.get_slug()
    await message.answer(
        "Open this link and press the Install button:\n\n"
        f"{github_app.install_url(slug)}\n\n"
        "Afterwards run /link <your-github-username>"
    )


@router.message(Command("link"))
async def on_link(message: types.Message, storage: Storage, github_app: GitHubApp) -> None:
    user_id = _user_id(message)
    storage.ensure_user(user_id, message.chat.id)

    login = _extract_login(message.text or "")
    if login is None:
        await message.answer("Usage: /link <github-username>")
        return

    storage.set_github_login(user_id, login)

    installation = await _find_installation(github_app, login)
    if installation is None:
        await message.answer(
            f"No installation for @{login} yet. Open /install to add it, then /sync."
        )
        return

    storage.set_installation(user_id, installation.id)
    await message.answer(f"Linked @{login} (installation #{installation.id}).")


@router.message(Command("sync"))
async def on_sync(message: types.Message, storage: Storage, github_app: GitHubApp) -> None:
    user_id = _user_id(message)
    storage.ensure_user(user_id, message.chat.id)
    link = storage.get_link(user_id)

    if link is None or not link.github_login:
        await message.answer("Run /link <your-github-username> first.")
        return

    installation = await _find_installation(github_app, link.github_login)
    if installation is None:
        await message.answer(
            f"No installation for @{link.github_login} yet. Open /install to add it."
        )
        return

    storage.set_installation(user_id, installation.id)
    digest = await digest_text(github_app, link)
    if digest:
        await message.answer(f"Linked to installation #{installation.id}.\n\n{digest}")
    else:
        await message.answer(f"Linked to installation #{installation.id}. No open PRs.")


@router.message(Command("unlink"))
async def on_unlink(message: types.Message, storage: Storage) -> None:
    storage.clear_link(_user_id(message))
    await message.answer("Unlinked.")


@router.message(Command("status"))
async def on_status(message: types.Message, storage: Storage, github_app: GitHubApp) -> None:
    user_id = _user_id(message)
    storage.ensure_user(user_id, message.chat.id)
    link = storage.get_link(user_id)

    if link is None or not link.github_login:
        await message.answer("Not linked. Run /link <your-github-username>.")
        return
    if link.installation_id is None:
        await message.answer(f"GitHub: @{link.github_login}. No installation matched yet.")
        return
    await message.answer(f"GitHub: @{link.github_login}\nInstallation: #{link.installation_id}")
