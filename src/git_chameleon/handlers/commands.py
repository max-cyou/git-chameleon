from __future__ import annotations

from aiogram import Router, types
from aiogram.filters import Command, CommandStart

from git_chameleon.handlers.keyboards import main_menu

router = Router()


@router.message(CommandStart())
async def on_start(message: types.Message) -> None:
    await message.answer(
        "Hello! I'm git-chameleon.\n\n"
        "I watch your GitHub repositories and report open pull requests.\n"
        "Use the buttons below or /help to see the commands.",
        reply_markup=main_menu(),
    )


@router.message(Command("help"))
async def on_help(message: types.Message) -> None:
    text = (
        "I connect Telegram to your GitHub repositories.\n\n"
        "Commands:\n"
        "/menu - open the control panel\n"
        "/install - link to install the GitHub App\n"
        "/link <username> - bind your GitHub account\n"
        "/sync - refresh installations and report open PRs\n"
        "/status - show your current binding\n"
        "/unlink - remove the binding\n"
        "/help - show this help"
    )
    await message.answer(text, reply_markup=main_menu())
