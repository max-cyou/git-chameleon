import httpx
import respx

from git_chameleon.services import llm as llm_module
from git_chameleon.services.github_app import GitHubApp
from git_chameleon.services.llm import (
    LLMClient,
    build_pr_context,
    markdown_to_html,
    pr_summary,
)
from git_chameleon.storage import Storage


def _client() -> LLMClient:
    return LLMClient("https://llm.example.com/v1", "sk-test", "test-model")


def _completion(text: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"message": {"role": "assistant", "content": text}}]},
    )


@respx.mock
async def test_complete_sends_openai_format() -> None:
    route = respx.post("https://llm.example.com/v1/chat/completions").mock(
        return_value=_completion("Hello!")
    )

    client = _client()
    answer = await client.complete("system prompt", "user prompt")
    await client.aclose()

    assert answer == "Hello!"
    assert route.called
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer sk-test"
    body = request.read().decode()
    assert '"model":"test-model"' in body.replace(", ", ",").replace(": ", ":")
    assert "system prompt" in body
    assert "user prompt" in body


@respx.mock
async def test_pr_summary_cached_per_pr() -> None:
    route = respx.post("https://llm.example.com/v1/chat/completions").mock(
        return_value=_completion("Short summary.")
    )

    client = _client()
    first = await pr_summary(client, "octocat", "repo", 7, "title", "body", "en")
    second = await pr_summary(client, "octocat", "repo", 7, "title", "body", "en")
    await client.aclose()

    assert first == "Short summary."
    assert second == first
    assert route.call_count == 1


def test_format_pr_files_truncates() -> None:
    from git_chameleon.services.github_app import PRFile
    from git_chameleon.services.llm import format_pr_files

    files = [
        PRFile(filename="a.py", additions=10, deletions=2, patch="+print('a')"),
        PRFile(filename="b.py", additions=1, deletions=0, patch=""),
    ]
    rendered = format_pr_files(files)
    assert "a.py (+10/-2)" in rendered
    assert "+print('a')" in rendered
    assert "b.py (+1/-0)" in rendered

    big = [PRFile(filename=f"f{i}.py", additions=5, deletions=5, patch="x" * 3000)
           for i in range(10)]
    assert len(format_pr_files(big)) <= 6500
    assert "remaining files omitted" in format_pr_files(big)


@respx.mock
async def test_pr_summary_includes_files() -> None:
    from git_chameleon.services.github_app import PRFile

    route = respx.post("https://llm.example.com/v1/chat/completions").mock(
        return_value=_completion("Real summary.")
    )

    client = _client()
    llm_module._summary_cache.clear()
    files = [PRFile(filename="cats.txt", additions=3, deletions=0, patch="+ =^.^=")]
    summary = await pr_summary(
        client, "octocat", "repo", 42, "catssssss", "", "ru", files
    )
    await client.aclose()

    assert summary == "Real summary."
    body = route.calls.last.request.read().decode()
    assert "cats.txt" in body
    assert "=^.^=" in body
    assert "не выдумывай" in body.lower() or "выдумывай" in body.lower()


@respx.mock
async def test_pr_summary_returns_none_on_failure() -> None:
    respx.post("https://llm.example.com/v1/chat/completions").mock(
        return_value=httpx.Response(500)
    )

    client = _client()
    summary = await pr_summary(client, "octocat", "repo", 8, "title", "body", "en")
    await client.aclose()

    assert summary is None


def test_markdown_to_html() -> None:
    assert markdown_to_html("**bold**") == "<b>bold</b>"
    assert markdown_to_html("*italic*") == "<i>italic</i>"
    assert markdown_to_html("`code`") == "<code>code</code>"
    assert markdown_to_html("```\nprint('hi')\n```") == "<pre>print('hi')</pre>"
    assert (
        markdown_to_html("[link](https://example.com)")
        == '<a href="https://example.com">link</a>'
    )
    assert markdown_to_html("a **b** `c` **d**") == "a <b>b</b> <code>c</code> <b>d</b>"


def test_markdown_to_html_escapes_raw_html() -> None:
    assert markdown_to_html("<script>x</script>") == "&lt;script&gt;x&lt;/script&gt;"
    assert markdown_to_html("1 < 2 & 3 > 2") == "1 &lt; 2 &amp; 3 &gt; 2"


def test_markdown_to_html_keeps_code_blocks_intact() -> None:
    converted = markdown_to_html("**note**\n```\n**not bold** `x`\n```")
    assert "<b>note</b>" in converted
    assert "<pre>**not bold** `x`</pre>" in converted


