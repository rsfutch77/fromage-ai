"""Tests for learning-performance chart functions (L1–L4) and
hyperparameter signals export.

Creates synthetic training log JSONL and dummy checkpoint files, runs all
4 chart functions and the signals export, then asserts outputs exist and
are non-empty.

See requirements section 13.3.1.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Fixtures — synthetic training data
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def training_dir(tmp_path_factory):
    """Create a temp directory with a synthetic training log and checkpoints."""
    base = tmp_path_factory.mktemp("learning")

    # --- training_log.jsonl ---
    log_path = base / "training_log.jsonl"
    entries = []
    for i in range(1, 21):
        game = i * 500
        epsilon = max(0.05, 1.0 - game / 5000 * 0.95)
        entries.append({
            "game": game,
            "epsilon": round(epsilon, 4),
            "win_rate": round(0.20 + i * 0.01, 4),
            "mean_score": round(40.0 + i * 0.5, 2),
            "std_score": round(6.0 - i * 0.15, 2),
            "pp_delta": round(-1.0 + i * 0.3, 2),
        })
    with open(log_path, "w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry) + "\n")

    # --- checkpoint files ---
    models_dir = base / "models"
    models_dir.mkdir()
    for i in range(1, 11):
        game = i * 1000
        weights = np.random.default_rng(seed=i).standard_normal(100)
        np.savez(models_dir / f"checkpoint_{game}.npz", w=weights)

    # --- config ---
    config_path = base / "agent_config.json"
    config_path.write_text(json.dumps({
        "epsilon_start": 1.0,
        "epsilon_end": 0.05,
        "epsilon_decay_games": 5000,
        "alpha": 0.001,
        "gamma": 0.95,
    }), encoding="utf-8")

    return base


@pytest.fixture(scope="module")
def log_path(training_dir):
    return training_dir / "training_log.jsonl"


@pytest.fixture(scope="module")
def models_dir(training_dir):
    return training_dir / "models"


@pytest.fixture(scope="module")
def config_path(training_dir):
    return training_dir / "agent_config.json"


@pytest.fixture(scope="module")
def config(config_path):
    with open(config_path, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def out_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("learning_plots")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_png(path: Path) -> None:
    assert path.exists(), f"PNG not created: {path}"
    assert os.path.getsize(path) > 0, f"PNG is empty: {path}"


# ---------------------------------------------------------------------------
# Chart L1 — Epsilon decay curve
# ---------------------------------------------------------------------------

def test_chart_L1_epsilon_decay(log_path, config, out_dir):
    from src.analysis.plots import plot_epsilon_decay

    out = out_dir / "chart_L1_epsilon_decay.png"
    plot_epsilon_decay(log_path, config, out)
    _assert_png(out)


# ---------------------------------------------------------------------------
# Chart L2 — Win rate vs training progress
# ---------------------------------------------------------------------------

def test_chart_L2_win_rate_vs_training(log_path, out_dir):
    from src.analysis.plots import plot_win_rate_vs_training

    out = out_dir / "chart_L2_win_rate_vs_training.png"
    plot_win_rate_vs_training(log_path, out)
    _assert_png(out)


# ---------------------------------------------------------------------------
# Chart L3 — Mean score over training
# ---------------------------------------------------------------------------

def test_chart_L3_mean_score_training(log_path, out_dir):
    from src.analysis.plots import plot_mean_score_training

    out = out_dir / "chart_L3_mean_score_training.png"
    plot_mean_score_training(log_path, out)
    _assert_png(out)


# ---------------------------------------------------------------------------
# Chart L4 — Q-weight magnitude over checkpoints
# ---------------------------------------------------------------------------

def test_chart_L4_q_weight_norms(models_dir, out_dir):
    from src.analysis.plots import plot_q_weight_norms

    out = out_dir / "chart_L4_q_weight_norms.png"
    plot_q_weight_norms(models_dir, out)
    _assert_png(out)


# ---------------------------------------------------------------------------
# Hyperparameter signals CSV
# ---------------------------------------------------------------------------

def test_write_hyperparameter_signals(log_path, models_dir, config_path, out_dir):
    from src.analysis.exports import write_hyperparameter_signals

    out = out_dir / "hyperparameter_signals.csv"
    write_hyperparameter_signals(log_path, models_dir, config_path, out)
    assert out.exists(), "CSV not created"
    assert os.path.getsize(out) > 0, "CSV is empty"

    content = out.read_text(encoding="utf-8")
    assert "signal,value,unit,threshold,status,recommendation" in content
    # Expect all 11 signals
    lines = [ln for ln in content.strip().split("\n") if ln]
    assert len(lines) == 12, f"Expected header + 11 signals, got {len(lines)} lines"


# ---------------------------------------------------------------------------
# Edge case: empty log skips gracefully
# ---------------------------------------------------------------------------

def test_charts_skip_on_empty_log(tmp_path):
    from src.analysis.plots import plot_epsilon_decay, plot_win_rate_vs_training

    empty_log = tmp_path / "empty.jsonl"
    empty_log.write_text("", encoding="utf-8")

    out = tmp_path / "should_not_exist.png"
    plot_epsilon_decay(empty_log, {"epsilon_end": 0.05}, out)
    assert not out.exists()

    plot_win_rate_vs_training(empty_log, out)
    assert not out.exists()


def test_L4_skips_on_no_checkpoints(tmp_path):
    from src.analysis.plots import plot_q_weight_norms

    empty_models = tmp_path / "no_models"
    empty_models.mkdir()
    out = tmp_path / "should_not_exist.png"
    plot_q_weight_norms(empty_models, out)
    assert not out.exists()
