"""Tests for src/ai/training.py — Milestone 8, req 11.2.2."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.ai.q_agent import QAgent
from src.ai.training import evaluate, train
from src.game.data_loader import GameDataLoader


@pytest.fixture(scope="module")
def data() -> GameDataLoader:
    return GameDataLoader()


@pytest.fixture(scope="module")
def mini_config(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Minimal agent config for fast tests (high eval/checkpoint thresholds)."""
    import json
    cfg = {
        "epsilon_start": 0.5,
        "epsilon_end": 0.05,
        "epsilon_decay_games": 10,
        "alpha": 0.01,
        "gamma": 0.95,
        "reward_win": 1.0,
        "reward_loss": 0.0,
        "reward_per_pp": 0.0,
        "model_save_dir": str(tmp_path_factory.mktemp("models")),
        "use_network_approx": False,
        "eval_interval": 100,
        "checkpoint_interval": 100,
    }
    p = tmp_path_factory.mktemp("config") / "agent_config.json"
    p.write_text(json.dumps(cfg))
    return p


def test_train_changes_weights(data: GameDataLoader, mini_config: Path) -> None:
    """Q-weights must differ from their zero-initialised values after training."""
    import json
    config = json.loads(mini_config.read_text())
    initial_agent = QAgent(data=data, config=config)
    initial_weights = initial_agent._weights.copy()

    trained_agent = train(n_games=20, data=data, config_path=mini_config)

    assert not np.array_equal(trained_agent._weights, initial_weights), (
        "Weights unchanged after 20 training games"
    )


def test_train_returns_qagent(data: GameDataLoader, mini_config: Path) -> None:
    """train() must return a QAgent instance."""
    result = train(n_games=5, data=data, config_path=mini_config)
    assert isinstance(result, QAgent)


def test_evaluate_keys(data: GameDataLoader, mini_config: Path) -> None:
    """evaluate() must return a dict with the three expected keys."""
    import json
    config = json.loads(mini_config.read_text())
    agent = QAgent(data=data, config=config)
    result = evaluate(agent, n_games=10, data=data)

    assert set(result.keys()) == {"win_rate", "mean_pp", "mean_pp_delta_vs_random"}


def test_evaluate_value_ranges(data: GameDataLoader, mini_config: Path) -> None:
    """evaluate() return values must be in plausible ranges."""
    import json
    config = json.loads(mini_config.read_text())
    agent = QAgent(data=data, config=config)
    result = evaluate(agent, n_games=10, data=data)

    assert 0.0 <= result["win_rate"] <= 1.0, f"win_rate out of range: {result['win_rate']}"
    assert result["mean_pp"] >= 0, f"mean_pp negative: {result['mean_pp']}"
    assert isinstance(result["mean_pp_delta_vs_random"], float)


def test_evaluate_restores_epsilon(data: GameDataLoader, mini_config: Path) -> None:
    """evaluate() must restore agent epsilon to its pre-call value."""
    import json
    config = json.loads(mini_config.read_text())
    agent = QAgent(data=data, config=config)
    agent._epsilon = 0.42
    evaluate(agent, n_games=5, data=data)
    assert agent._epsilon == pytest.approx(0.42)


def test_checkpoint_written(data: GameDataLoader, tmp_path: Path) -> None:
    """A checkpoint file must be created when checkpoint_interval is reached."""
    import json
    cfg = {
        "epsilon_start": 1.0,
        "epsilon_end": 0.05,
        "epsilon_decay_games": 5,
        "alpha": 0.01,
        "gamma": 0.95,
        "reward_win": 1.0,
        "reward_loss": 0.0,
        "reward_per_pp": 0.0,
        "model_save_dir": str(tmp_path / "models"),
        "use_network_approx": False,
        "eval_interval": 100,
        "checkpoint_interval": 5,
    }
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(cfg))

    train(n_games=5, data=data, config_path=cfg_path)

    models_dir = tmp_path / "models"
    checkpoints = list(models_dir.glob("checkpoint_*.npz"))
    assert len(checkpoints) >= 1, "No checkpoint file written"
    assert (models_dir / "trained_agent.npz").exists(), "Final model not saved"
