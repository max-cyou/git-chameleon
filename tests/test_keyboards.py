from git_chameleon.handlers.keyboards import (
    REPOS_PER_PAGE,
    MenuCB,
    RepoCB,
    back_to_menu,
    back_to_settings,
    confirm_unlink,
    groups_keyboard,
    llm_menu,
    llm_screen_text,
    main_menu,
    menu_text,
    repos_keyboard,
    settings_menu,
    status_text,
)
from git_chameleon.i18n import Strings
from git_chameleon.storage import UserLink


def all_callback_data(markup) -> list[str]:
    return [btn.callback_data for row in markup.inline_keyboard for btn in row]


def all_texts(markup) -> list[str]:
    return [btn.text for row in markup.inline_keyboard for btn in row]


def test_main_menu_actions() -> None:
    markup = main_menu(Strings("en"))
    assert all_texts(markup) == ["Linking", "Settings"]
    assert all_callback_data(markup) == ["menu:link", "menu:settings"]


def test_main_menu_localized_labels() -> None:
    assert all_texts(main_menu(Strings("ru"))) == ["Привязка", "Настройки"]


def test_settings_menu_actions() -> None:
    markup = settings_menu(Strings("en"))
    assert all_texts(markup) == [
        "Repositories",
        "Groups",
        "LLM",
        "Unlink",
        "Back to menu",
    ]
    assert all_callback_data(markup) == [
        "menu:repos",
        "menu:groups",
        "menu:llm",
        "menu:unlink",
        "menu:menu",
    ]
    assert all_texts(settings_menu(Strings("ru"))) == [
        "Репозитории",
        "Группы",
        "LLM",
        "Отвязать",
        "В меню",
    ]


def test_main_menu_add_group_button() -> None:
    markup = main_menu(Strings("en"), add_group_url="https://t.me/bot?startgroup=add")
    texts = all_texts(markup)
    urls = [btn.url for row in markup.inline_keyboard for btn in row]
    assert texts == ["Linking", "Settings", "Add to group"]
    assert "https://t.me/bot?startgroup=add" in urls


def test_groups_keyboard_layout() -> None:
    rows = [(-100, "Dev Team", True), (-200, "Work Chat", False)]
    markup = groups_keyboard(Strings("en"), rows, page=0, pages=1)
    keyboard = markup.inline_keyboard

    assert keyboard[0][0].text == "✅ Dev Team"
    assert keyboard[1][0].text == "Work Chat"
    assert keyboard[0][0].callback_data == "grp:toggle:0:-100"
    assert keyboard[1][0].callback_data == "grp:toggle:0:-200"

    nav = [btn.callback_data for btn in keyboard[2]]
    assert nav == ["grp:page:0:0", "grp:page:0:0", "grp:page:0:0"]
    back_row = [btn.callback_data for btn in keyboard[3]]
    assert back_row == ["menu:settings", "menu:menu"]


def test_confirm_unlink_actions() -> None:
    data = all_callback_data(confirm_unlink(Strings("en")))
    assert data == ["menu:unlink_confirm", "menu:settings"]


def test_back_buttons() -> None:
    assert all_callback_data(back_to_menu(Strings("en"))) == ["menu:menu"]
    assert all_callback_data(back_to_settings(Strings("en"))) == ["menu:settings"]


def test_menu_cb_pack() -> None:
    assert MenuCB(action="link").pack() == "menu:link"


def test_repo_cb_pack() -> None:
    assert RepoCB(action="toggle", page=2, repo_id=123).pack() == "repo:toggle:2:123"
    assert RepoCB(action="page", page=1, repo_id=0).pack() == "repo:page:1:0"


def test_repos_keyboard_layout() -> None:
    rows = [
        (11, "octocat/alpha", False),
        (22, "octocat/beta", True),
        (33, "octocat/gamma", False),
    ]
    markup = repos_keyboard(Strings("en"), rows, page=0, pages=2)
    keyboard = markup.inline_keyboard

    assert len(keyboard) == 5  # 3 repo rows + nav row + back row
    assert keyboard[0][0].text == "octocat/alpha"
    assert keyboard[1][0].text == "✅ octocat/beta"
    assert keyboard[0][0].callback_data == "repo:toggle:0:11"
    assert keyboard[1][0].callback_data == "repo:toggle:0:22"

    nav = [btn.callback_data for btn in keyboard[3]]
    assert nav == ["repo:page:0:0", "repo:page:0:0", "repo:page:1:0"]
    assert [btn.text for btn in keyboard[3]] == ["◀", "1/2", "▶"]

    back_row = [btn.callback_data for btn in keyboard[4]]
    assert back_row == ["menu:settings", "menu:menu"]
    assert [btn.text for btn in keyboard[4]] == ["Back to settings", "Back to menu"]


def test_repos_keyboard_clamps_nav_on_last_page() -> None:
    rows = [(11, "octocat/alpha", False)]
    markup = repos_keyboard(Strings("en"), rows, page=1, pages=2)
    nav = [btn.callback_data for btn in markup.inline_keyboard[1]]
    assert nav == ["repo:page:0:0", "repo:page:1:0", "repo:page:1:0"]
    back_row = [btn.callback_data for btn in markup.inline_keyboard[2]]
    assert back_row == ["menu:settings", "menu:menu"]


def test_repos_per_page_is_five() -> None:
    assert REPOS_PER_PAGE == 5


def test_llm_menu_toggles() -> None:
    off = UserLink(user_id=1, chat_id=1)
    markup = llm_menu(Strings("en"), off, provider_configured=False)
    assert all_texts(markup) == ["Chat", "Review", "Back to settings", "Back to menu"]
    assert all_callback_data(markup) == [
        "menu:llm_chat",
        "menu:llm_review",
        "menu:settings",
        "menu:menu",
    ]

    on = UserLink(user_id=1, chat_id=1, llm_chat=True, llm_review=True)
    assert all_texts(llm_menu(Strings("ru"), on, provider_configured=True)) == [
        "✅ Чат",
        "✅ Ревью",
        "К настройкам",
        "В меню",
    ]


def test_llm_screen_text_states() -> None:
    configured = llm_screen_text(Strings("en"), True, "gpt-4o-mini")
    assert configured.startswith("<b>")
    assert "gpt-4o-mini" in configured

    unconfigured = llm_screen_text(Strings("ru"), False)
    assert "не настроен" in unconfigured


def test_texts_without_link() -> None:
    assert "Not linked" in status_text(Strings("en"), None)
    assert "Not linked" in menu_text(Strings("en"), None)
    assert "не привязан" in menu_text(Strings("ru"), None).lower()


def test_texts_with_installation() -> None:
    link = UserLink(user_id=1, chat_id=1, github_login="octocat", installation_id=42)
    assert status_text(Strings("en"), link) == "GitHub: @octocat\nInstallation: #42"
    assert status_text(Strings("ru"), link) == "GitHub: @octocat\nУстановка: #42"
    assert "@octocat" in menu_text(Strings("en"), link)
    assert "#42" in menu_text(Strings("ru"), link)


def test_texts_login_without_installation() -> None:
    link = UserLink(user_id=1, chat_id=1, github_login="octocat")
    assert "No installation" in status_text(Strings("en"), link)
    assert "no installation" in menu_text(Strings("en"), link).lower()
    assert "не найдена" in menu_text(Strings("ru"), link)
