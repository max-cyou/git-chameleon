from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    github_token: str = field(default_factory=lambda: os.getenv("GITHUB_TOKEN", ""))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))


def load_settings() -> Settings:
    load_dotenv()
    return Settings()
