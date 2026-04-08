"""SQLite storage for game results.

Implements ResultsDB with store_result() and fetch_scores().
Schema: games table + scores table (one row per player per game),
        placed_cheese table (age counts per player per game),
        villes_control table (region controller per game).

See requirements sections 8.1 and 8.3.1–8.3.2.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.game.simulation import GameResult

logger = logging.getLogger(__name__)

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
    score_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id                INTEGER NOT NULL REFERENCES games(game_id),
    player_id              INTEGER NOT NULL,
    board_id               INTEGER NOT NULL,
    festival               INTEGER NOT NULL,
    villes                 INTEGER NOT NULL,
    fromagerie             INTEGER NOT NULL,
    bistro                 INTEGER NOT NULL,
    orders                 INTEGER NOT NULL,
    fruit                  INTEGER NOT NULL,
    headquarters           INTEGER NOT NULL,
    unused_resources       INTEGER NOT NULL,
    total                  INTEGER NOT NULL,
    is_winner              INTEGER NOT NULL,
    structures_unlocked    TEXT,
    fruit_spent_on_fruited INTEGER,
    fruit_spent_on_jam     INTEGER,
    milking_parlours_used  INTEGER
)
"""

_CREATE_PLACED_CHEESE = """
CREATE TABLE IF NOT EXISTS placed_cheese (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id   INTEGER NOT NULL REFERENCES games(game_id),
    player_id INTEGER NOT NULL,
    age       TEXT    NOT NULL,
    count     INTEGER NOT NULL
)
"""

_CREATE_VILLES_CONTROL = """
CREATE TABLE IF NOT EXISTS villes_control (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id             INTEGER NOT NULL REFERENCES games(game_id),
    region              TEXT    NOT NULL,
    controlling_player  INTEGER NOT NULL
)
"""

_CREATE_TOKEN_ASSIGNMENTS = """
CREATE TABLE IF NOT EXISTS token_assignments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id     INTEGER NOT NULL REFERENCES games(game_id),
    region_name TEXT    NOT NULL,
    win_value   INTEGER NOT NULL
)
"""

# Safe migrations for existing DBs (new columns only; try/except swallows
# "duplicate column name" errors from sqlite3).
_MIGRATE_SCORES = [
    "ALTER TABLE scores ADD COLUMN structures_unlocked    TEXT",
    "ALTER TABLE scores ADD COLUMN fruit_spent_on_fruited INTEGER",
    "ALTER TABLE scores ADD COLUMN fruit_spent_on_jam     INTEGER",
    "ALTER TABLE scores ADD COLUMN milking_parlours_used  INTEGER",
]


