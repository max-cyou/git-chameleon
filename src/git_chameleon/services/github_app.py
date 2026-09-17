from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import httpx
import jwt

API_BASE_URL = "https://api.github.com"
ACTIONS_URL_TPL = "https://github.com/apps/{slug}/installations/new"

GITHUB_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


@dataclass(frozen=True)
class Installation:
    id: int
    account_login: str
    account_type: str

    @classmethod
    def from_dict(cls, data: dict) -> Installation:
        return cls(
            id=data["id"],
            account_login=data["account"]["login"],
            account_type=data["account"]["type"],
        )


@dataclass(frozen=True)
class PullRequest:
    number: int
    title: str
    html_url: str
    state: str
    is_draft: bool
    body: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> PullRequest:
        return cls(
            number=data["number"],
            title=data["title"],
            html_url=data["html_url"],
            state=data["state"],
            is_draft=bool(data.get("draft", False)),
            body=data.get("body") or "",
        )


class GitHubApp:
    """GitHub App client: JWT auth, installations and installation tokens."""

    def __init__(self, client_id: str, private_key_path: str) -> None:
        self._client_id = client_id
        self._private_key = Path(private_key_path).read_text()
        self._client = httpx.AsyncClient(base_url=API_BASE_URL)

    def _jwt(self) -> str:
        now = int(time.time())
        payload = {"iat": now, "exp": now + 540, "iss": self._client_id}
        return jwt.encode(payload, self._private_key, algorithm="RS256")

    async def _request(
        self,
        method: str,
        url: str,
        *,
        token: str | None = None,
        params: dict | None = None,
    ) -> httpx.Response:
        headers = dict(GITHUB_HEADERS)
        headers["Authorization"] = f"Bearer {token or self._jwt()}"
        response = await self._client.request(method, url, headers=headers, params=params)
        response.raise_for_status()
        return response

    async def get_slug(self) -> str:
        response = await self._request("GET", "/app")
        return response.json()["slug"]

    def install_url(self, slug: str) -> str:
        return ACTIONS_URL_TPL.format(slug=slug)

    async def list_installations(self) -> list[Installation]:
        response = await self._request("GET", "/app/installations", params={"per_page": 100})
        return [Installation.from_dict(item) for item in response.json()]

    async def installation_token(self, installation_id: int) -> str:
        response = await self._request(
            "POST", f"/app/installations/{installation_id}/access_tokens"
        )
        return response.json()["token"]

    async def list_repositories(self, token: str) -> list[dict]:
        response = await self._request("GET", "/installation/repositories", token=token)
        return response.json()["repositories"]

    async def list_pull_requests(
        self, token: str, owner: str, repo: str, *, state: str = "open"
    ) -> list[PullRequest]:
        response = await self._request(
            "GET", f"/repos/{owner}/{repo}/pulls", token=token, params={"state": state}
        )
        return [PullRequest.from_dict(item) for item in response.json()]

    async def aclose(self) -> None:
        await self._client.aclose()
