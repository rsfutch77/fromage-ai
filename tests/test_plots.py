"""Tests for analysis chart functions.

Populates a temporary ResultsDB with 50 RandomAgent game results, then
runs each of the 14 chart functions and verifies that a non-empty PNG file
is created.

See requirements section 8.3.7.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.ai.random_agent import RandomAgent
from src.analysis.exports import write_strategy_summary
from src.analysis.results_db import ResultsDB
from src.analysis.runner import run_batch
from src.game.data_loader import GameDataLoader


_AGENT_CONFIG = "RandomAgent x4"
_N_GAMES = 50


@pytest.fixture(scope="module")
def data():
    return GameDataLoader()


@pytest.fixture(scope="module")
def populated_db(data, tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test_plots.db"
    agents = [RandomAgent(data, seed=i) for i in range(4)]
    results = run_batch(_N_GAMES, agents, data, base_seed=0)
    db = ResultsDB(db_path)
    for result in results:
        db.store_result(result, _AGENT_CONFIG)
    return db


@pytest.fixture(scope="module")
def out_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("plots")


def _assert_png(path: Path) -> None:
    assert path.exists(), f"PNG not created: {path}"
    assert os.path.getsize(path) > 0, f"PNG is empty: {path}"


# ---------------------------------------------------------------------------
# Chart tests
# ---------------------------------------------------------------------------

def test_chart_01_structure_frequency(populated_db, out_dir):
    from src.analysis.plots import plot_structure_frequency
    plot_structure_frequency(populated_db, out_dir)
    _assert_png(out_dir / "chart_01_structure_frequency.png")


def test_chart_02_points_per_venue(populated_db, out_dir):
    from src.analysis.plots import plot_points_per_venue
    plot_points_per_venue(populated_db, out_dir)
    _assert_png(out_dir / "chart_02_points_per_venue.png")


def test_chart_03_win_rate_by_board(populated_db, out_dir):
    from src.analysis.plots import plot_win_rate_by_board
    plot_win_rate_by_board(populated_db, out_dir)
    _assert_png(out_dir / "chart_03_win_rate_by_board.png")


def test_chart_04_fruit_usage(populated_db, out_dir):
    from src.analysis.plots import plot_fruit_usage
    plot_fruit_usage(populated_db, out_dir)
    _assert_png(out_dir / "chart_04_fruit_usage.png")


def test_chart_05_orders_share(populated_db, out_dir):
    from src.analysis.plots import plot_orders_share
    plot_orders_share(populated_db, out_dir)
    _assert_png(out_dir / "chart_05_orders_share.png")


def test_chart_06_unused_resources_share(populated_db, out_dir):
    from src.analysis.plots import plot_unused_resources_share
    plot_unused_resources_share(populated_db, out_dir)
    _assert_png(out_dir / "chart_06_unused_resources_share.png")


def test_chart_07_winner_vs_loser_radar(populated_db, out_dir):
    from src.analysis.plots import plot_winner_vs_loser_radar
    plot_winner_vs_loser_radar(populated_db, out_dir)
    _assert_png(out_dir / "chart_07_winner_vs_loser_radar.png")


def test_chart_08_board_venue_heatmap(populated_db, out_dir):
    from src.analysis.plots import plot_board_venue_heatmap
    plot_board_venue_heatmap(populated_db, out_dir)
    _assert_png(out_dir / "chart_08_board_venue_heatmap.png")


def test_chart_09_cheese_age_distribution(populated_db, out_dir):
    from src.analysis.plots import plot_cheese_age_distribution
    plot_cheese_age_distribution(populated_db, out_dir)
    _assert_png(out_dir / "chart_09_cheese_age_distribution.png")


def test_chart_10_structure_unlock_by_outcome(populated_db, out_dir):
    from src.analysis.plots import plot_structure_unlock_by_outcome
    plot_structure_unlock_by_outcome(populated_db, out_dir)
    _assert_png(out_dir / "chart_10_structure_unlock_by_outcome.png")


def test_chart_11_headquarters_by_board(populated_db, out_dir):
    from src.analysis.plots import plot_headquarters_by_board
    plot_headquarters_by_board(populated_db, out_dir)
    _assert_png(out_dir / "chart_11_headquarters_by_board.png")


def test_chart_12_parlour_usage_vs_win_rate(populated_db, out_dir):
    from src.analysis.plots import plot_parlour_usage_vs_win_rate
    plot_parlour_usage_vs_win_rate(populated_db, out_dir)
    _assert_png(out_dir / "chart_12_parlour_usage_vs_win_rate.png")


def test_chart_13_villes_region_control(populated_db, out_dir):
    from src.analysis.plots import plot_villes_region_control
    plot_villes_region_control(populated_db, out_dir)
    _assert_png(out_dir / "chart_13_villes_region_control.png")


def test_chart_14_fruit_balance_scatter(populated_db, out_dir):
    from src.analysis.plots import plot_fruit_balance_scatter
    plot_fruit_balance_scatter(populated_db, out_dir)
    _assert_png(out_dir / "chart_14_fruit_balance_scatter.png")


# ---------------------------------------------------------------------------
# exports test
# ---------------------------------------------------------------------------

def test_write_strategy_summary(populated_db, out_dir):
    summary_path = out_dir / "strategy_summary.md"
    write_strategy_summary(populated_db, summary_path)
    assert summary_path.exists()
    content = summary_path.read_text(encoding="utf-8")
    assert "## Finding:" in content
    assert "source_chart:" in content


# ---------------------------------------------------------------------------
# Skip guard: chart functions skip gracefully with empty DB
# ---------------------------------------------------------------------------

def test_chart_skips_on_empty_db(tmp_path):
    from src.analysis.plots import plot_points_per_venue
    empty_db = ResultsDB(tmp_path / "empty.db")
    plot_points_per_venue(empty_db, tmp_path / "plots")
    # no PNG should be created
    assert not (tmp_path / "plots" / "chart_02_points_per_venue.png").exists()
