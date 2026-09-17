from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

CHAT_SYSTEM_PROMPTS = {
    "en": "You are a helpful assistant inside a Telegram bot. Answer briefly.",
    "ru": "Ты полезный ассистент в Telegram-боте. Отвечай кратко.",
}

SUMMARY_SYSTEM_PROMPTS = {
    "en": "Summarize the pull request below in one or two sentences. Answer in English.",
    "ru": "Сделай краткое саммари pull request'а ниже в одном-двух предложениях. Ответь по-русски.",
}

_summary_cache: dict[tuple[str, str, int], str] = {}


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

    async def complete(self, system: str, user: str) -> str:
        response = await self._client.post(
            "/chat/completions",
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
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
        summary = await llm.complete(summary_system_prompt(locale), user_message)
    except Exception:
        logger.exception("LLM summary failed for %s/%s#%s", owner, repo, number)
        return None
    _summary_cache[key] = summary
    return summary
