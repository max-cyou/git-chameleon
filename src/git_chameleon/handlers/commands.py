from __future__ import annotations

from aiogram import Router, types
from aiogram.filters import Command, CommandStart

router = Router()


@router.message(CommandStart())
async def on_start(message: types.Message) -> None:
    await message.answer("Hello! I'm git-chameleon. Send /help to see what I can do.")


@router.message(Command("help"))
async def on_help(message: types.Message) -> None:
    text = (
        "I help you connect Telegram to GitHub.\n\n"
        "Available commands:\n"
        "/start - start the bot\n"
        "/help - show this help"
    )
    await message.answer(text)
