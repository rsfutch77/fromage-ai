"""Tests for the engine module. See 2-requirements.md section 4.7.2."""

import copy

import pytest

from src.game.actions import GatherAction, MakeCheeseAction, MilkingParlourAction
from src.game.board import rotate_board, setup_game
from src.game.data_loader import GameDataLoader, OrderCard
from src.game.engine import (
    _TurnCtx,
    _gain_resource_inplace,
    apply_gather,
    apply_make_cheese,
    apply_milking_parlour,
    apply_unlock_structure,
)
from src.game.types import (
    AgeType,
    CheeseType,
    FruitRequirement,
    IllegalActionError,
    ResourceType,
    VenueType,
    WorkerLocation,
)
from src.game.actions import UnlockStructureAction


@pytest.fixture
def data():
    return GameDataLoader()


@pytest.fixture
def state(data):
    return setup_game(data, seed=42)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _force_fromagerie(state, data):
    """Rotate board until player 0 faces Fromagerie."""
    while state.venue_facing(0) != VenueType.FROMAGERIE:
        state = rotate_board(state)
    return state


def _give_all_workers_in_hand(player):
    for w in player.workers:
        w.location = WorkerLocation.IN_HAND
        w.venue = None
        w.space_id = None
        w.return_after_rotation = None


# ---------------------------------------------------------------------------
# Gather tests (req 4.7.2 – gather correctly sets worker return rotation & adds resources)
# ---------------------------------------------------------------------------

def test_gather_sets_worker_return_rotation(data, state):
    """Worker return_after_rotation = (rotation_index + space) % 4."""
    action = GatherAction(resource_space=2)
    new = apply_gather(state, 0, action, data)
    deployed = [w for w in new.players[0].workers
                if w.location == WorkerLocation.ON_RESOURCE_TILE]
    assert len(deployed) == 1
    assert deployed[0].return_after_rotation == (state.rotation_index + 2) % 4
    assert deployed[0].space_id == 2


def test_gather_adds_resources(data, state):
    """Gathering space N adds N resources of the facing type (before greenhouse)."""
    resource = state.resource_facing(0)
    before = state.players[0].resources.get(resource, 0)
    new = apply_gather(state, 0, GatherAction(resource_space=3), data)
    after = new.players[0].resources.get(resource, 0)
    # At least +3; greenhouse may add 1 more
    assert after >= before + 3


def test_gather_does_not_mutate_input(data, state):
    original = dict(state.players[0].resources)
    apply_gather(state, 0, GatherAction(resource_space=1), data)
    assert state.players[0].resources == original


# ---------------------------------------------------------------------------
# Make-cheese fruit deduction (req 4.7.2)
# ---------------------------------------------------------------------------

def test_make_cheese_deducts_fruit_for_fruited_space(data, state):
    """Placing on a fruited space deducts 1 Fruit and increments fruit_spent_on_fruited."""
    fruited = [sp for sp in data.fromagerie_spaces
               if sp.fruit_requirement == FruitRequirement.FRUIT]
    if not fruited:
        pytest.skip("No fruited Fromagerie spaces in test data")
    sp = fruited[0]

    new = copy.deepcopy(state)
    new = _force_fromagerie(new, data)
    player = new.players[0]
    _give_all_workers_in_hand(player)
    player.resources[ResourceType.FRUIT] = 5

    action = MakeCheeseAction(venue=VenueType.FROMAGERIE, worker_type=sp.cheese_type,
                               space_id=sp.space_id)
    new2 = apply_make_cheese(new, 0, action, data)
    assert new2.players[0].resources[ResourceType.FRUIT] == 4
    assert new2.players[0].fruit_spent_on_fruited == 1


def test_make_cheese_deducts_fruit_for_jam_space(data, state):
    """Placing on a jam space deducts 1 Fruit and increments fruit_spent_on_jam."""
    jam_spaces = [sp for sp in data.fromagerie_spaces
                  if sp.fruit_requirement == FruitRequirement.JAM]
    if not jam_spaces:
        pytest.skip("No jam Fromagerie spaces in test data")
    sp = jam_spaces[0]

    new = copy.deepcopy(state)
    new = _force_fromagerie(new, data)
    player = new.players[0]
    _give_all_workers_in_hand(player)
    player.resources[ResourceType.FRUIT] = 5

    action = MakeCheeseAction(venue=VenueType.FROMAGERIE, worker_type=sp.cheese_type,
                               space_id=sp.space_id)
    new2 = apply_make_cheese(new, 0, action, data)
    assert new2.players[0].resources[ResourceType.FRUIT] == 4
    assert new2.players[0].fruit_spent_on_jam == 1


