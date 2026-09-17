from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    github_token: str = field(default_factory=lambda: os.getenv("GITHUB_TOKEN", ""))
    github_app_client_id: str = field(default_factory=lambda: os.getenv("GITHUB_APP_CLIENT_ID", ""))
    github_app_private_key_path: str = field(
        default_factory=lambda: os.getenv("GITHUB_APP_PRIVATE_KEY_PATH", "")
    )
    database_path: str = field(default_factory=lambda: os.getenv("DATABASE_PATH", "data/bot.db"))
    llm_base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", ""))
    llm_api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", ""))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))


def load_settings(dotenv_path: str | os.PathLike | None = None) -> Settings:
    load_dotenv(dotenv_path=dotenv_path)
    return Settings()
