import pytest

from git_chameleon.config import load_settings


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_APP_CLIENT_ID", raising=False)
    monkeypatch.delenv("GITHUB_APP_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    settings = load_settings(dotenv_path=tmp_path / "missing.env")

    assert settings.bot_token == ""
    assert settings.github_token == ""
    assert settings.log_level == "INFO"


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("BOT_TOKEN", "test-token")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = load_settings(dotenv_path=tmp_path / "missing.env")

    assert settings.bot_token == "test-token"
    assert settings.log_level == "DEBUG"
