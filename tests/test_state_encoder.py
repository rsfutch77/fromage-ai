"""Tests for the state_encoder module. See requirements sections 9.1.7 and 9.2.8."""

import copy

import numpy as np
import pytest

from src.ai.state_encoder import (
    STATE_VECTOR_SIZE,
    _BASE_SIZE,
    encode_state,
    _REGION_ORDER,
)
from src.game.board import setup_game
from src.game.data_loader import GameDataLoader
from src.game.state import PlacedCheese
from src.game.types import AgeType, CheeseType, SpaceType, VenueType, VENUE_ORDER, RESOURCE_ORDER


@pytest.fixture(scope="module")
def data():
    return GameDataLoader()


@pytest.fixture(scope="module")
def state(data):
    return setup_game(data, seed=42)


# ---------------------------------------------------------------------------
# Base encoder tests (carried forward)
# ---------------------------------------------------------------------------

def test_length(state, data):
    """Encoded vector length must equal STATE_VECTOR_SIZE (292)."""
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
    """STATE_VECTOR_SIZE must equal 292 (enhanced) and _BASE_SIZE must equal 197."""
    assert STATE_VECTOR_SIZE == 292
    assert _BASE_SIZE == 197


# ---------------------------------------------------------------------------
# Legacy (non-enhanced) encoder tests
# ---------------------------------------------------------------------------

def test_legacy_length(state, data):
    """Legacy vector length must equal _BASE_SIZE (197)."""
    vec = encode_state(state, 0, data, enhanced=False)
    assert len(vec) == _BASE_SIZE


def test_legacy_values_in_unit_interval(state, data):
    """Legacy features must lie in [0, 1]."""
    vec = encode_state(state, 0, data, enhanced=False)
    assert np.all(vec >= 0.0)
    assert np.all(vec <= 1.0)


# ---------------------------------------------------------------------------
# Enhanced encoder: venue/resource lookahead (10E.1)
# ---------------------------------------------------------------------------

def test_venue_lookahead_matches_rotation(state, data):
    """Venue lookahead one-hots must match venue_facing at each offset."""
    for player_id in range(4):
        vec = encode_state(state, player_id, data)
        # Venue lookahead starts after base 197 features
        lookahead_start = _BASE_SIZE
        for offset in range(4):
            sub = vec[lookahead_start + offset * 4: lookahead_start + offset * 4 + 4]
            expected_idx = (player_id + state.rotation_index + offset) % 4
            expected = np.zeros(4, dtype=np.float32)
            expected[expected_idx] = 1.0
            np.testing.assert_array_equal(sub, expected,
                err_msg=f"Player {player_id}, venue offset {offset}")


def test_resource_lookahead_matches_rotation(state, data):
    """Resource lookahead one-hots must match resource_facing at each offset."""
    for player_id in range(4):
        vec = encode_state(state, player_id, data)
        res_start = _BASE_SIZE + 16  # after venue lookahead
        for offset in range(3):
            sub = vec[res_start + offset * 4: res_start + offset * 4 + 4]
            expected_idx = (
                player_id + state.resource_tile_orientation + state.rotation_index + offset
            ) % 4
            expected = np.zeros(4, dtype=np.float32)
            expected[expected_idx] = 1.0
            np.testing.assert_array_equal(sub, expected,
                err_msg=f"Player {player_id}, resource offset {offset}")


# ---------------------------------------------------------------------------
# Enhanced encoder: worker turns-until-available (10E.2)
# ---------------------------------------------------------------------------

def test_worker_availability_initial_state(state, data):
    """At game start, all workers in hand → turns=0 for all types."""
    vec = encode_state(state, 0, data)
    worker_start = _BASE_SIZE + 16 + 12  # after venue + resource lookahead
    for i in range(3):
        sub = vec[worker_start + i * 4: worker_start + i * 4 + 4]
        # index 0 should be 1.0 (in hand = 0 turns)
        assert sub[0] == 1.0, f"Worker type {i}: expected in-hand"
        assert sum(sub) == 1.0, f"Worker type {i}: expected one-hot"


# ---------------------------------------------------------------------------
# Enhanced encoder: scoring-derived features with known placements (10E.3-6)
# ---------------------------------------------------------------------------

