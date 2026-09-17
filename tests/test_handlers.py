import asyncio
from types import SimpleNamespace

from aiogram.types import Chat, Message, User

from git_chameleon.handlers.github import _addresses_bot


def _fake_bot(username: str | None):
    me = SimpleNamespace(username=username)
    return SimpleNamespace(me=lambda: asyncio.sleep(0, result=me))


def _message(text: str) -> Message:
    return Message(
        message_id=1,
        date=1740000000,
        chat=Chat(id=-100, type="supergroup"),
        from_user=User(id=1, is_bot=False, first_name="Max"),
        text=text,
    )


async def test_addresses_bot_by_mention() -> None:
    assert await _addresses_bot(_message("@git_ch_bot привет"), _fake_bot("git_ch_bot"))
    assert await _addresses_bot(_message("ЭЙ, @GIT_CH_BOT"), _fake_bot("git_ch_bot"))


async def test_addresses_bot_by_trigger_words() -> None:
    bot = _fake_bot("git_ch_bot")
    assert await _addresses_bot(_message("юз, глянь PR"), bot)
    assert await _addresses_bot(_message("хамелеон, привет"), bot)
    assert await _addresses_bot(_message("Chameleon check this"), bot)


async def test_ignores_plain_group_text() -> None:
    bot = _fake_bot("git_ch_bot")
    assert not await _addresses_bot(_message("просто болтовня"), bot)
    assert not await _addresses_bot(_message("как дела?"), bot)


async def test_no_username_still_triggers_on_words() -> None:
    bot = _fake_bot(None)
    assert await _addresses_bot(_message("хамелеон!"), bot)
    assert not await _addresses_bot(_message("привет"), bot)
