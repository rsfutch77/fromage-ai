"""Tests for board.py: rotate_board, retrieve_workers, setup_game, and GameState serialisation.

See 2-requirements.md requirements 2.5.1–2.5.5.
"""

import copy
import pytest

from src.game.board import rotate_board, retrieve_workers, setup_game, is_game_over
from src.game.data_loader import GameDataLoader
from src.game.state import GameState
from src.game.types import ResourceType, VenueType, WorkerLocation


@pytest.fixture(scope="module")
def loader() -> GameDataLoader:
    return GameDataLoader()


@pytest.fixture(scope="module")
def initial_state(loader) -> GameState:
    return setup_game(loader, seed=0)


# ---------------------------------------------------------------------------
# rotate_board (req 2.5.1)
# ---------------------------------------------------------------------------

def test_rotate_increments_rotation_index(initial_state):
    s2 = rotate_board(initial_state)
    assert s2.rotation_index == (initial_state.rotation_index + 1) % 4


def test_rotate_wraps_at_4(initial_state):
    s = initial_state
    for _ in range(4):
        s = rotate_board(s)
    assert s.rotation_index == initial_state.rotation_index


def test_rotate_does_not_mutate_original(initial_state):
    original_rot = initial_state.rotation_index
    rotate_board(initial_state)
    assert initial_state.rotation_index == original_rot


# ---------------------------------------------------------------------------
# retrieve_workers (req 2.5.2)
# ---------------------------------------------------------------------------

def test_retrieve_workers_returns_due_worker(loader):
    state = setup_game(loader, seed=1)
    player = state.players[0]
    worker = player.workers[0]
    worker.location = WorkerLocation.ON_RESOURCE_TILE
    worker.venue = None
    worker.space_id = 1
    worker.return_after_rotation = state.rotation_index

    retrieved = retrieve_workers(state)
    retrieved_worker = retrieved.players[0].workers[0]
    assert retrieved_worker.location == WorkerLocation.IN_HAND
    assert retrieved_worker.venue is None
    assert retrieved_worker.space_id is None
    assert retrieved_worker.return_after_rotation is None


def test_retrieve_workers_leaves_other_workers(loader):
    state = setup_game(loader, seed=2)
    player = state.players[0]
    player.workers[0].location = WorkerLocation.ON_RESOURCE_TILE
    player.workers[0].return_after_rotation = state.rotation_index

    player.workers[1].location = WorkerLocation.ON_CHEESE_SPACE
    player.workers[1].return_after_rotation = (state.rotation_index + 1) % 4

    retrieved = retrieve_workers(state)
    assert retrieved.players[0].workers[0].location == WorkerLocation.IN_HAND
    assert retrieved.players[0].workers[1].location == WorkerLocation.ON_CHEESE_SPACE


# ---------------------------------------------------------------------------
# setup_game (req 2.5.3)
# ---------------------------------------------------------------------------

def test_setup_game_has_4_players(loader):
    assert len(setup_game(loader, seed=10).players) == 4


def test_setup_game_3_workers_each(loader):
    state = setup_game(loader, seed=10)
    for player in state.players:
        assert len(player.workers) == 3


def test_setup_game_15_cheese_tokens_each(loader):
    state = setup_game(loader, seed=10)
    for player in state.players:
        assert player.cheese_tokens_remaining == 15


def test_setup_game_correct_starting_resources_seed_0(loader):
    state = setup_game(loader, seed=0)
    for player in state.players:
        total = sum(player.resources.values())
        assert total == 3, f"Player {player.player_id} has {total} resources (expected 3)"


def test_setup_game_correct_starting_resources_seed_99(loader):
    state = setup_game(loader, seed=99)
    for player in state.players:
        total = sum(player.resources.values())
        assert total == 3


def test_setup_game_same_seed_reproducible(loader):
    s_a = setup_game(loader, seed=42)
    s_b = setup_game(loader, seed=42)
    assert s_a.resource_tile_orientation == s_b.resource_tile_orientation
    assert [p.board_id for p in s_a.players] == [p.board_id for p in s_b.players]
    assert [c.cheese_type for c in s_a.order_card_deck] == [c.cheese_type for c in s_b.order_card_deck]


# ---------------------------------------------------------------------------
# JSON round-trip (req 2.5.4)
# ---------------------------------------------------------------------------