def _make_state_with_placements(data):
    """Create a state with known cheese placements for testing derived features."""
    state = setup_game(data, seed=42)
    state = copy.deepcopy(state)
    player = state.players[0]

    # Place tokens on Festival (adjacent positions for a group)
    festival_cheese_spaces = [
        sp for sp in data.festival_spaces if sp.space_type == SpaceType.CHEESE
    ]
    for sp in festival_cheese_spaces[:3]:
        pc = PlacedCheese(
            cheese_type=sp.cheese_type or CheeseType.SOFT,
            age=sp.age or AgeType.BRONZE,
            venue=VenueType.FESTIVAL,
            player_id=0,
            row=sp.row,
            col=sp.col,
        )
        player.cheese_tokens_on_board.append(pc)
        player.cheese_tokens_remaining -= 1

    # Place tokens on Fromagerie (different shelves)
    for sp in data.fromagerie_spaces[:3]:
        pc = PlacedCheese(
            cheese_type=sp.cheese_type,
            age=sp.age,
            venue=VenueType.FROMAGERIE,
            player_id=0,
            space_id=sp.space_id,
        )
        player.cheese_tokens_on_board.append(pc)
        player.cheese_tokens_remaining -= 1

    # Place tokens on Bistro (on the same table for a pairing)
    bistro_spaces_sorted = sorted(data.bistro_spaces, key=lambda s: s.table_id)
    first_table = bistro_spaces_sorted[0].table_id
    same_table = [s for s in bistro_spaces_sorted if s.table_id == first_table][:2]
    for sp in same_table:
        pc = PlacedCheese(
            cheese_type=sp.cheese_type,
            age=sp.plate_age,
            venue=VenueType.BISTRO,
            player_id=0,
            space_id=sp.space_id,
            table_id=sp.table_id,
        )
        player.cheese_tokens_on_board.append(pc)
        player.cheese_tokens_remaining -= 1

    # Place tokens on Villes (to gain influence in a region)
    for sp in data.villes_spaces[:2]:
        pc = PlacedCheese(
            cheese_type=sp.cheese_type,
            age=sp.age,
            venue=VenueType.VILLES,
            player_id=0,
            space_id=sp.space_id,
        )
        player.cheese_tokens_on_board.append(pc)
        player.cheese_tokens_remaining -= 1

    return state


def test_festival_derived_nonzero(data):
    """Festival derived features should be non-zero with known placements."""
    state = _make_state_with_placements(data)
    vec = encode_state(state, 0, data)
    fest_start = _BASE_SIZE + 16 + 12 + 12  # after lookahead + workers
    fest_sub = vec[fest_start: fest_start + 5]
    # At least the score or a group size should be non-zero
    assert np.any(fest_sub > 0), f"Festival derived features all zero: {fest_sub}"


def test_fromagerie_derived_nonzero(data):
    """Fromagerie derived features should be non-zero with known placements."""
    state = _make_state_with_placements(data)
    vec = encode_state(state, 0, data)
    from_start = _BASE_SIZE + 16 + 12 + 12 + 5  # after festival derived
    from_sub = vec[from_start: from_start + 6]
    # Own shelf count should be > 0
    assert from_sub[0] > 0, f"Fromagerie own shelves should be > 0: {from_sub}"


def test_bistro_derived_nonzero(data):
    """Bistro derived features should be non-zero with known placements."""
    state = _make_state_with_placements(data)
    vec = encode_state(state, 0, data)
    bis_start = _BASE_SIZE + 16 + 12 + 12 + 5 + 6  # after fromagerie derived
    bis_sub = vec[bis_start: bis_start + 8]
    # Pairings should be > 0 (we placed 2 tokens on same table)
    assert bis_sub[0] > 0, f"Bistro pairings should be > 0: {bis_sub}"


def test_villes_derived_nonzero(data):
    """Villes derived features should be non-zero with known placements."""
    state = _make_state_with_placements(data)
    vec = encode_state(state, 0, data)
    vil_start = _BASE_SIZE + 16 + 12 + 12 + 5 + 6 + 8  # after bistro derived
    vil_sub = vec[vil_start: vil_start + 36]
    # At least some region should show non-zero self-influence
    assert np.any(vil_sub > 0), f"Villes derived features all zero: {vil_sub}"


def test_enhanced_values_in_unit_interval_with_placements(data):
    """All features must remain in [0, 1] even with placements."""
    state = _make_state_with_placements(data)
    for player_id in range(4):
        vec = encode_state(state, player_id, data)
        assert np.all(vec >= 0.0), f"Player {player_id}: min {vec.min()}"
        assert np.all(vec <= 1.0), f"Player {player_id}: max {vec.max()}"
