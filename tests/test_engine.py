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
    apply_turn,
    apply_unlock_structure,
    gain_resource,
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
from src.game.actions import TurnAction, UnlockStructureAction


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
    """Worker return_after_rotation = (rotation_index + space.turns) % 4."""
    action = GatherAction(resource_space=AgeType.SILVER)
    new = apply_gather(state, 0, action, data)
    deployed = [w for w in new.players[0].workers
                if w.location == WorkerLocation.ON_RESOURCE_TILE]
    assert len(deployed) == 1
    assert deployed[0].return_after_rotation == (state.rotation_index + AgeType.SILVER.turns) % 4
    assert deployed[0].space_id == AgeType.SILVER.turns


def test_gather_adds_resources(data, state):
    """Gathering Gold space adds 3 resources of the facing type (before greenhouse)."""
    resource = state.resource_facing(0)
    before = state.players[0].resources.get(resource, 0)
    new = apply_gather(state, 0, GatherAction(resource_space=AgeType.GOLD), data)
    after = new.players[0].resources.get(resource, 0)
    # At least +3; greenhouse may add 1 more
    assert after >= before + 3


def test_gather_does_not_mutate_input(data, state):
    original = dict(state.players[0].resources)
    apply_gather(state, 0, GatherAction(resource_space=AgeType.BRONZE), data)
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

def test_milking_parlour_increments_use_count_and_allows_reuse(data, state):
    """Milking parlour increments the use count and can be used more than once."""
    new = copy.deepcopy(state)
    player = new.players[0]
    parlours = [p for p in data.milking_parlours if p.board_id == player.board_id]
    if not parlours:
        pytest.skip("No parlours for this player board")
    parlour = parlours[0]
    player.resources[ResourceType.LIVESTOCK] = parlour.livestock_cost * 3 + 10
    player.resources[ResourceType.FRUIT] = 5
    player.cheese_tokens_remaining = 10

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
    assert new2.players[0].milking_parlours_used[parlour.parlour_num - 1] == 1

    # Use a different target space so the second use doesn't collide
    other_spaces = [s for s in data.fromagerie_spaces
                    if s.cheese_type == cheese_type and s.age == age and s.space_id != target_sid]
    if not other_spaces:
        pytest.skip("No second matching fromagerie space for reuse test")
    action2 = MilkingParlourAction(
        parlour_num=parlour.parlour_num,
        chosen_cheese_type=cheese_type,
        chosen_age=age,
        target_venue=VenueType.FROMAGERIE,
        target_space_id=other_spaces[0].space_id,
    )
    new3 = apply_milking_parlour(new2, 0, action2, data)
    assert new3.players[0].milking_parlours_used[parlour.parlour_num - 1] == 2


# ---------------------------------------------------------------------------
# apply_unlock_structure (req 4.7.2)
# ---------------------------------------------------------------------------

def test_apply_unlock_structure_happy_path(data, state):
    """Unlocking slot 1 deducts the correct cost and sets the flag."""
    new = copy.deepcopy(state)
    player = new.players[0]
    board = next(b for b in data.player_board_structures if b.board_id == player.board_id)
    cost = board.structure_costs[0]
    player.resources[ResourceType.STRUCTURE] = cost + 5

    action = UnlockStructureAction(slot=1)
    new2 = apply_unlock_structure(new, 0, action, data)

    assert new2.players[0].structures_unlocked[0] is True
    assert new2.players[0].resources[ResourceType.STRUCTURE] == 5


def test_apply_unlock_structure_already_unlocked_raises(data, state):
    """Attempting to unlock an already-unlocked slot raises IllegalActionError."""
    new = copy.deepcopy(state)
    player = new.players[0]
    board = next(b for b in data.player_board_structures if b.board_id == player.board_id)
    player.resources[ResourceType.STRUCTURE] = 20
    player.structures_unlocked[0] = True

    with pytest.raises(IllegalActionError):
        apply_unlock_structure(new, 0, UnlockStructureAction(slot=1), data)


def test_apply_unlock_structure_insufficient_resources_raises(data, state):
    """Not enough Structure tokens raises IllegalActionError."""
    new = copy.deepcopy(state)
    new.players[0].resources[ResourceType.STRUCTURE] = 0

    with pytest.raises(IllegalActionError):
        apply_unlock_structure(new, 0, UnlockStructureAction(slot=1), data)


# ---------------------------------------------------------------------------
# Barn (req 4.7.2)
# ---------------------------------------------------------------------------

