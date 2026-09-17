"""Telegram handlers for the bot."""

from aiogram import Router

from git_chameleon.handlers import commands, startup

main_router = Router()
main_router.include_router(commands.router)
main_router.include_router(startup.router)

__all__ = ["main_router", "commands", "startup"]
