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
    locale: str | None = None


_COLUMNS = "user_id, chat_id, github_login, installation_id, locale"


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
                installation_id INTEGER,
                locale TEXT
            )
            """
        )
        columns = {row[1] for row in self._conn.execute("PRAGMA table_info(user_links)")}
        if "locale" not in columns:
            self._conn.execute("ALTER TABLE user_links ADD COLUMN locale TEXT")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS repo_selections (
                user_id INTEGER NOT NULL,
                repo_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, repo_id)
            )
            """
        )
        self._conn.commit()

    def _row_to_link(self, row: tuple) -> UserLink:
        user_id, chat_id, github_login, installation_id, locale = row
        return UserLink(
            user_id=user_id,
            chat_id=chat_id,
            github_login=github_login,
            installation_id=installation_id,
            locale=locale,
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

    def set_locale(self, user_id: int, chat_id: int, locale: str) -> None:
        self._conn.execute(
            """
            INSERT INTO user_links (user_id, chat_id, locale) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET locale = excluded.locale
            """,
            (user_id, chat_id, locale),
        )
        self._conn.commit()

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
            f"SELECT {_COLUMNS} FROM user_links WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return self._row_to_link(row) if row else None

    def clear_link(self, user_id: int) -> None:
        self._conn.execute(
            "UPDATE user_links SET github_login = NULL, installation_id = NULL WHERE user_id = ?",
            (user_id,),
        )
        self._conn.execute("DELETE FROM repo_selections WHERE user_id = ?", (user_id,))
        self._conn.commit()

    def selected_repo_ids(self, user_id: int) -> set[int]:
        rows = self._conn.execute(
            "SELECT repo_id FROM repo_selections WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return {row[0] for row in rows}

    def toggle_repo(self, user_id: int, repo_id: int) -> bool:
        """Toggle a repo selection. Returns True if the repo is now selected."""
        existing = self._conn.execute(
            "SELECT 1 FROM repo_selections WHERE user_id = ? AND repo_id = ?",
            (user_id, repo_id),
        ).fetchone()
        if existing:
            self._conn.execute(
                "DELETE FROM repo_selections WHERE user_id = ? AND repo_id = ?",
                (user_id, repo_id),
            )
        else:
            self._conn.execute(
                "INSERT INTO repo_selections (user_id, repo_id) VALUES (?, ?)",
                (user_id, repo_id),
            )
        self._conn.commit()
        return existing is None

    def all_links(self) -> list[UserLink]:
        rows = self._conn.execute(f"SELECT {_COLUMNS} FROM user_links").fetchall()
        links: list[UserLink] = []
        for row in rows:
            link = self._row_to_link(row)
            if link.github_login:
                links.append(link)
        return links

    def find_by_login(self, github_login: str) -> UserLink | None:
        row = self._conn.execute(
            f"SELECT {_COLUMNS} FROM user_links WHERE lower(github_login) = lower(?)",
            (github_login,),
        ).fetchone()
        return self._row_to_link(row) if row else None

    def close(self) -> None:
        self._conn.close()