# ---------------------------------------------------------------------------
# Order completion (req 4.7.2)
# ---------------------------------------------------------------------------

def test_order_completion_triggers_on_matching_cheese(data, state):
    """Order card moves to orders_completed when placed cheese matches."""
    new = copy.deepcopy(state)
    new = _force_fromagerie(new, data)
    sp = data.fromagerie_spaces[0]
    player = new.players[0]
    _give_all_workers_in_hand(player)
    player.resources[ResourceType.FRUIT] = 5
    player.order_cards_held = [OrderCard(cheese_type=sp.cheese_type, age=sp.age)]
    player.orders_completed = []

    action = MakeCheeseAction(venue=VenueType.FROMAGERIE, worker_type=sp.cheese_type,
                               space_id=sp.space_id)
    new2 = apply_make_cheese(new, 0, action, data)
    assert len(new2.players[0].orders_completed) == 1
    assert len(new2.players[0].order_cards_held) == 0


# ---------------------------------------------------------------------------
# game_end_triggered (req 4.7.2)
# ---------------------------------------------------------------------------

def test_game_end_triggered_on_last_token(data, state):
    """game_end_triggered is set when player places their last token."""
    new = copy.deepcopy(state)
    new = _force_fromagerie(new, data)
    sp = data.fromagerie_spaces[0]
    player = new.players[0]
    player.cheese_tokens_remaining = 1
    _give_all_workers_in_hand(player)
    player.resources[ResourceType.FRUIT] = 5

    action = MakeCheeseAction(venue=VenueType.FROMAGERIE, worker_type=sp.cheese_type,
                               space_id=sp.space_id)
    new2 = apply_make_cheese(new, 0, action, data)
    assert new2.game_end_triggered is True


# ---------------------------------------------------------------------------
# Greenhouse (req 4.7.2)
# ---------------------------------------------------------------------------

def test_greenhouse_fires_once_per_turn(data, state):
    """Greenhouse adds +1 resource and does NOT fire twice in the same turn context."""
    board_struct = next(b for b in data.player_board_structures
                        if b.board_id == state.players[0].board_id)
    gh_res = board_struct.greenhouse_resource

    new = copy.deepcopy(state)
    player = new.players[0]
    player.structures_unlocked[2] = True  # unlock greenhouse
    player.resources[gh_res] = 0

    ctx = _TurnCtx()
    _gain_resource_inplace(new, 0, gh_res, 1, data, ctx)  # fires greenhouse
    _gain_resource_inplace(new, 0, gh_res, 1, data, ctx)  # should NOT fire again

    # Expected: 1 + 1(greenhouse) + 1 = 3 (not 4)
    assert new.players[0].resources[gh_res] == 3


# ---------------------------------------------------------------------------
# Milking parlour slot-used flag (req 4.7.2)
# ---------------------------------------------------------------------------

def test_milking_parlour_marks_used_and_raises_on_reuse(data, state):
    """Milking parlour marks slot used and raises IllegalActionError on reuse."""
    new = copy.deepcopy(state)
    player = new.players[0]
    parlours = [p for p in data.milking_parlours if p.board_id == player.board_id]
    if not parlours:
        pytest.skip("No parlours for this player board")
    parlour = parlours[0]
    player.resources[ResourceType.LIVESTOCK] = parlour.livestock_cost + 10
    player.resources[ResourceType.FRUIT] = 5  # cover any fruit requirement on the target space

    # Build a target space
    cheese_type = parlour.bonus_cheese_type
    age = parlour.bonus_cheese_age
    if cheese_type is None:
        sp = data.fromagerie_spaces[0]
        cheese_type, age = sp.cheese_type, sp.age
        target_sid = sp.space_id
    else:
        matching = [s for s in data.fromagerie_spaces
                    if s.cheese_type == cheese_type and s.age == age]
        if not matching:
            pytest.skip("No matching fromagerie space")
        target_sid = matching[0].space_id

    action = MilkingParlourAction(
        parlour_num=parlour.parlour_num,
        chosen_cheese_type=cheese_type,
        chosen_age=age,
        target_venue=VenueType.FROMAGERIE,
        target_space_id=target_sid,
    )
    new2 = apply_milking_parlour(new, 0, action, data)
    assert new2.players[0].milking_parlours_used[parlour.parlour_num - 1] is True

    with pytest.raises(IllegalActionError):
        apply_milking_parlour(new2, 0, action, data)
