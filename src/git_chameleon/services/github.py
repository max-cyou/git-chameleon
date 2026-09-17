from __future__ import annotations

from dataclasses import dataclass

import httpx

API_BASE_URL = "https://api.github.com"


@dataclass(frozen=True)
class Repository:
    full_name: str
    description: str | None
    html_url: str
    stargazers_count: int

    def __str__(self) -> str:
        stars = f" {self.stargazers_count} stars" if self.stargazers_count else ""
        desc = f" - {self.description}" if self.description else ""
        return f"*{self.full_name}*{stars}{desc}\n{self.html_url}"


class GitHubClient:
    """Thin async client over the GitHub REST API."""

    def __init__(self, token: str | None = None) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.AsyncClient(base_url=API_BASE_URL, headers=headers)

    async def get_repository(self, name: str) -> Repository:
        response = await self._client.get(f"/repos/{name}")
        response.raise_for_status()
        data = response.json()
        return Repository(
            full_name=data["full_name"],
            description=data.get("description"),
            html_url=data["html_url"],
            stargazers_count=data["stargazers_count"],
        )

    async def aclose(self) -> None:
        await self._client.aclose()