def test_json_roundtrip_preserves_rotation(initial_state):
    back = GameState.from_json(initial_state.to_json())
    assert back.rotation_index == initial_state.rotation_index


def test_json_roundtrip_preserves_players(initial_state):
    back = GameState.from_json(initial_state.to_json())
    assert len(back.players) == len(initial_state.players)


def test_json_roundtrip_preserves_resources(initial_state):
    back = GameState.from_json(initial_state.to_json())
    for pid in range(4):
        assert back.players[pid].resources == initial_state.players[pid].resources


def test_json_roundtrip_preserves_deck(initial_state):
    back = GameState.from_json(initial_state.to_json())
    assert len(back.order_card_deck) == len(initial_state.order_card_deck)
    for orig, restored in zip(initial_state.order_card_deck, back.order_card_deck):
        assert orig.cheese_type == restored.cheese_type
        assert orig.age == restored.age


def test_json_roundtrip_preserves_workers(initial_state):
    back = GameState.from_json(initial_state.to_json())
    for pid in range(4):
        orig_w = initial_state.players[pid].workers
        back_w = back.players[pid].workers
        assert len(orig_w) == len(back_w)
        for ow, bw in zip(orig_w, back_w):
            assert ow.cheese_type == bw.cheese_type
            assert ow.location == bw.location


def test_from_json_raises_on_malformed():
    with pytest.raises(ValueError):
        GameState.from_json("not valid json{{{")


# ---------------------------------------------------------------------------
# venue_facing and resource_facing (req 2.5.5)
# ---------------------------------------------------------------------------

def test_venue_facing_covers_all_venues_across_rotations(loader):
    """All 4 venues appear exactly once across 4 players at any given rotation."""
    state = setup_game(loader, seed=5)
    for rot in range(4):
        s = copy.deepcopy(state)
        s.rotation_index = rot
        seen = {s.venue_facing(pid) for pid in range(4)}
        assert seen == set(VenueType), f"Not all venues seen at rotation {rot}: {seen}"


def test_resource_facing_covers_all_resources(loader):
    """All 4 resources appear exactly once across 4 players at any orientation."""
    state = setup_game(loader, seed=5)
    seen = {state.resource_facing(pid) for pid in range(4)}
    assert seen == set(ResourceType)


def test_venue_facing_changes_with_rotation(loader):
    state = setup_game(loader, seed=5)
    venue_rot0 = state.venue_facing(0)
    s2 = copy.deepcopy(state)
    s2.rotation_index = 1
    venue_rot1 = s2.venue_facing(0)
    assert venue_rot0 != venue_rot1


# ---------------------------------------------------------------------------
# Customer token randomisation (stretch goal 1)
# ---------------------------------------------------------------------------

def test_customer_tokens_stored_on_state(loader):
    state = setup_game(loader, seed=0)
    assert len(state.customer_tokens) == 6
    # Region names are preserved (positions stay the same)
    region_names = {ct.region_name for ct in state.customer_tokens}
    assert region_names == {"purple", "blue", "green", "white", "yellow", "pink"}


def test_customer_tokens_same_seed_reproducible(loader):
    s_a = setup_game(loader, seed=42)
    s_b = setup_game(loader, seed=42)
    vals_a = [(ct.region_name, ct.win_value) for ct in s_a.customer_tokens]
    vals_b = [(ct.region_name, ct.win_value) for ct in s_b.customer_tokens]
    assert vals_a == vals_b


def test_customer_tokens_different_seeds_differ(loader):
    """Run 10 seeds; assert not all produce the same token arrangement."""
    arrangements = []
    for seed in range(10):
        state = setup_game(loader, seed=seed)
        arrangement = tuple(ct.win_value for ct in state.customer_tokens)
        arrangements.append(arrangement)
    assert len(set(arrangements)) > 1, "All 10 seeds produced identical token arrangements"


def test_customer_tokens_values_conserved(loader):
    """Point values are shuffled, not lost — same multiset every game."""
    original_values = sorted([7, 7, 8, 8, 9, 9])
    for seed in range(5):
        state = setup_game(loader, seed=seed)
        actual = sorted(ct.win_value for ct in state.customer_tokens)
        assert actual == original_values, f"Seed {seed}: values {actual} != {original_values}"
