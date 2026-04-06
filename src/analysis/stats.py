"""Baseline statistical analysis of game results.

Implements BaselineStats: win rates by board, mean scores by category,
percentiles, and a rich-formatted summary table.

See requirements section 8.2.
"""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING

from rich.table import Table

from src.game.types import AgeType

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
    worker_by_age : dict[AgeType, float]
        Mean worker placements per age tier across all player-games.
    parlour_by_age : dict[AgeType, float]
        Mean parlour placements per age tier across all player-games.
    winner_worker_by_age : dict[AgeType, float]
        Mean worker placements per age tier for winning player-games only.
    winner_parlour_by_age : dict[AgeType, float]
        Mean parlour placements per age tier for winning player-games only.
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

        # Win counts per board id (1-indexed, matching player_board_structures.csv)
        wins: dict[int, int] = {i: 0 for i in range(1, 5)}
        category_sums: dict[str, float] = {c: 0.0 for c in _CATEGORIES}
        totals: list[float] = []

        # Worker vs parlour placement counts per age tier
        ages = list(AgeType)
        worker_sums: dict[AgeType, float] = {a: 0.0 for a in ages}
        parlour_sums: dict[AgeType, float] = {a: 0.0 for a in ages}
        winner_worker_sums: dict[AgeType, float] = {a: 0.0 for a in ages}
        winner_parlour_sums: dict[AgeType, float] = {a: 0.0 for a in ages}
        n_winner_player_games: int = 0

        for result in self._results:
            winner_set = set(result.winner_ids)
            pid_to_board = {p.player_id: p.board_id for p in result.final_state.players}
            for sb in result.scores:
                pid = sb.player_id
                if pid in winner_set:
                    bid = pid_to_board[pid]
                    wins[bid] = wins.get(bid, 0) + 1
                for cat in _CATEGORIES:
                    category_sums[cat] += getattr(sb, cat)
                totals.append(float(sb.total))

            for player in result.final_state.players:
                pid = player.player_id
                is_winner = pid in winner_set
                if is_winner:
                    n_winner_player_games += 1
                for pc in player.cheese_tokens_on_board:
                    if pc.from_milking_parlour:
                        parlour_sums[pc.age] += 1.0
                        if is_winner:
                            winner_parlour_sums[pc.age] += 1.0
                    else:
                        worker_sums[pc.age] += 1.0
                        if is_winner:
                            winner_worker_sums[pc.age] += 1.0

        n_player_games = len(totals)  # == n_games * 4

        self.win_rate_by_board: dict[int, float] = {
            bid: wins[bid] / n_games for bid in range(1, 5)
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

        self.worker_by_age: dict[AgeType, float] = {
            a: worker_sums[a] / n_player_games for a in ages
        }
        self.parlour_by_age: dict[AgeType, float] = {
            a: parlour_sums[a] / n_player_games for a in ages
        }
        _w_denom = n_winner_player_games if n_winner_player_games > 0 else 1
        self.winner_worker_by_age: dict[AgeType, float] = {
            a: winner_worker_sums[a] / _w_denom for a in ages
        }
        self.winner_parlour_by_age: dict[AgeType, float] = {
            a: winner_parlour_sums[a] / _w_denom for a in ages
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
        for bid in sorted(self.win_rate_by_board):
            win_table.add_row(str(bid), f"{self.win_rate_by_board[bid]:.3f}")
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

        # --- Worker vs parlour by age tier ---
        wp_table = Table(title="Worker vs Parlour Placements by Age Tier (mean per player-game)", show_lines=False)
        wp_table.add_column("Age", justify="left")
        wp_table.add_column("Workers (all)", justify="right")
        wp_table.add_column("Parlours (all)", justify="right")
        wp_table.add_column("Workers (winners)", justify="right")
        wp_table.add_column("Parlours (winners)", justify="right")
        for age in AgeType:
            wp_table.add_row(
                age.name.capitalize(),
                f"{self.worker_by_age[age]:.2f}",
                f"{self.parlour_by_age[age]:.2f}",
                f"{self.winner_worker_by_age[age]:.2f}",
                f"{self.winner_parlour_by_age[age]:.2f}",
            )
        console.print(wp_table)

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
