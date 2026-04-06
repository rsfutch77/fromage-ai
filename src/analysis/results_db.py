"""SQLite storage for game results.

Implements ResultsDB with store_result() and fetch_scores().
Schema: games table + scores table (one row per player per game).

See requirements section 8.1.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.game.simulation import GameResult

_DEFAULT_DB = Path("data/results.db")

_CREATE_GAMES = """
CREATE TABLE IF NOT EXISTS games (
    game_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    seed         INTEGER,
    total_turns  INTEGER NOT NULL,
    timestamp    TEXT    NOT NULL,
    agent_config TEXT    NOT NULL
)
"""

_CREATE_SCORES = """
CREATE TABLE IF NOT EXISTS scores (
    score_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id          INTEGER NOT NULL REFERENCES games(game_id),
    player_id        INTEGER NOT NULL,
    board_id         INTEGER NOT NULL,
    festival         INTEGER NOT NULL,
    villes           INTEGER NOT NULL,
    fromagerie       INTEGER NOT NULL,
    bistro           INTEGER NOT NULL,
    orders           INTEGER NOT NULL,
    fruit            INTEGER NOT NULL,
    headquarters     INTEGER NOT NULL,
    unused_resources INTEGER NOT NULL,
    total            INTEGER NOT NULL,
    is_winner        INTEGER NOT NULL
)
"""


class ResultsDB:
    """Persistent SQLite store for batch game results.

    The database and schema are created automatically on first use.

    Parameters
    ----------
    db_path:
        Path to the SQLite file.  Defaults to ``data/results.db``.
    """

    def __init__(self, db_path: Path = _DEFAULT_DB) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(_CREATE_GAMES)
            conn.execute(_CREATE_SCORES)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def store_result(self, result: "GameResult", agent_config: str) -> None:
        """Insert one game row and four score rows in a single transaction."""
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO games (seed, total_turns, timestamp, agent_config)"
                " VALUES (?, ?, ?, ?)",
                (result.seed, result.total_turns, timestamp, agent_config),
            )
            game_id = cur.lastrowid
            winner_set = set(result.winner_ids)
            for sb in result.scores:
                conn.execute(
                    "INSERT INTO scores"
                    " (game_id, player_id, board_id,"
                    "  festival, villes, fromagerie, bistro,"
                    "  orders, fruit, headquarters, unused_resources,"
                    "  total, is_winner)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        game_id,
                        sb.player_id,
                        sb.player_id,  # board_id == player_id in default setup
                        sb.festival,
                        sb.villes,
                        sb.fromagerie,
                        sb.bistro,
                        sb.orders,
                        sb.fruit,
                        sb.headquarters,
                        sb.unused_resources,
                        sb.total,
                        1 if sb.player_id in winner_set else 0,
                    ),
                )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def fetch_scores(self, agent_config: str | None = None) -> list[dict]:
        """Return all score rows joined with their game metadata.

        If *agent_config* is given, only rows from games with that config
        are returned.
        """
        sql = (
            "SELECT g.game_id, g.seed, g.total_turns, g.timestamp,"
            "       g.agent_config,"
            "       s.score_id, s.player_id, s.board_id,"
            "       s.festival, s.villes, s.fromagerie, s.bistro,"
            "       s.orders, s.fruit, s.headquarters, s.unused_resources,"
            "       s.total, s.is_winner"
            " FROM scores s"
            " JOIN games g ON g.game_id = s.game_id"
        )
        params: tuple = ()
        if agent_config is not None:
            sql += " WHERE g.agent_config = ?"
            params = (agent_config,)

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()

        return [dict(row) for row in rows]
