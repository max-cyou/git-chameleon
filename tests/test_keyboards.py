from git_chameleon.handlers.keyboards import (
    REPOS_PER_PAGE,
    MenuCB,
    RepoCB,
    back_to_menu,
    back_to_settings,
    confirm_unlink,
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
    assert all_texts(markup) == ["Repositories", "Unlink"]
    assert all_callback_data(markup) == ["menu:repos", "menu:unlink"]
    assert all_texts(settings_menu(Strings("ru"))) == ["Репозитории", "Отвязать"]


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
    assert keyboard[4][0].callback_data == "menu:settings"


def test_repos_keyboard_clamps_nav_on_last_page() -> None:
    rows = [(11, "octocat/alpha", False)]
    markup = repos_keyboard(Strings("en"), rows, page=1, pages=2)
    nav = [btn.callback_data for btn in markup.inline_keyboard[1]]
    assert nav == ["repo:page:0:0", "repo:page:1:0", "repo:page:1:0"]


def test_repos_per_page_is_five() -> None:
    assert REPOS_PER_PAGE == 5


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