def test_apply_barn_via_turn_gains_resource_and_deploys_worker(data, state):
    """apply_turn with use_barn=True gains the board's barn resource and deploys a worker."""
    new = copy.deepcopy(state)
    player = new.players[0]
    player.structures_unlocked[0] = True  # unlock barn
    _give_all_workers_in_hand(player)

    board = next(b for b in data.player_board_structures if b.board_id == player.board_id)
    barn_res = board.barn_resource

    if barn_res == ResourceType.ORDER:
        before = len(player.order_cards_held)
        new2 = apply_turn(new, 0, TurnAction(use_barn=True), data)
        assert len(new2.players[0].order_cards_held) == before + 1
    else:
        before = player.resources.get(barn_res, 0)
        new2 = apply_turn(new, 0, TurnAction(use_barn=True), data)
        assert new2.players[0].resources.get(barn_res, 0) == before + 1

    barn_workers = [w for w in new2.players[0].workers
                    if w.location.name == "ON_BARN"]
    assert len(barn_workers) == 1


def test_apply_barn_raises_when_not_unlocked(data, state):
    """Using the barn without unlocking it raises IllegalActionError."""
    new = copy.deepcopy(state)
    new.players[0].structures_unlocked[0] = False

    with pytest.raises(IllegalActionError):
        apply_turn(new, 0, TurnAction(use_barn=True), data)


# ---------------------------------------------------------------------------
# Loading Dock trigger (req 4.7.2)
# ---------------------------------------------------------------------------

def test_loading_dock_triggers_on_matching_venue(data, state):
    """Placing cheese at the loading dock's venue rewards 1 unit of the dock resource."""
    new = copy.deepcopy(state)
    player = new.players[0]
    board = next(b for b in data.player_board_structures if b.board_id == player.board_id)

    # Rotate until player 0 faces the loading dock venue
    while new.venue_facing(0) != board.loading_dock_venue:
        new = rotate_board(new)

    player = new.players[0]
    player.structures_unlocked[1] = True  # unlock loading dock
    _give_all_workers_in_hand(player)
    player.resources[ResourceType.FRUIT] = 10

    # Pick any legal space at the loading dock venue
    if board.loading_dock_venue == VenueType.FROMAGERIE:
        sp = data.fromagerie_spaces[0]
        action = MakeCheeseAction(venue=VenueType.FROMAGERIE, worker_type=sp.cheese_type,
                                   space_id=sp.space_id)
    elif board.loading_dock_venue == VenueType.VILLES:
        sp = data.villes_spaces[0]
        action = MakeCheeseAction(venue=VenueType.VILLES, worker_type=sp.cheese_type,
                                   space_id=sp.space_id)
    elif board.loading_dock_venue == VenueType.BISTRO:
        sp = data.bistro_spaces[0]
        action = MakeCheeseAction(venue=VenueType.BISTRO, worker_type=sp.cheese_type,
                                   space_id=sp.space_id)
    else:
        # Festival
        cheese_sp = next(s for s in data.festival_spaces
                         if s.space_type.name == "CHEESE")
        action = MakeCheeseAction(venue=VenueType.FESTIVAL, worker_type=cheese_sp.cheese_type,
                                   row=cheese_sp.row, col=cheese_sp.col)

    dock_res = board.loading_dock_reward
    before = player.resources.get(dock_res, 0)

    new2 = apply_make_cheese(new, 0, action, data)
    after = new2.players[0].resources.get(dock_res, 0)

    assert after == before + 1


# ---------------------------------------------------------------------------
# Fromagerie shelf bonuses (req 4.7.2)
# ---------------------------------------------------------------------------

def test_fromagerie_shelf_bonus_gain_1_resource_any(data, state):
    """Placing on a 'gain_1_resource_any' shelf (shelf 2) grants +1 STRUCTURE."""
    # Space IDs 4–6 are on shelf 2 (Silver, gain_1_resource_any)
    sp = next(s for s in data.fromagerie_spaces if s.shelf_id == 2
              and s.fruit_requirement.name == "NONE")

    new = copy.deepcopy(state)
    new = _force_fromagerie(new, data)
    player = new.players[0]
    _give_all_workers_in_hand(player)
    player.resources[ResourceType.FRUIT] = 5
    before_struct = player.resources.get(ResourceType.STRUCTURE, 0)

    action = MakeCheeseAction(venue=VenueType.FROMAGERIE, worker_type=sp.cheese_type,
                               space_id=sp.space_id)
    new2 = apply_make_cheese(new, 0, action, data)

    assert new2.players[0].resources.get(ResourceType.STRUCTURE, 0) == before_struct + 1


