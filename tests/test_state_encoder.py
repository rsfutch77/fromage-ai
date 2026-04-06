"""Tests for the state_encoder module. See requirements section 9.1.7."""

import numpy as np
import pytest

from src.ai.state_encoder import STATE_VECTOR_SIZE, encode_state
from src.game.board import setup_game
from src.game.data_loader import GameDataLoader


@pytest.fixture(scope="module")
def data():
    return GameDataLoader()


@pytest.fixture(scope="module")
def state(data):
    return setup_game(data, seed=42)


def test_length(state, data):
    """Encoded vector length must equal STATE_VECTOR_SIZE."""
    vec = encode_state(state, 0, data)
    assert len(vec) == STATE_VECTOR_SIZE


def test_values_in_unit_interval(state, data):
    """All features must lie in [0, 1]."""
    for player_id in range(4):
        vec = encode_state(state, player_id, data)
        assert np.all(vec >= 0.0), f"Player {player_id}: min value {vec.min()}"
        assert np.all(vec <= 1.0), f"Player {player_id}: max value {vec.max()}"


def test_dtype_float32(state, data):
    """Output must be float32."""
    vec = encode_state(state, 0, data)
    assert vec.dtype == np.float32


def test_deterministic(state, data):
    """Same (state, player_id) must produce identical vectors."""
    v1 = encode_state(state, 0, data)
    v2 = encode_state(state, 0, data)
    np.testing.assert_array_equal(v1, v2)


def test_different_players_differ(state, data):
    """Different player_ids generally produce different vectors (for initial state)."""
    v0 = encode_state(state, 0, data)
    v1 = encode_state(state, 1, data)
    assert not np.array_equal(v0, v1), "Player 0 and player 1 should differ in initial state"


def test_state_vector_size_constant():
    """STATE_VECTOR_SIZE must equal 197."""
    assert STATE_VECTOR_SIZE == 197
