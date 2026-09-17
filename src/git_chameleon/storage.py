from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Group:
    chat_id: int
    title: str
    mention_prs: bool = True


@dataclass(frozen=True)
class UserLink:
    user_id: int
    chat_id: int
    github_login: str | None = None
    installation_id: int | None = None
    locale: str | None = None
    llm_chat: bool = False
    llm_review: bool = False
    llm_style: str = "default"


_COLUMNS = "user_id, chat_id, github_login, installation_id, locale, llm_chat, llm_review, llm_style"


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
        for column in ("llm_chat", "llm_review"):
            if column not in columns:
                self._conn.execute(f"ALTER TABLE user_links ADD COLUMN {column} INTEGER DEFAULT 0")
        if "llm_style" not in columns:
            self._conn.execute(
                "ALTER TABLE user_links ADD COLUMN llm_style TEXT DEFAULT 'default'"
            )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS repo_selections (
                user_id INTEGER NOT NULL,
                repo_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, repo_id)
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS group_chats (
                chat_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                mention_prs INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS group_members (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (chat_id, user_id)
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sent_prs (
                chat_id INTEGER NOT NULL,
                pr_key TEXT NOT NULL,
                PRIMARY KEY (chat_id, pr_key)
            )
            """
        )
        self._conn.commit()

    def _row_to_link(self, row: tuple) -> UserLink:
        user_id, chat_id, github_login, installation_id, locale, llm_chat, llm_review, llm_style = row
        return UserLink(
            user_id=user_id,
            chat_id=chat_id,
            github_login=github_login,
            installation_id=installation_id,
            locale=locale,
            llm_chat=bool(llm_chat),
            llm_review=bool(llm_review),
            llm_style=llm_style or "default",
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

    def _toggle_flag(self, user_id: int, column: str) -> bool:
        """Flip a boolean user flag. Returns the new value."""
        assert column in ("llm_chat", "llm_review")
        self._conn.execute(
            f"UPDATE user_links SET {column} = 1 - {column} WHERE user_id = ?",
            (user_id,),
        )
        self._conn.commit()
        link = self.get_link(user_id)
        return bool(getattr(link, column)) if link else False

    def toggle_llm_chat(self, user_id: int) -> bool:
        return self._toggle_flag(user_id, "llm_chat")

    def toggle_llm_review(self, user_id: int) -> bool:
        return self._toggle_flag(user_id, "llm_review")

    def set_llm_style(self, user_id: int, style: str) -> None:
        assert style in ("default", "rustic")
        self._conn.execute(
            "UPDATE user_links SET llm_style = ? WHERE user_id = ?",
            (style, user_id),
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

    def upsert_group(self, chat_id: int, title: str, user_id: int) -> None:
        """Remember a group the bot is in and that the user is its member."""
        self._conn.execute(
            """
            INSERT INTO group_chats (chat_id, title, mention_prs) VALUES (?, ?, 1)
            ON CONFLICT(chat_id) DO UPDATE SET title = excluded.title
            """,
            (chat_id, title),
        )
        self._conn.execute(
            "INSERT OR IGNORE INTO group_members (chat_id, user_id) VALUES (?, ?)",
            (chat_id, user_id),
        )
        self._conn.commit()

    def groups_for_user(self, user_id: int) -> list[Group]:
        rows = self._conn.execute(
            """
            SELECT g.chat_id, g.title, g.mention_prs
            FROM group_chats g
            JOIN group_members m ON m.chat_id = g.chat_id
            WHERE m.user_id = ?
            ORDER BY lower(g.title)
            """,
            (user_id,),
        ).fetchall()
        return [
            Group(chat_id=row[0], title=row[1], mention_prs=bool(row[2]))
            for row in rows
        ]

    def toggle_group_mentions(self, chat_id: int) -> bool:
        """Flip the PR-mention flag of a group. Returns the new value."""
        self._conn.execute(
            "UPDATE group_chats SET mention_prs = 1 - mention_prs WHERE chat_id = ?",
            (chat_id,),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT mention_prs FROM group_chats WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()
        return bool(row[0]) if row else False

    def digest_group_ids(self, user_id: int) -> list[int]:
        """Groups shared with the user where PR mentions are enabled."""
        rows = self._conn.execute(
            """
            SELECT g.chat_id FROM group_chats g
            JOIN group_members m ON m.chat_id = g.chat_id
            WHERE m.user_id = ? AND g.mention_prs = 1
            """,
            (user_id,),
        ).fetchall()
        return [row[0] for row in rows]

    def known_pr_keys(self, chat_id: int) -> set[str]:
        rows = self._conn.execute(
            "SELECT pr_key FROM sent_prs WHERE chat_id = ?",
            (chat_id,),
        ).fetchall()
        return {row[0] for row in rows}

    def add_pr_keys(self, chat_id: int, pr_keys: set[str]) -> None:
        if not pr_keys:
            return
        self._conn.executemany(
            "INSERT OR IGNORE INTO sent_prs (chat_id, pr_key) VALUES (?, ?)",
            [(chat_id, key) for key in pr_keys],
        )
        self._conn.commit()
