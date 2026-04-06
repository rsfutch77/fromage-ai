"""Baseline statistical analysis of game results.

Implements BaselineStats: win rates by board, mean scores by category,
percentiles, and a rich-formatted summary table.

See requirements section 8.2.
"""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING

from rich.table import Table

if TYPE_CHECKING:
    from src.game.simulation import GameResult

_CATEGORIES = (
    "festival",
    "villes",
    "fromagerie",
    "bistro",
    "orders",
    "fruit",
    "headquarters",
    "unused_resources",
    "total",
)

_PERCENTILE_MARKS = (10, 25, 50, 75, 90)


class BaselineStats:
    """Aggregate statistics over a batch of completed games.

    Parameters
    ----------
    results:
        List of GameResult objects, typically from ``run_batch()``.

    Attributes
    ----------
    win_rate_by_board : dict[int, float]
        Fraction of games won by each board/player position (0–3).
    mean_score_by_category : dict[str, float]
        Mean points per scoring category across all player-games.
    score_std : float
        Standard deviation of total scores across all player-games.
    mean_turns : float
        Mean number of turns per game.
    score_percentiles : dict[int, float]
        10/25/50/75/90th percentiles of total scores.
    """

    def __init__(self, results: list["GameResult"]) -> None:
        if not results:
            raise ValueError("results must be non-empty")
        self._results = results
        self._compute()

    # ------------------------------------------------------------------
    # Internal computation
    # ------------------------------------------------------------------

    def _compute(self) -> None:
        n_games = len(self._results)

        # Win counts per board id (player_id == board_id in default setup)
        wins: dict[int, int] = {i: 0 for i in range(4)}
        category_sums: dict[str, float] = {c: 0.0 for c in _CATEGORIES}
        totals: list[float] = []

        for result in self._results:
            winner_set = set(result.winner_ids)
            for sb in result.scores:
                pid = sb.player_id
                if pid in winner_set:
                    wins[pid] = wins.get(pid, 0) + 1
                for cat in _CATEGORIES:
                    category_sums[cat] += getattr(sb, cat)
                totals.append(float(sb.total))

        n_player_games = len(totals)  # == n_games * 4

        self.win_rate_by_board: dict[int, float] = {
            pid: wins[pid] / n_games for pid in range(4)
        }
        self.mean_score_by_category: dict[str, float] = {
            cat: category_sums[cat] / n_player_games for cat in _CATEGORIES
        }
        self.score_std: float = statistics.pstdev(totals)
        self.mean_turns: float = sum(r.total_turns for r in self._results) / n_games

        sorted_totals = sorted(totals)
        self.score_percentiles: dict[int, float] = {
            p: _percentile(sorted_totals, p) for p in _PERCENTILE_MARKS
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def summary_table(self) -> str:
        """Return a rich-formatted summary as a string."""
        from io import StringIO
        from rich.console import Console

        buf = StringIO()
        console = Console(file=buf, highlight=False)

        # --- Win rates ---
        win_table = Table(title="Win Rate by Board Position", show_lines=False)
        win_table.add_column("Board", justify="right")
        win_table.add_column("Win Rate", justify="right")
        for pid in range(4):
            win_table.add_row(str(pid), f"{self.win_rate_by_board[pid]:.3f}")
        console.print(win_table)

        # --- Mean scores by category ---
        cat_table = Table(title="Mean Score by Category", show_lines=False)
        cat_table.add_column("Category", justify="left")
        cat_table.add_column("Mean Points", justify="right")
        for cat in _CATEGORIES:
            cat_table.add_row(cat, f"{self.mean_score_by_category[cat]:.2f}")
        console.print(cat_table)

        # --- Summary stats ---
        misc_table = Table(title="Overall Statistics", show_lines=False)
        misc_table.add_column("Statistic", justify="left")
        misc_table.add_column("Value", justify="right")
        misc_table.add_row("Mean turns / game", f"{self.mean_turns:.1f}")
        misc_table.add_row("Score std dev", f"{self.score_std:.2f}")
        for p in _PERCENTILE_MARKS:
            misc_table.add_row(f"P{p} total score", f"{self.score_percentiles[p]:.1f}")
        console.print(misc_table)

        return buf.getvalue()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _percentile(sorted_data: list[float], p: int) -> float:
    """Return the p-th percentile of a pre-sorted list using linear interpolation."""
    n = len(sorted_data)
    if n == 1:
        return sorted_data[0]
    idx = (p / 100) * (n - 1)
    lo = int(idx)
    hi = lo + 1
    if hi >= n:
        return sorted_data[-1]
    frac = idx - lo
    return sorted_data[lo] + frac * (sorted_data[hi] - sorted_data[lo])
