from git_chameleon.handlers.keyboards import (
    MenuCB,
    back_to_menu,
    confirm_unlink,
    main_menu,
    menu_text,
    status_text,
)
from git_chameleon.i18n import Strings
from git_chameleon.storage import UserLink


def all_callback_data(markup) -> list[str]:
    return [btn.callback_data for row in markup.inline_keyboard for btn in row]


def test_main_menu_actions() -> None:
    data = all_callback_data(main_menu(Strings("en")))
    assert "menu:status" in data
    assert "menu:sync" in data
    assert "menu:install" in data
    assert "menu:unlink" in data


def test_main_menu_localized_labels() -> None:
    en = [btn.text for row in main_menu(Strings("en")).inline_keyboard for btn in row]
    ru = [btn.text for row in main_menu(Strings("ru")).inline_keyboard for btn in row]
    assert en == ["Status", "Sync now", "Install App", "Unlink"]
    assert ru == ["Статус", "Синхронизировать", "Установить приложение", "Отвязать"]


def test_confirm_unlink_actions() -> None:
    data = all_callback_data(confirm_unlink(Strings("en")))
    assert data == ["menu:unlink_confirm", "menu:menu"]


def test_back_to_menu_action() -> None:
    assert all_callback_data(back_to_menu(Strings("en"))) == ["menu:menu"]


def test_menu_cb_pack() -> None:
    assert MenuCB(action="sync").pack() == "menu:sync"


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
