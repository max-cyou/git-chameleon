from aiogram import types

from git_chameleon.i18n import DEFAULT_LOCALE, STRINGS, I18nMiddleware, Strings, normalize_locale
from git_chameleon.storage import Storage


def test_normalize_locale() -> None:
    assert normalize_locale(None) == "en"
    assert normalize_locale("") == "en"
    assert normalize_locale("ru") == "ru"
    assert normalize_locale("ru-RU") == "ru"
    assert normalize_locale("en_US") == "en"
    assert normalize_locale("de") == "en"
    assert normalize_locale("DE") == "en"


def test_strings_lookup_and_format() -> None:
    assert Strings("en").get("btn.settings") == "Settings"
    assert Strings("ru").get("btn.settings") == "Настройки"
    assert Strings("de").get("btn.settings") == "Settings"
    assert (
        Strings("en").get("link.linked", login="octocat", installation_id=7)
        == "Linked @octocat (installation #7)."
    )
    assert (
        Strings("ru").get("link.linked", login="octocat", installation_id=7)
        == "Привязано: @octocat (установка #7)."
    )


def test_strings_missing_key() -> None:
    assert Strings("ru").get("no.such.key") == "no.such.key"
    assert Strings("en").get("no.such.key") == "no.such.key"


def test_locales_have_same_keys() -> None:
    assert set(STRINGS[DEFAULT_LOCALE]) == set(STRINGS["ru"])


def test_titles_are_bold() -> None:
    for locale in ("en", "ru"):
        assert STRINGS[locale]["menu.title"].startswith("<b>")
        assert STRINGS[locale]["repos.title"].startswith("<b>")
        assert STRINGS[locale]["digest.title"].startswith("<b>")
        assert STRINGS[locale]["settings.text"].startswith("<b>")
        assert STRINGS[locale]["start.greeting"].startswith("<b>")


def test_pr_title_is_escaped() -> None:
    from git_chameleon.scheduler import _fmt_pr

    line = _fmt_pr("octocat", "repo", 7, "fix a < b & c > d", False, "[draft]")
    assert "&lt;" in line and "&gt;" in line and "&amp;" in line
    assert "<b>" not in line


def test_strings_from_none_locale_uses_default() -> None:
    assert Strings(None).locale == DEFAULT_LOCALE
    assert Strings("xx").locale == DEFAULT_LOCALE


async def test_middleware_injects_strings_and_stores_locale(tmp_path) -> None:
    storage = Storage(str(tmp_path / "test.db"))
    middleware = I18nMiddleware()
    captured: dict[str, object] = {}

    async def handler(event, data):
        captured["strings"] = data["strings"]

    user = types.User(id=5, is_bot=False, first_name="Max", language_code="ru-RU")
    chat = types.Chat(id=5, type="private")
    await middleware(
        handler,
        types.Update(update_id=1),
        {"event_from_user": user, "event_chat": chat, "storage": storage},
    )

    strings = captured["strings"]
    assert isinstance(strings, Strings)
    assert strings.locale == "ru"
    assert storage.get_link(5).locale == "ru"
    storage.close()


async def test_middleware_defaults_without_user() -> None:
    middleware = I18nMiddleware()
    captured: dict[str, object] = {}

    async def handler(event, data):
        captured["strings"] = data["strings"]

    await middleware(handler, types.Update(update_id=1), {})
    assert isinstance(captured["strings"], Strings)
    assert captured["strings"].locale == "en"


def test_storage_locale_roundtrip(tmp_path) -> None:
    storage = Storage(str(tmp_path / "test.db"))
    storage.ensure_user(1, 100)
    assert storage.get_link(1).locale is None

    storage.set_locale(1, 100, "ru")
    link = storage.get_link(1)
    assert link.locale == "ru"
    assert link.chat_id == 100
    storage.close()


