"""Tests for analysis.runner. See requirements section 7.2.3."""

import pytest

from src.ai.random_agent import RandomAgent
from src.analysis.runner import run_batch
from src.game.data_loader import GameDataLoader
from src.game.simulation import GameResult


@pytest.fixture(scope="module")
def data():
    return GameDataLoader()


def _agents(data, seed=0):
    return [RandomAgent(data, seed=seed + i) for i in range(4)]


# ---------------------------------------------------------------------------
# req 7.2.3 — run_batch returns the correct number of results
# ---------------------------------------------------------------------------

def test_run_batch_count(data):
    """run_batch(10, ...) returns exactly 10 GameResult objects."""
    results = run_batch(10, _agents(data, seed=1), data, base_seed=1)
    assert len(results) == 10
    for r in results:
        assert isinstance(r, GameResult)


def test_run_batch_all_scores_non_negative(data):
    """All four player scores in every game are non-negative integers."""
    results = run_batch(10, _agents(data, seed=2), data, base_seed=2)
    for result in results:
        assert len(result.scores) == 4
        for sb in result.scores:
            assert isinstance(sb.total, int)
            assert sb.total >= 0


def test_run_batch_seeds_differ(data):
    """With base_seed, successive games use different seeds."""
    results = run_batch(5, _agents(data, seed=10), data, base_seed=10)
    seeds = [r.seed for r in results]
    assert seeds == [10, 11, 12, 13, 14]


def test_run_batch_no_seed(data):
    """run_batch without base_seed still generates a seed for each game."""
    results = run_batch(3, _agents(data), data, base_seed=None)
    for r in results:
        assert isinstance(r.seed, int)


def test_run_batch_reproducible(data):
    """Two run_batch calls with the same base_seed produce identical scores."""
    a = run_batch(5, _agents(data, seed=99), data, base_seed=99)
    b = run_batch(5, _agents(data, seed=99), data, base_seed=99)
    for ra, rb in zip(a, b):
        assert ra.total_turns == rb.total_turns
        assert ra.winner_ids == rb.winner_ids
        for sa, sb_score in zip(ra.scores, rb.scores):
            assert sa.total == sb_score.total
