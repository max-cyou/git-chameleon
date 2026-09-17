from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UserLink:
    user_id: int
    chat_id: int
    github_login: str | None = None
    installation_id: int | None = None


class Storage:
    """SQLite store for Telegram user <-> GitHub installation mappings."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path))
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_links (
                user_id INTEGER PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                github_login TEXT UNIQUE,
                installation_id INTEGER
            )
            """
        )
        self._conn.commit()

    def _row_to_link(self, row: tuple) -> UserLink:
        user_id, chat_id, github_login, installation_id = row
        return UserLink(
            user_id=user_id,
            chat_id=chat_id,
            github_login=github_login,
            installation_id=installation_id,
        )

    def ensure_user(self, user_id: int, chat_id: int) -> UserLink:
        self._conn.execute(
            "INSERT OR IGNORE INTO user_links (user_id, chat_id) VALUES (?, ?)",
            (user_id, chat_id),
        )
        self._conn.commit()
        link = self.get_link(user_id)
        assert link is not None
        return link

    def set_github_login(self, user_id: int, github_login: str) -> None:
        self._conn.execute(
            "UPDATE user_links SET github_login = ? WHERE user_id = ?",
            (github_login, user_id),
        )
        self._conn.commit()

    def set_installation(self, user_id: int, installation_id: int) -> None:
        self._conn.execute(
            "UPDATE user_links SET installation_id = ? WHERE user_id = ?",
            (installation_id, user_id),
        )
        self._conn.commit()

    def get_link(self, user_id: int) -> UserLink | None:
        row = self._conn.execute(
            "SELECT user_id, chat_id, github_login, installation_id FROM user_links WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return self._row_to_link(row) if row else None

    def clear_link(self, user_id: int) -> None:
        self._conn.execute(
            "UPDATE user_links SET github_login = NULL, installation_id = NULL WHERE user_id = ?",
            (user_id,),
        )
        self._conn.commit()

    def all_links(self) -> list[UserLink]:
        rows = self._conn.execute(
            "SELECT user_id, chat_id, github_login, installation_id FROM user_links"
        ).fetchall()
        links: list[UserLink] = []
        for row in rows:
            link = self._row_to_link(row)
            if link.github_login:
                links.append(link)
        return links

    def find_by_login(self, github_login: str) -> UserLink | None:
        row = self._conn.execute(
            "SELECT user_id, chat_id, github_login, installation_id FROM user_links WHERE lower(github_login) = lower(?)",
            (github_login,),
        ).fetchone()
        return self._row_to_link(row) if row else None

    def close(self) -> None:
        self._conn.close()
