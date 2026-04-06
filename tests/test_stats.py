"""Tests for analysis.stats. See requirements section 8.2.3."""

import pytest

from src.ai.random_agent import RandomAgent
from src.analysis.runner import run_batch
from src.analysis.stats import BaselineStats
from src.game.data_loader import GameDataLoader


@pytest.fixture(scope="module")
def results():
    data = GameDataLoader()
    agents = [RandomAgent(data, seed=i) for i in range(4)]
    return run_batch(50, agents, data, base_seed=0)


# ---------------------------------------------------------------------------
# req 8.2.3 — BaselineStats correctness
# ---------------------------------------------------------------------------

def test_win_rates_sum_to_one(results):
    """Win rates across all 4 boards sum to approximately 1.0 (±0.05)."""
    stats = BaselineStats(results)
    total = sum(stats.win_rate_by_board.values())
    assert abs(total - 1.0) <= 0.05


def test_mean_scores_non_negative(results):
    """All mean scores per category are non-negative."""
    stats = BaselineStats(results)
    for cat, mean in stats.mean_score_by_category.items():
        assert mean >= 0, f"Negative mean for category '{cat}': {mean}"


def test_score_std_non_negative(results):
    """Standard deviation of total scores is non-negative."""
    stats = BaselineStats(results)
    assert stats.score_std >= 0


def test_mean_turns_positive(results):
    """Mean turns per game is positive."""
    stats = BaselineStats(results)
    assert stats.mean_turns > 0


def test_percentiles_ordered(results):
    """Percentile values are non-decreasing."""
    stats = BaselineStats(results)
    marks = sorted(stats.score_percentiles.keys())
    for a, b in zip(marks, marks[1:]):
        assert stats.score_percentiles[a] <= stats.score_percentiles[b]


def test_summary_table_returns_string(results):
    """summary_table() returns a non-empty string."""
    stats = BaselineStats(results)
    table = stats.summary_table()
    assert isinstance(table, str)
    assert len(table) > 0


def test_empty_results_raises():
    """BaselineStats raises ValueError when given an empty list."""
    with pytest.raises(ValueError):
        BaselineStats([])
