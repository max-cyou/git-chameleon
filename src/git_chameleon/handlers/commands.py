from __future__ import annotations

from aiogram import Router, types
from aiogram.filters import Command, CommandStart

from git_chameleon.handlers.keyboards import main_menu
from git_chameleon.i18n import Strings

router = Router()


@router.message(CommandStart())
async def on_start(message: types.Message, strings: Strings) -> None:
    await message.answer(
        strings.get("start.greeting"),
        reply_markup=main_menu(strings),
    )


@router.message(Command("help"))
async def on_help(message: types.Message, strings: Strings) -> None:
    await message.answer(strings.get("help.text"), reply_markup=main_menu(strings))