def test_fromagerie_shelf_bonus_gain_2_diff_resources(data, state):
    """Placing on a 'gain_2_diff_resources' shelf (shelf 3) grants +1 STRUCTURE and +1 LIVESTOCK."""
    # Space IDs 7–9 are on shelf 3 (Gold, gain_2_diff_resources)
    sp = next(s for s in data.fromagerie_spaces if s.shelf_id == 3
              and s.fruit_requirement.name == "NONE")

    new = copy.deepcopy(state)
    new = _force_fromagerie(new, data)
    player = new.players[0]
    _give_all_workers_in_hand(player)
    player.resources[ResourceType.FRUIT] = 5
    before_struct = player.resources.get(ResourceType.STRUCTURE, 0)
    before_live = player.resources.get(ResourceType.LIVESTOCK, 0)

    action = MakeCheeseAction(venue=VenueType.FROMAGERIE, worker_type=sp.cheese_type,
                               space_id=sp.space_id)
    new2 = apply_make_cheese(new, 0, action, data)

    assert new2.players[0].resources.get(ResourceType.STRUCTURE, 0) == before_struct + 1
    assert new2.players[0].resources.get(ResourceType.LIVESTOCK, 0) == before_live + 1


# ---------------------------------------------------------------------------
# gain_resource — ORDER draw (req 4.7.2)
# ---------------------------------------------------------------------------

def test_gain_resource_order_draws_from_deck(data, state):
    """gain_resource with ORDER draws cards from the deck into the player's hand."""
    new = copy.deepcopy(state)
    player = new.players[0]
    before_held = len(player.order_cards_held)
    before_deck = len(new.order_card_deck)

    new2 = gain_resource(new, 0, ResourceType.ORDER, 2, data)

    assert len(new2.players[0].order_cards_held) == before_held + 2
    assert len(new2.order_card_deck) == before_deck - 2


def test_gain_resource_does_not_mutate_input(data, state):
    """gain_resource returns a new state without mutating the original."""
    original_deck_len = len(state.order_card_deck)
    gain_resource(state, 0, ResourceType.ORDER, 1, data)
    assert len(state.order_card_deck) == original_deck_len


# ---------------------------------------------------------------------------
# apply_turn composition (req 4.7.2)
# ---------------------------------------------------------------------------

def test_apply_turn_gather_and_make_cheese(data, state):
    """apply_turn with both gather and make_cheese applies both sub-actions."""
    new = copy.deepcopy(state)
    new = _force_fromagerie(new, data)
    player = new.players[0]
    _give_all_workers_in_hand(player)
    player.resources[ResourceType.FRUIT] = 10
    before_tokens = player.cheese_tokens_remaining

    # Gather takes the first in-hand worker; pick a cheese space matching a different worker type
    gather_type = player.workers[0].cheese_type
    remaining_types = {w.cheese_type for w in player.workers[1:]}
    sp = next(s for s in data.fromagerie_spaces
              if s.fruit_requirement.name == "NONE" and s.cheese_type in remaining_types)

    gather = GatherAction(resource_space=AgeType.BRONZE)
    make = MakeCheeseAction(venue=VenueType.FROMAGERIE, worker_type=sp.cheese_type,
                             space_id=sp.space_id)

    new2 = apply_turn(new, 0, TurnAction(gather=gather, make_cheese=[make]), data)

    # Token was placed
    assert new2.players[0].cheese_tokens_remaining == before_tokens - 1
    # At least one worker is on resource tile
    on_tile = [w for w in new2.players[0].workers
               if w.location == WorkerLocation.ON_RESOURCE_TILE]
    assert len(on_tile) == 1


def test_apply_turn_too_many_make_cheese_raises(data, state):
    """TurnAction with two make_cheese actions raises IllegalActionError."""
    new = copy.deepcopy(state)
    new = _force_fromagerie(new, data)
    _give_all_workers_in_hand(new.players[0])
    new.players[0].resources[ResourceType.FRUIT] = 10

    sp1 = data.fromagerie_spaces[0]
    sp2 = data.fromagerie_spaces[1]
    mc1 = MakeCheeseAction(venue=VenueType.FROMAGERIE, worker_type=sp1.cheese_type,
                            space_id=sp1.space_id)
    mc2 = MakeCheeseAction(venue=VenueType.FROMAGERIE, worker_type=sp2.cheese_type,
                            space_id=sp2.space_id)

    with pytest.raises(IllegalActionError):
        apply_turn(new, 0, TurnAction(make_cheese=[mc1, mc2]), data)


