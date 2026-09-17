import httpx
import pytest
import respx

from git_chameleon.services.github import GitHubClient, Repository


@respx.mock
async def test_get_repository() -> None:
    route = respx.get("https://api.github.com/repos/python-telegram-bot/python-telegram-bot").mock(
        return_value=httpx.Response(
            200,
            json={
                "full_name": "python-telegram-bot/python-telegram-bot",
                "description": "We have made you a wrapper you can't refuse",
                "html_url": "https://github.com/python-telegram-bot/python-telegram-bot",
                "stargazers_count": 26000,
            },
        )
    )

    client = GitHubClient()
    repo = await client.get_repository("python-telegram-bot/python-telegram-bot")
    await client.aclose()

    assert route.called
    assert isinstance(repo, Repository)
    assert repo.full_name == "python-telegram-bot/python-telegram-bot"
    assert repo.html_url.startswith("https://github.com/")


@respx.mock
async def test_get_repository_raises_on_404() -> None:
    respx.get("https://api.github.com/repos/nope/nope").mock(return_value=httpx.Response(404))

    client = GitHubClient()
    with pytest.raises(httpx.HTTPStatusError):
        await client.get_repository("nope/nope")
    await client.aclose()
