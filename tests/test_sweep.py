"""Tests for src/sweep.py — Milestone 11, task 11.6."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.game.data_loader import GameDataLoader
from src.sweep import _run_single_config, expand_grid, run_sweep


@pytest.fixture(scope="module")
def data() -> GameDataLoader:
    return GameDataLoader()


# ---------------------------------------------------------------------------
# 11.6.1  Grid expansion produces the correct number of combinations
# ---------------------------------------------------------------------------

def test_expand_grid_count() -> None:
    grid = {
        "alpha": [0.001, 0.005, 0.01, 0.02],
        "gamma": [0.9, 0.95, 0.99],
        "epsilon_decay_games": [1500, 3000, 5000],
        "weight_decay": [1e-6, 1e-5],
    }
    combos = expand_grid(grid)
    assert len(combos) == 4 * 3 * 3 * 2  # 72


def test_expand_grid_single_values() -> None:
    grid = {"alpha": [0.01], "gamma": [0.95]}
    combos = expand_grid(grid)
    assert len(combos) == 1
    assert combos[0] == {"alpha": 0.01, "gamma": 0.95}


def test_expand_grid_keys_preserved() -> None:
    grid = {"a": [1, 2], "b": [3, 4]}
    combos = expand_grid(grid)
    assert all(set(c.keys()) == {"a", "b"} for c in combos)


# ---------------------------------------------------------------------------
# 11.6.2  _run_single_config returns expected keys
# ---------------------------------------------------------------------------

def test_run_single_config_keys(data: GameDataLoader) -> None:
    config = {
        "epsilon_start": 1.0,
        "epsilon_end": 0.05,
        "epsilon_decay_games": 5,
        "alpha": 0.01,
        "gamma": 0.95,
        "weight_decay": 1e-6,
        "use_network_approx": False,
    }
    # (run_id, combo_id, repeat, config, n_games, eval_interval, eval_games, final_eval_games, seed, swept_keys)
    swept_keys = ["alpha", "gamma", "epsilon_decay_games", "weight_decay"]
    args = (0, 0, 0, config, 5, 5, 3, 5, 42, swept_keys)
    result = _run_single_config(args)

    expected_keys = {
        "run_id", "combo_id", "repeat", "win_rate", "mean_pp", "pp_delta",
        "final_epsilon", "elapsed_seconds", "eval_log",
        "alpha", "gamma", "epsilon_decay_games", "weight_decay",
    }
    assert expected_keys.issubset(set(result.keys()))
    assert result["run_id"] == 0
    assert result["combo_id"] == 0
    assert result["repeat"] == 0
    assert 0.0 <= result["win_rate"] <= 1.0
    assert result["elapsed_seconds"] >= 0


# ---------------------------------------------------------------------------
# 11.6.3  run_sweep with minimal grid produces valid CSV
# ---------------------------------------------------------------------------

def test_run_sweep_minimal(tmp_path: Path) -> None:
    """A 2-combo sweep must produce a CSV with correct columns and row count."""
    base_cfg = {
        "epsilon_start": 1.0,
        "epsilon_end": 0.05,
        "epsilon_decay_games": 5,
        "alpha": 0.01,
        "gamma": 0.95,
        "weight_decay": 1e-6,
        "use_network_approx": False,
        "eval_interval": 100,
        "checkpoint_interval": 100,
    }
    base_path = tmp_path / "base.json"
    base_path.write_text(json.dumps(base_cfg))

    sweep_cfg = {
        "base_config": str(base_path),
        "screening_games": 5,
        "screening_eval_interval": 5,
        "screening_eval_games": 3,
        "final_eval_games": 3,
        "max_workers": 1,
        "grid": {
            "alpha": [0.005, 0.01],
        },
    }
    sweep_path = tmp_path / "sweep.json"
    sweep_path.write_text(json.dumps(sweep_cfg))

    results = run_sweep(sweep_path, seed=42)

    assert len(results) == 2
    assert results[0]["rank"] == 1
    assert results[1]["rank"] == 2
    # Best win_rate should be first
    assert results[0]["win_rate"] >= results[1]["win_rate"]

    # Check CSV was written
    csv_path = Path("output") / "sweep_results.csv"
    assert csv_path.exists()
    lines = csv_path.read_text().strip().split("\n")
    assert len(lines) == 3  # header + 2 data rows
    header = lines[0].split(",")
    assert "rank" in header
    assert "win_rate" in header
    assert "alpha" in header


def test_run_sweep_with_repeats(tmp_path: Path) -> None:
    """A 2-combo × 2-repeat sweep produces per-run CSV and summary CSV."""
    base_cfg = {
        "epsilon_start": 1.0,
        "epsilon_end": 0.05,
        "epsilon_decay_games": 5,
        "alpha": 0.01,
        "gamma": 0.95,
        "weight_decay": 1e-6,
        "use_network_approx": False,
        "eval_interval": 100,
        "checkpoint_interval": 100,
    }
    base_path = tmp_path / "base.json"
    base_path.write_text(json.dumps(base_cfg))

    sweep_cfg = {
        "base_config": str(base_path),
        "screening_games": 5,
        "screening_eval_interval": 5,
        "screening_eval_games": 3,
        "final_eval_games": 3,
        "max_workers": 1,
        "repeats": 2,
        "grid": {
            "alpha": [0.005, 0.01],
        },
    }
    sweep_path = tmp_path / "sweep.json"
    sweep_path.write_text(json.dumps(sweep_cfg))

    results = run_sweep(sweep_path, seed=42)

    # 2 combos × 2 repeats = 4 per-run results
    assert len(results) == 4
    assert all("combo_id" in r for r in results)
    assert all("repeat" in r for r in results)

    # Per-run CSV: 4 data rows
    csv_path = Path("output") / "sweep_results.csv"
    lines = csv_path.read_text().strip().split("\n")
    assert len(lines) == 5  # header + 4

    # Summary CSV: 2 combo rows
    summary_path = Path("output") / "sweep_summary.csv"
    assert summary_path.exists()
    summary_lines = summary_path.read_text().strip().split("\n")
    assert len(summary_lines) == 3  # header + 2 combos
    header = summary_lines[0].split(",")
    assert "mean_win_rate" in header
    assert "std_win_rate" in header
