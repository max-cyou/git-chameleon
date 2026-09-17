"""Core bot entry point."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from git_chameleon.config import load_settings
from git_chameleon.handlers import main_router
from git_chameleon.i18n import I18nMiddleware
from git_chameleon.scheduler import Scheduler
from git_chameleon.services.github_app import GitHubApp
from git_chameleon.services.llm import LLMClient
from git_chameleon.storage import Storage
from git_chameleon.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = load_settings()
    setup_logging(settings.log_level)

    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()

    storage = Storage(settings.database_path)
    github_app = GitHubApp(
        settings.github_app_client_id,
        settings.github_app_private_key_path,
    )
    llm: LLMClient | None = None
    if settings.llm_base_url and settings.llm_api_key and settings.llm_model:
        llm = LLMClient(settings.llm_base_url, settings.llm_api_key, settings.llm_model)
        logger.info("LLM provider configured: %s (%s)", settings.llm_base_url, settings.llm_model)
    else:
        logger.warning("LLM provider not configured (LLM_BASE_URL/LLM_API_KEY/LLM_MODEL)")
    dispatcher.workflow_data.update(storage=storage, github_app=github_app, llm=llm)
    dispatcher.update.outer_middleware(I18nMiddleware())
    dispatcher.include_router(main_router)

    scheduler = Scheduler(bot, storage, github_app, llm)
    scheduler_task = asyncio.create_task(scheduler.run())

    try:
        await dispatcher.start_polling(bot)
    finally:
        scheduler_task.cancel()
        await bot.session.close()
        storage.close()
        await github_app.aclose()
        if llm is not None:
            await llm.aclose()


if __name__ == "__main__":
    asyncio.run(main())