def test_storage_migration_adds_locale_column(tmp_path) -> None:
    import sqlite3

    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE user_links (
            user_id INTEGER PRIMARY KEY,
            chat_id INTEGER NOT NULL,
            github_login TEXT UNIQUE,
            installation_id INTEGER
        )
        """
    )
    conn.execute(
        "INSERT INTO user_links (user_id, chat_id, github_login, installation_id)"
        " VALUES (1, 100, 'octocat', 7)"
    )
    conn.commit()
    conn.close()

    storage = Storage(str(db_path))
    link = storage.get_link(1)
    assert link is not None
    assert link.github_login == "octocat"
    assert link.installation_id == 7
    assert link.locale is None

    storage.set_locale(1, 100, "ru")
    assert storage.get_link(1).locale == "ru"
    storage.close()


def test_repo_selection_roundtrip(tmp_path) -> None:
    storage = Storage(str(tmp_path / "test.db"))
    storage.ensure_user(1, 100)

    assert storage.selected_repo_ids(1) == set()
    assert storage.toggle_repo(1, 11) is True
    assert storage.toggle_repo(1, 22) is True
    assert storage.selected_repo_ids(1) == {11, 22}
    assert storage.toggle_repo(1, 11) is False
    assert storage.selected_repo_ids(1) == {22}
    storage.close()


def test_clear_link_removes_repo_selection(tmp_path) -> None:
    storage = Storage(str(tmp_path / "test.db"))
    storage.ensure_user(1, 100)
    storage.set_github_login(1, "octocat")
    storage.toggle_repo(1, 11)

    storage.clear_link(1)
    assert storage.selected_repo_ids(1) == set()
    storage.close()


def test_llm_flag_toggles(tmp_path) -> None:
    storage = Storage(str(tmp_path / "test.db"))
    storage.ensure_user(1, 100)

    link = storage.get_link(1)
    assert link is not None
    assert link.llm_chat is False
    assert link.llm_review is False

    assert storage.toggle_llm_chat(1) is True
    assert storage.toggle_llm_review(1) is True
    link = storage.get_link(1)
    assert link is not None
    assert link.llm_chat is True
    assert link.llm_review is True

    assert storage.toggle_llm_chat(1) is False
    link = storage.get_link(1)
    assert link is not None
    assert link.llm_chat is False
    assert link.llm_review is True
    storage.close()


def test_storage_migration_adds_llm_columns(tmp_path) -> None:
    import sqlite3

    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE user_links (
            user_id INTEGER PRIMARY KEY,
            chat_id INTEGER NOT NULL,
            github_login TEXT UNIQUE,
            installation_id INTEGER
        )
        """
    )
    conn.execute(
        "INSERT INTO user_links (user_id, chat_id, github_login, installation_id)"
        " VALUES (1, 100, 'octocat', 7)"
    )
    conn.commit()
    conn.close()

    storage = Storage(str(db_path))
    link = storage.get_link(1)
    assert link is not None
    assert link.llm_chat is False
    assert link.llm_review is False
    storage.close()


def test_group_tracking_and_toggles(tmp_path) -> None:
    storage = Storage(str(tmp_path / "test.db"))
    storage.upsert_group(-100, "Dev Team", 1)
    storage.upsert_group(-100, "Dev Team Renamed", 2)
    storage.upsert_group(-200, "Work Chat", 1)

    groups = storage.groups_for_user(1)
    assert [g.title for g in groups] == ["Dev Team Renamed", "Work Chat"]
    assert all(g.mention_prs for g in groups)
    assert len(storage.groups_for_user(2)) == 1

    assert storage.toggle_group_mentions(-100) is False
    assert storage.digest_group_ids(1) == [-200]
    assert storage.toggle_group_mentions(-100) is True
    assert sorted(storage.digest_group_ids(1)) == [-200, -100]
    storage.close()


def test_llm_style_roundtrip(tmp_path) -> None:
    storage = Storage(str(tmp_path / "test.db"))
    storage.ensure_user(1, 100)
    assert storage.get_link(1).llm_style == "default"

    storage.set_llm_style(1, "rustic")
    assert storage.get_link(1).llm_style == "rustic"
    storage.set_llm_style(1, "default")
    assert storage.get_link(1).llm_style == "default"
    storage.close()


def test_sent_pr_keys_roundtrip(tmp_path) -> None:
    storage = Storage(str(tmp_path / "test.db"))
    assert storage.known_pr_keys(1) == set()

    storage.add_pr_keys(1, {"o/r#1", "o/r#2"})
    assert storage.known_pr_keys(1) == {"o/r#1", "o/r#2"}
    assert storage.known_pr_keys(2) == set()

    storage.add_pr_keys(1, {"o/r#1"})  # idempotent
    assert len(storage.known_pr_keys(1)) == 2
    storage.close()
