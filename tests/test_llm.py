import httpx
import respx

from git_chameleon.services.llm import LLMClient, pr_summary


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


@respx.mock
async def test_pr_summary_returns_none_on_failure() -> None:
    respx.post("https://llm.example.com/v1/chat/completions").mock(
        return_value=httpx.Response(500)
    )

    client = _client()
    summary = await pr_summary(client, "octocat", "repo", 8, "title", "body", "en")
    await client.aclose()

    assert summary is None
