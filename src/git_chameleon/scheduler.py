from __future__ import annotations

import asyncio
import html
import logging

from aiogram import Bot

from git_chameleon.i18n import Strings
from git_chameleon.services.github_app import GitHubApp
from git_chameleon.services.llm import LLMClient, pr_summary
from git_chameleon.storage import Storage, UserLink

logger = logging.getLogger(__name__)

SYNC_INTERVAL_SECONDS = 60
DIGEST_INTERVAL_SECONDS = 300


def _fmt_pr(
    owner: str, repo: str, number: int, title: str, is_draft: bool, draft_marker: str
) -> str:
    draft = f" {draft_marker}" if is_draft else ""
    return f"#{number}{draft} {html.escape(title)} ({owner}/{repo})"


async def digest_text(
    github_app: GitHubApp,
    link: UserLink,
    strings: Strings | None = None,
    selected_ids: set[int] | None = None,
    llm: LLMClient | None = None,
) -> tuple[str, set[str]] | None:
    """Return the digest text with its PR keys, or None if nothing to report."""
    if not link.installation_id:
        return None
    if not selected_ids:
        return None
    strings = strings or Strings(link.locale)
    token = await github_app.installation_token(link.installation_id)
    repos = [repo for repo in await github_app.list_repositories(token)
             if repo["id"] in selected_ids]

    review_on = llm is not None and link.llm_review
    blocks: list[str] = []
    pr_keys: set[str] = set()
    for repo in repos:
        owner = repo["owner"]["login"]
        name = repo["name"]
        try:
            pulls = await github_app.list_pull_requests(token, owner, name)
        except Exception:
            logger.exception("Failed to fetch pull requests for %s/%s", owner, name)
            continue
        for pr in pulls:
            pr_keys.add(f"{owner}/{name}#{pr.number}")
            line = _fmt_pr(
                owner, name, pr.number, pr.title, pr.is_draft, strings.get("digest.draft")
            )
            if review_on and llm is not None:
                try:
                    files = await github_app.list_pr_files(token, owner, name, pr.number)
                except Exception:
                    logger.exception(
                        "Failed to fetch files for %s/%s#%s", owner, name, pr.number
                    )
                    files = None
                summary = await pr_summary(
                    llm,
                    owner,
                    name,
                    pr.number,
                    pr.title,
                    pr.body,
                    strings.locale,
                    files,
                )
                if summary:
                    line += "\n<i>" + html.escape(summary) + "</i>"
            blocks.append(line)

    if not blocks:
        return None
    mention = (
        f'<a href="tg://user?id={link.user_id}">@{link.github_login or "user"}</a>'
    )
    footer = None if review_on else strings.get("digest.no_llm")
    parts = (
        strings.get("digest.title"),
        strings.get("digest.mention", mention=mention),
        "\n".join(blocks),
        footer,
        strings.get("digest.total", total=len(blocks)),
    )
    return "\n\n".join(part for part in parts if part), pr_keys


class Scheduler:
    """Periodic tasks: refresh installations and report open PRs."""

    def __init__(
        self,
        bot: Bot,
        storage: Storage,
        github_app: GitHubApp,
        llm: LLMClient | None = None,
    ) -> None:
        self._bot = bot
        self._storage = storage
        self._github_app = github_app
        self._llm = llm

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
            selected = self._storage.selected_repo_ids(link.user_id)
            digest = await digest_text(
                self._github_app, link, Strings(link.locale), selected, self._llm
            )
            if digest is None:
                continue
            text, pr_keys = digest
            destinations = [link.chat_id] + self._storage.digest_group_ids(link.user_id)
            for chat_id in destinations:
                fresh = pr_keys - self._storage.known_pr_keys(chat_id)
                if not fresh:
                    continue
                try:
                    await asyncio.wait_for(
                        self._bot.send_message(chat_id, text), timeout=60
                    )
                except Exception:
                    logger.exception("Failed to send digest to chat %s", chat_id)
                    continue
                self._storage.add_pr_keys(chat_id, fresh)

    async def run(self) -> None:
        logger.info("Scheduler started")
        while True:
            try:
                await self.sync_installations()
                await self.check_prs()
            except Exception:
                logger.exception("Scheduler cycle failed")
            await asyncio.sleep(DIGEST_INTERVAL_SECONDS)
