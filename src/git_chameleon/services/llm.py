from __future__ import annotations

import html
import logging
import re
import time

import httpx

from git_chameleon.services.github_app import GitHubApp
from git_chameleon.storage import Storage, UserLink

logger = logging.getLogger(__name__)

CHAT_SYSTEM_PROMPTS = {
    "en": (
        "You are git-chameleon, an assistant inside a Telegram bot that tracks "
        "the user's GitHub pull requests.\n"
        "- Keep answers short: a few short paragraphs at most.\n"
        "- Answer in the user's language.\n"
        "- Format with Markdown: **bold**, *italic*, `code`, "
        "fenced ```code blocks``` and [links](url).\n"
        "- If open pull requests are listed below, treat them as ground truth "
        "and never invent repository facts."
    ),
    "ru": (
        "Ты — git-chameleon, ассистент в Telegram-боте, который следит за "
        "pull request'ами пользователя на GitHub.\n"
        "- Отвечай кратко: максимум несколько коротких абзацев.\n"
        "- Отвечай на языке пользователя.\n"
        "- Форматируй ответ в Markdown: **жирный**, *курсив*, `код`, "
        "```блоки кода``` и [ссылки](url).\n"
        "- Если ниже перечислены открытые pull request'ы — опирайся только "
        "на них и не выдумывай факты о репозиториях."
    ),
}

SUMMARY_SYSTEM_PROMPTS = {
    "en": (
        "You write detailed pull request reviews for a Telegram digest. "
        "In 4-6 sentences (or a compact bullet list, one item per line "
        "prefixed with '- ') describe: what the PR changes, why it matters, "
        "and what to pay attention to when reviewing. "
        "Plain text only: no Markdown, no HTML. Answer in English."
    ),
    "ru": (
        "Ты пишешь подробные ревью pull request'ов для дайджеста в Telegram. "
        "В 4-6 предложениях (или компактным списком, по пункту на строку "
        "с '- ') опиши: что меняет PR, зачем это нужно и на что обратить "
        "внимание при ревью. Только простой текст: без Markdown и HTML. "
        "Ответь по-русски."
    ),
}

CONTEXT_HEADER = {
    "en": "Currently open pull requests of the user:",
    "ru": "Открытые pull request'ы пользователя сейчас:",
}

CONTEXT_TTL_SECONDS = 300
MAX_CONTEXT_PRS = 15
MAX_USER_CHARS = 4000
CHAT_MAX_TOKENS = 1500
CHAT_TEMPERATURE = 0.4
SUMMARY_MAX_TOKENS = 2000
SUMMARY_TEMPERATURE = 0.2

_summary_cache: dict[tuple[str, str, int], str] = {}
_pr_context_cache: dict[int, tuple[float, str | None]] = {}


class LLMClient:
    """Minimal client for an OpenAI-compatible chat completions API."""

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self._model = model
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60,
        )

    @property
    def model(self) -> str:
        return self._model

    async def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        payload: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature
        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    async def aclose(self) -> None:
        await self._client.aclose()


def chat_system_prompt(locale: str) -> str:
    return CHAT_SYSTEM_PROMPTS.get(locale, CHAT_SYSTEM_PROMPTS["en"])


def summary_system_prompt(locale: str) -> str:
    return SUMMARY_SYSTEM_PROMPTS.get(locale, SUMMARY_SYSTEM_PROMPTS["en"])


async def pr_summary(
    llm: LLMClient,
    owner: str,
    repo: str,
    number: int,
    title: str,
    body: str,
    locale: str,
) -> str | None:
    """Return a cached-or-fresh summary of a pull request, or None on failure."""
    key = (owner, repo, number)
    cached = _summary_cache.get(key)
    if cached is not None:
        return cached

    user_message = f"{owner}/{repo} #{number}: {title}\n\n{body[:4000]}"
    try:
        summary = await llm.complete(
            summary_system_prompt(locale),
            user_message,
            max_tokens=SUMMARY_MAX_TOKENS,
            temperature=SUMMARY_TEMPERATURE,
        )
    except Exception:
        logger.exception("LLM summary failed for %s/%s#%s", owner, repo, number)
        return None
    if not summary:
        logger.warning(
            "LLM summary for %s/%s#%s came back empty (reasoning tokens?)",
            owner,
            repo,
            number,
        )
        return None
    _summary_cache[key] = summary
    return summary


