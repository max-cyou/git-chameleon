from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from git_chameleon.services.github_app import GitHubApp
from git_chameleon.storage import Storage, UserLink

logger = logging.getLogger(__name__)

SYNC_INTERVAL_SECONDS = 60
DIGEST_INTERVAL_SECONDS = 300


def _fmt_pr(owner: str, repo: str, number: int, title: str, is_draft: bool) -> str:
    draft = " [draft]" if is_draft else ""
    return f"#{number}{draft} {title} ({owner}/{repo})"


async def digest_text(github_app: GitHubApp, link: UserLink) -> str | None:
    """Return a text digest of open pull requests, or None if nothing to report."""
    if not link.installation_id:
        return None
    token = await github_app.installation_token(link.installation_id)
    repos = await github_app.list_repositories(token)

    lines: list[str] = []
    for repo in repos:
        owner = repo["owner"]["login"]
        name = repo["name"]
        try:
            pulls = await github_app.list_pull_requests(token, owner, name)
        except Exception:
            logger.exception("Failed to fetch pull requests for %s/%s", owner, name)
            continue
        lines.extend(_fmt_pr(owner, name, pr.number, pr.title, pr.is_draft) for pr in pulls)

    if not lines:
        return None
    return "Open PRs:\n\n" + "\n".join(lines)


class Scheduler:
    """Periodic tasks: refresh installations and report open PRs."""

    def __init__(self, bot: Bot, storage: Storage, github_app: GitHubApp) -> None:
        self._bot = bot
        self._storage = storage
        self._github_app = github_app
        self._last_digest: dict[int, str | None] = {}

    async def sync_installations(self) -> None:
        try:
            installations = await self._github_app.list_installations()
        except Exception:
            logger.exception("Failed to list installations")
            return
        for link in self._storage.all_links():
            if not link.github_login:
                continue
            match = next(
                (
                    inst
                    for inst in installations
                    if inst.account_login.lower() == link.github_login.lower()
                ),
                None,
            )
            if match is None:
                continue
            if link.installation_id != match.id:
                self._storage.set_installation(link.user_id, match.id)
                logger.info("Linked installation %s to user %s", match.id, link.user_id)

    async def check_prs(self) -> None:
        for link in self._storage.all_links():
            digest = await digest_text(self._github_app, link)
            if digest == self._last_digest.get(link.user_id):
                continue
            self._last_digest[link.user_id] = digest
            if digest is not None:
                await self._bot.send_message(link.chat_id, digest)

    async def run(self) -> None:
        logger.info("Scheduler started")
        while True:
            await self.sync_installations()
            await self.check_prs()
            await asyncio.sleep(DIGEST_INTERVAL_SECONDS)
