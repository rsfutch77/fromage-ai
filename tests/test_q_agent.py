"""Tests for the QAgent class. See requirements section 10.1."""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from src.ai.q_agent import QAgent
from src.game.actions import TurnAction, all_legal_turn_actions
from src.game.board import setup_game
from src.game.data_loader import GameDataLoader


@pytest.fixture(scope="module")
def data():
    return GameDataLoader()


@pytest.fixture(scope="module")
def state(data):
    return setup_game(data, seed=7)


@pytest.fixture(scope="module")
def config():
    return {
        "epsilon_start": 0.0,
        "epsilon_end": 0.05,
        "epsilon_decay_games": 5000,
        "alpha": 0.1,
        "gamma": 0.95,
        "reward_win": 1.0,
        "reward_loss": 0.0,
        "reward_per_pp": 0.0,
        "model_save_dir": "models/",
        "use_network_approx": False,
    }


@pytest.fixture(scope="module")
def agent(data, config):
    return QAgent(data=data, config=config, seed=0)


# ---------------------------------------------------------------------------
# choose_action
# ---------------------------------------------------------------------------

def test_choose_action_returns_turn_action(agent, state):
    """choose_action must return a TurnAction instance."""
    action = agent.choose_action(state, 0)
    assert isinstance(action, TurnAction)


def test_choose_action_is_legal(agent, state, data):
    """Returned action must be in the legal action set."""
    legal = all_legal_turn_actions(state, 0, data)
    action = agent.choose_action(state, 0)
    assert action in legal


def test_epsilon_one_random(data, config, state):
    """With ε=1.0 the agent selects uniformly at random; results vary over runs."""
    random_config = dict(config, epsilon_start=1.0)
    agent_random = QAgent(data=data, config=random_config, seed=None)
    choices = [agent_random.choose_action(state, 0) for _ in range(30)]
    # All returned actions must be TurnAction instances
    assert all(isinstance(c, TurnAction) for c in choices)
    # At least 2 distinct choices from 30 draws (very likely for a non-trivial state)
    unique = {(str(c.gather), c.use_barn, len(c.make_cheese)) for c in choices}
    assert len(unique) >= 2, "Random agent should produce varied choices over 30 draws"


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

def test_update_changes_weights(data, config, state):
    """After calling update, the weight vector must differ from its initial zero value."""
    fresh_config = dict(config, epsilon_start=0.0)
    agent = QAgent(data=data, config=fresh_config, seed=1)
    weights_before = agent._weights.copy()

    legal = all_legal_turn_actions(state, 0, data)
    action = legal[0]
    agent.update(state, 0, action, reward=1.0, next_state=state)

    assert not np.array_equal(agent._weights, weights_before), \
        "Weights should change after an update with non-zero reward"


def test_update_network_changes_params(data, state):
    """Network params must change after update when use_network_approx=True."""
    net_config = {
        "epsilon_start": 0.0,
        "alpha": 0.01,
        "gamma": 0.95,
        "use_network_approx": True,
    }
    agent = QAgent(data=data, config=net_config, seed=2)
    W1_before = agent._params["W1"].copy()

    legal = all_legal_turn_actions(state, 0, data)
    action = legal[0]
    agent.update(state, 0, action, reward=1.0, next_state=state)

    assert not np.array_equal(agent._params["W1"], W1_before), \
        "Network weights should change after update"


# ---------------------------------------------------------------------------
# save / load round-trip
# ---------------------------------------------------------------------------

def test_save_load_roundtrip_linear(data, config, state):
    """save then load must preserve weights and epsilon exactly."""
    agent = QAgent(data=data, config=config, seed=3)
    legal = all_legal_turn_actions(state, 0, data)
    agent.update(state, 0, legal[0], reward=0.5, next_state=state)
    original_weights = agent._weights.copy()
    original_epsilon = agent._epsilon

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test_agent.npz"
        agent.save(path)
        loaded = QAgent.load(path, data)

    np.testing.assert_array_equal(loaded._weights, original_weights)
    assert loaded._epsilon == original_epsilon


def test_save_load_roundtrip_network(data, state):
    """save then load must preserve network params."""
    net_config = {
        "epsilon_start": 0.5,
        "alpha": 0.01,
        "gamma": 0.9,
        "use_network_approx": True,
    }
    agent = QAgent(data=data, config=net_config, seed=4)
    legal = all_legal_turn_actions(state, 0, data)
    agent.update(state, 0, legal[0], reward=1.0, next_state=state)
    original_W1 = agent._params["W1"].copy()

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "net_agent.npz"
        agent.save(path)
        loaded = QAgent.load(path, data)

    np.testing.assert_array_equal(loaded._params["W1"], original_W1)
