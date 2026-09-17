from __future__ import annotations

from aiogram import Bot, Router
from aiogram.types import BotCommand

router = Router()

commands = ["/start", "/help"]


@router.startup()
async def set_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands([BotCommand(command=cmd, description=cmd) for cmd in commands])
