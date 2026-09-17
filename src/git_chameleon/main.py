"""Core bot entry point."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from git_chameleon.config import load_settings
from git_chameleon.handlers import main_router
from git_chameleon.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = load_settings()
    setup_logging(settings.log_level)

    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")

    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(main_router)

    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