async def build_pr_context(
    github_app: GitHubApp, storage: Storage, link: UserLink, llm: LLMClient | None
) -> str | None:
    """Open-PR context for chat, cached per user for CONTEXT_TTL_SECONDS.

    Each entry carries the LLM review when available, otherwise just the title.
    """
    now = time.monotonic()
    cached = _pr_context_cache.get(link.user_id)
    if cached is not None and now - cached[0] < CONTEXT_TTL_SECONDS:
        return cached[1]

    value = await _collect_pr_context(github_app, storage, link, llm)
    _pr_context_cache[link.user_id] = (now, value)
    return value


async def _collect_pr_context(
    github_app: GitHubApp, storage: Storage, link: UserLink, llm: LLMClient | None
) -> str | None:
    if not link.installation_id:
        return None
    selected = storage.selected_repo_ids(link.user_id)
    if not selected:
        return None

    try:
        token = await github_app.installation_token(link.installation_id)
        repos = [
            repo for repo in await github_app.list_repositories(token)
            if repo["id"] in selected
        ]
    except Exception:
        logger.exception("Failed to build PR context for user %s", link.user_id)
        return None

    review_on = llm is not None and link.llm_review
    entries: list[str] = []
    for repo in repos:
        owner = repo["owner"]["login"]
        name = repo["name"]
        try:
            pulls = await github_app.list_pull_requests(token, owner, name)
        except Exception:
            logger.exception("Failed to fetch pull requests for %s/%s", owner, name)
            continue
        for pr in pulls:
            entry = f"{owner}/{name}#{pr.number}: {pr.title}"
            if review_on and llm is not None:
                summary = await pr_summary(
                    llm, owner, name, pr.number, pr.title, pr.body, link.locale or "en"
                )
                if summary:
                    entry += "\n  Review: " + summary.replace("\n", " ")
            entries.append(entry)
            if len(entries) >= MAX_CONTEXT_PRS:
                break
        if len(entries) >= MAX_CONTEXT_PRS:
            break
    if not entries:
        return None
    header = CONTEXT_HEADER.get(link.locale or "en", CONTEXT_HEADER["en"])
    return header + "\n" + "\n".join(f"- {entry}" for entry in entries)


_CODE_BLOCK_RE = re.compile(r"```(?:[a-zA-Z0-9_-]+)?[ \t]*\n?(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*|__(.+?)__", re.DOTALL)
_ITALIC_RE = re.compile(r"(?<![\*_])\*(?!\s)(.+?)(?<!\s)\*(?![\*_])", re.DOTALL)
_LINK_RE = re.compile(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)")


def markdown_to_html(text: str) -> str:
    """Convert a Markdown answer to Telegram HTML.

    Raw HTML in the answer is escaped first, so only converted markup remains.
    """
    stash: dict[str, str] = {}

    def keep(converted: str) -> str:
        key = f"\x00{len(stash)}\x00"
        stash[key] = converted
        return key

    escaped = html.escape(text, quote=False)

    def stash_code_block(match: re.Match[str]) -> str:
        return keep(f"<pre>{match.group(1).strip()}</pre>")

    def stash_inline_code(match: re.Match[str]) -> str:
        return keep(f"<code>{match.group(1)}</code>")

    def stash_link(match: re.Match[str]) -> str:
        return keep(f'<a href="{match.group(2)}">{match.group(1)}</a>')

    converted = _CODE_BLOCK_RE.sub(stash_code_block, escaped)
    converted = _INLINE_CODE_RE.sub(stash_inline_code, converted)
    converted = _LINK_RE.sub(stash_link, converted)
    converted = _BOLD_RE.sub(
        lambda m: f"<b>{m.group(1) or m.group(2)}</b>", converted
    )
    converted = _ITALIC_RE.sub(lambda m: f"<i>{m.group(1)}</i>", converted)

    for key, value in stash.items():
        converted = converted.replace(key, value)
    return converted