# ---------------------------------------------------------------------------
# Error cases (req 4.7.2)
# ---------------------------------------------------------------------------

def test_make_cheese_raises_when_no_tokens_remaining(data, state):
    """apply_make_cheese raises IllegalActionError if the player has no tokens left."""
    new = copy.deepcopy(state)
    new = _force_fromagerie(new, data)
    player = new.players[0]
    _give_all_workers_in_hand(player)
    player.cheese_tokens_remaining = 0
    player.resources[ResourceType.FRUIT] = 5

    sp = data.fromagerie_spaces[0]
    action = MakeCheeseAction(venue=VenueType.FROMAGERIE, worker_type=sp.cheese_type,
                               space_id=sp.space_id)
    with pytest.raises(IllegalActionError):
        apply_make_cheese(new, 0, action, data)


# ---------------------------------------------------------------------------
# Fromagerie shelf 1 swap (trade_resource_for_any)
# ---------------------------------------------------------------------------

def test_fromagerie_shelf_bonus_trade_resource_for_any(data, state):
    """Swap: give 1 STRUCTURE, receive 1 LIVESTOCK on shelf 1."""
    new = copy.deepcopy(state)
    new = _force_fromagerie(new, data)
    player = new.players[0]
    _give_all_workers_in_hand(player)

    # Shelf 1 spaces are space_id 1, 2, 3.  Pick space 1 (Soft, Bronze, no fruit).
    sp = next(s for s in data.fromagerie_spaces if s.space_id == 1)
    player.resources[ResourceType.FRUIT] = 5
    player.resources[ResourceType.STRUCTURE] = 3
    player.resources[ResourceType.LIVESTOCK] = 0

    action = MakeCheeseAction(
        venue=VenueType.FROMAGERIE, worker_type=sp.cheese_type, space_id=sp.space_id,
        resource_to_give=ResourceType.STRUCTURE, resource_to_receive=ResourceType.LIVESTOCK,
    )
    new2 = apply_make_cheese(new, 0, action, data)
    assert new2.players[0].resources[ResourceType.STRUCTURE] == 2  # 3 - 1
    assert new2.players[0].resources[ResourceType.LIVESTOCK] >= 1  # 0 + 1 (greenhouse may add more)


def test_fromagerie_swap_no_op_when_fields_none(data, state):
    """No resource change from swap when give/receive are None."""
    new = copy.deepcopy(state)
    new = _force_fromagerie(new, data)
    player = new.players[0]
    _give_all_workers_in_hand(player)

    sp = next(s for s in data.fromagerie_spaces if s.space_id == 1)
    player.resources[ResourceType.FRUIT] = 5
    player.resources[ResourceType.STRUCTURE] = 3
    player.resources[ResourceType.LIVESTOCK] = 2

    action = MakeCheeseAction(
        venue=VenueType.FROMAGERIE, worker_type=sp.cheese_type, space_id=sp.space_id,
        resource_to_give=None, resource_to_receive=None,
    )
    new2 = apply_make_cheese(new, 0, action, data)
    # Structure and livestock should be unchanged by the swap
    assert new2.players[0].resources[ResourceType.STRUCTURE] == 3
    assert new2.players[0].resources[ResourceType.LIVESTOCK] == 2


def test_milking_parlour_raises_when_insufficient_livestock(data, state):
    """apply_milking_parlour raises IllegalActionError if livestock is insufficient."""
    new = copy.deepcopy(state)
    player = new.players[0]
    parlours = [p for p in data.milking_parlours if p.board_id == player.board_id]
    if not parlours:
        pytest.skip("No parlours for this player board")
    parlour = parlours[0]
    player.resources[ResourceType.LIVESTOCK] = 0

    sp = data.fromagerie_spaces[0]
    action = MilkingParlourAction(
        parlour_num=parlour.parlour_num,
        chosen_cheese_type=sp.cheese_type,
        chosen_age=sp.age,
        target_venue=VenueType.FROMAGERIE,
        target_space_id=sp.space_id,
    )
    with pytest.raises(IllegalActionError):
        apply_milking_parlour(new, 0, action, data)