class ResultsDB:
    """Persistent SQLite store for batch game results.

    The database and schema are created automatically on first use.
    Existing databases are migrated to include the new columns.

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
            conn.execute(_CREATE_PLACED_CHEESE)
            conn.execute(_CREATE_VILLES_CONTROL)
            conn.execute(_CREATE_TOKEN_ASSIGNMENTS)
            for stmt in _MIGRATE_SCORES:
                try:
                    conn.execute(stmt)
                except sqlite3.OperationalError:
                    pass  # column already exists

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def store_result(self, result: "GameResult", agent_config: str) -> None:
        """Insert one game row and four score rows in a single transaction."""
        timestamp = datetime.now(timezone.utc).isoformat()
        player_by_id = {p.player_id: p for p in result.final_state.players}
        winner_set = set(result.winner_ids)

        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO games (seed, total_turns, timestamp, agent_config)"
                " VALUES (?, ?, ?, ?)",
                (result.seed, result.total_turns, timestamp, agent_config),
            )
            game_id = cur.lastrowid

            for sb in result.scores:
                player = player_by_id[sb.player_id]
                parlours_count = sum(1 for x in player.milking_parlours_used if x > 0)
                conn.execute(
                    "INSERT INTO scores"
                    " (game_id, player_id, board_id,"
                    "  festival, villes, fromagerie, bistro,"
                    "  orders, fruit, headquarters, unused_resources,"
                    "  total, is_winner,"
                    "  structures_unlocked, fruit_spent_on_fruited,"
                    "  fruit_spent_on_jam, milking_parlours_used)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        game_id,
                        sb.player_id,
                        player.board_id,
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
                        json.dumps(player.structures_unlocked),
                        player.fruit_spent_on_fruited,
                        player.fruit_spent_on_jam,
                        parlours_count,
                    ),
                )

            for player in result.final_state.players:
                age_counts: Counter[str] = Counter(
                    pc.age.name for pc in player.cheese_tokens_on_board
                )
                for age_name, count in age_counts.items():
                    conn.execute(
                        "INSERT INTO placed_cheese (game_id, player_id, age, count)"
                        " VALUES (?, ?, ?, ?)",
                        (game_id, player.player_id, age_name, count),
                    )

            for region, holder in result.final_state.villes_customer_token_holders.items():
                conn.execute(
                    "INSERT INTO villes_control (game_id, region, controlling_player)"
                    " VALUES (?, ?, ?)",
                    (game_id, region, holder if holder is not None else -1),
                )

            for token in result.final_state.customer_tokens:
                conn.execute(
                    "INSERT INTO token_assignments"
                    " (game_id, region_name, win_value)"
                    " VALUES (?, ?, ?)",
                    (game_id, token.region_name, token.win_value),
                )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def fetch_scores(self, agent_config: str | None = None) -> list[dict]:
        """Return all score rows joined with their game metadata.

        If *agent_config* is given, only rows from games with that config
        are returned.  Includes all extended columns added in Milestone 6.
        """
        sql = (
            "SELECT g.game_id, g.seed, g.total_turns, g.timestamp,"
            "       g.agent_config,"
            "       s.score_id, s.player_id, s.board_id,"
            "       s.festival, s.villes, s.fromagerie, s.bistro,"
            "       s.orders, s.fruit, s.headquarters, s.unused_resources,"
            "       s.total, s.is_winner,"
            "       s.structures_unlocked, s.fruit_spent_on_fruited,"
            "       s.fruit_spent_on_jam, s.milking_parlours_used"
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

    def fetch_placed_cheese(self, agent_config: str | None = None) -> list[dict]:
        """Return placed_cheese rows joined with game metadata and is_winner."""
        sql = (
            "SELECT pc.game_id, pc.player_id, pc.age, pc.count,"
            "       s.is_winner"
            " FROM placed_cheese pc"
            " JOIN games g ON g.game_id = pc.game_id"
            " JOIN scores s ON s.game_id = pc.game_id AND s.player_id = pc.player_id"
        )
        params: tuple = ()
        if agent_config is not None:
            sql += " WHERE g.agent_config = ?"
            params = (agent_config,)

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()

        return [dict(row) for row in rows]

    def fetch_villes_control(self, agent_config: str | None = None) -> list[dict]:
        """Return villes_control rows joined with winner information."""
        sql = (
            "SELECT vc.game_id, vc.region, vc.controlling_player,"
            "       CASE WHEN vc.controlling_player = -1 THEN 0"
            "            ELSE s.is_winner END AS controller_is_winner"
            " FROM villes_control vc"
            " JOIN games g ON g.game_id = vc.game_id"
            " LEFT JOIN scores s"
            "        ON s.game_id = vc.game_id"
            "       AND s.player_id = vc.controlling_player"
        )
        params: tuple = ()
        if agent_config is not None:
            sql += " WHERE g.agent_config = ?"
            params = (agent_config,)

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()

        return [dict(row) for row in rows]

    def fetch_token_assignments(self, agent_config: str | None = None) -> list[dict]:
        """Return token_assignments rows joined with villes_control and winner info.

        Each row contains: game_id, region_name, win_value, controlling_player,
        controller_is_winner.
        """
        sql = (
            "SELECT ta.game_id, ta.region_name, ta.win_value,"
            "       vc.controlling_player,"
            "       CASE WHEN vc.controlling_player = -1 THEN 0"
            "            ELSE s.is_winner END AS controller_is_winner"
            " FROM token_assignments ta"
            " JOIN games g ON g.game_id = ta.game_id"
            " JOIN villes_control vc"
            "   ON vc.game_id = ta.game_id AND vc.region = ta.region_name"
            " LEFT JOIN scores s"
            "        ON s.game_id = ta.game_id"
            "       AND s.player_id = vc.controlling_player"
        )
        params: tuple = ()
        if agent_config is not None:
            sql += " WHERE g.agent_config = ?"
            params = (agent_config,)

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()

        return [dict(row) for row in rows]

    def game_count(self, agent_config: str | None = None) -> int:
        """Return the number of games stored, optionally filtered by config."""
        sql = "SELECT COUNT(*) FROM games"
        params: tuple = ()
        if agent_config is not None:
            sql += " WHERE agent_config = ?"
            params = (agent_config,)
        with self._connect() as conn:
            return conn.execute(sql, params).fetchone()[0]