@respx.mock
async def test_complete_sends_limits() -> None:
    route = respx.post("https://llm.example.com/v1/chat/completions").mock(
        return_value=_completion("ok")
    )

    client = _client()
    await client.complete("s", "u", max_tokens=123, temperature=0.5)
    await client.aclose()

    body = route.calls.last.request.read().decode()
    assert '"max_tokens":123' in body.replace(" ", "")
    assert '"temperature":0.5' in body.replace(" ", "")


def _github_app(tmp_path) -> GitHubApp:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    key_path = tmp_path / "key.pem"
    key_path.write_text(pem)
    return GitHubApp("client-id", str(key_path))


def _mock_github(prs: list[dict]):
    respx.post("https://api.github.com/app/installations/7/access_tokens").mock(
        return_value=httpx.Response(201, json={"token": "inst-token"})
    )
    repos_route = respx.get("https://api.github.com/installation/repositories").mock(
        return_value=httpx.Response(
            200,
            json={
                "repositories": [
                    {"id": 11, "name": "repo", "owner": {"login": "octocat"}}
                ]
            },
        )
    )
    respx.get("https://api.github.com/repos/octocat/repo/pulls").mock(
        return_value=httpx.Response(200, json=prs)
    )
    return repos_route


@respx.mock
async def test_build_pr_context_with_review(tmp_path) -> None:
    _mock_github(
        [
            {
                "number": 12,
                "title": "Fix login",
                "html_url": "https://github.com/o/r/pull/12",
                "state": "open",
                "body": "body text",
            }
        ]
    )
    llm_route = respx.post("https://llm.example.com/v1/chat/completions").mock(
        return_value=_completion("Fixes auth flow.")
    )

    github_app = _github_app(tmp_path)
    storage = Storage(str(tmp_path / "test.db"))
    storage.ensure_user(1, 100)
    storage.set_github_login(1, "octocat")
    storage.set_installation(1, 7)
    storage.toggle_repo(1, 11)
    storage.toggle_llm_review(1)
    link = storage.get_link(1)
    assert link is not None

    client = _client()
    llm_module._pr_context_cache.clear()
    llm_module._summary_cache.clear()

    context = await build_pr_context(github_app, storage, link, client)
    assert context is not None
    assert "octocat/repo#12: Fix login" in context
    assert "Review: Fixes auth flow." in context

    second = await build_pr_context(github_app, storage, link, client)
    assert second == context
    assert llm_route.call_count == 1  # summary cached

    storage.close()
    await client.aclose()


@respx.mock
async def test_build_pr_context_titles_only_without_review(tmp_path) -> None:
    _mock_github(
        [
            {
                "number": 13,
                "title": "Add tests",
                "html_url": "https://github.com/o/r/pull/13",
                "state": "open",
                "body": "body",
            }
        ]
    )
    llm_route = respx.post("https://llm.example.com/v1/chat/completions").mock(
        return_value=_completion("unused")
    )

    github_app = _github_app(tmp_path)
    storage = Storage(str(tmp_path / "test.db"))
    storage.ensure_user(2, 100)
    storage.set_installation(2, 7)
    storage.toggle_repo(2, 11)
    link = storage.get_link(2)
    assert link is not None
    assert link.llm_review is False

    llm_module._pr_context_cache.clear()
    client = _client()

    context = await build_pr_context(github_app, storage, link, client)
    assert context is not None
    assert "octocat/repo#13: Add tests" in context
    assert "Review:" not in context
    assert llm_route.call_count == 0  # no LLM calls without review flag

    storage.close()
    await client.aclose()


@respx.mock
async def test_build_pr_context_cache_expires(tmp_path) -> None:
    repos_route = _mock_github(
        [
            {
                "number": 14,
                "title": "T",
                "html_url": "u",
                "state": "open",
                "body": "",
            }
        ]
    )

    github_app = _github_app(tmp_path)
    storage = Storage(str(tmp_path / "test.db"))
    storage.ensure_user(3, 100)
    storage.set_installation(3, 7)
    storage.toggle_repo(3, 11)
    link = storage.get_link(3)
    assert link is not None

    llm_module._pr_context_cache.clear()
    client = _client()

    await build_pr_context(github_app, storage, link, client)
    await build_pr_context(github_app, storage, link, client)
    assert repos_route.call_count == 1  # served from cache

    stamp, value = llm_module._pr_context_cache[3]
    llm_module._pr_context_cache[3] = (stamp - llm_module.CONTEXT_TTL_SECONDS, value)
    await build_pr_context(github_app, storage, link, client)
    assert repos_route.call_count == 2  # rebuilt after TTL

    storage.close()
    await client.aclose()
