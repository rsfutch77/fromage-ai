"""Game action application: apply each action type to GameState.

Functions: gain_resource, apply_gather, apply_make_cheese,
apply_milking_parlour, apply_unlock_structure, apply_turn.
Handles triggered effects: Greenhouse, Loading Dock, order completion.

See requirements section 4.

NOTE — Fromagerie resource-bonus shelf bonuses (trade_resource_for_any,
gain_1_resource_any, gain_2_diff_resources) require player choices that are
not encoded in MakeCheeseAction.  In this simulation these are handled with a
deterministic fallback (see _apply_fromagerie_shelf_bonus).  The choices can
be exposed to a UI in a later milestone.
"""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING

from src.game.types import (
    FruitRequirement,
    IllegalActionError,
    ResourceType,
    VenueType,
    WorkerLocation,
)

if TYPE_CHECKING:
    from src.game.actions import GatherAction, MakeCheeseAction, MilkingParlourAction, TurnAction, UnlockStructureAction
    from src.game.data_loader import (
        BistroSpace,
        FestivalSpace,
        FromagerieShelf,
        FromagerieSpace,
        GameDataLoader,
        MilkingParlour,
        VillesSpace,
    )
    from src.game.state import GameState, PlacedCheese, PlayerState

logger = logging.getLogger(__name__)

# Structure slot indices (0-based into structures_unlocked list)
_BARN_IDX = 0
_LOADING_DOCK_IDX = 1
_GREENHOUSE_IDX = 2
_HQ_IDX = 3


# ---------------------------------------------------------------------------
# Transient turn context (not stored in GameState)
# ---------------------------------------------------------------------------

class _TurnCtx:
    """Tracks one-per-turn trigger flags; passed through inplace helpers."""
    __slots__ = ["greenhouse_fired"]

    def __init__(self) -> None:
        self.greenhouse_fired: bool = False


# ---------------------------------------------------------------------------
# Private lookup helpers
# ---------------------------------------------------------------------------

def _get_fromagerie_space(data: GameDataLoader, space_id: int) -> FromagerieSpace:
    for sp in data.fromagerie_spaces:
        if sp.space_id == space_id:
            return sp
    raise IllegalActionError(f"Fromagerie space {space_id} not found")


def _get_bistro_space(data: GameDataLoader, space_id: int) -> BistroSpace:
    for sp in data.bistro_spaces:
        if sp.space_id == space_id:
            return sp
    raise IllegalActionError(f"Bistro space {space_id} not found")


def _get_villes_space(data: GameDataLoader, space_id: int) -> VillesSpace:
    for sp in data.villes_spaces:
        if sp.space_id == space_id:
            return sp
    raise IllegalActionError(f"Villes space {space_id} not found")


def _get_festival_space(data: GameDataLoader, row: int, col: int) -> FestivalSpace:
    for sp in data.festival_spaces:
        if sp.row == row and sp.col == col:
            return sp
    raise IllegalActionError(f"Festival space ({row},{col}) not found")


def _get_fromagerie_shelf(data: GameDataLoader, shelf_id: int) -> FromagerieShelf:
    for sh in data.fromagerie_shelves:
        if sh.shelf_id == shelf_id:
            return sh
    raise IllegalActionError(f"Fromagerie shelf {shelf_id} not found")


def _get_board_struct(data: GameDataLoader, board_id: int):
    for bs in data.player_board_structures:
        if bs.board_id == board_id:
            return bs
    raise IllegalActionError(f"Board structure {board_id} not found")


def _get_milking_parlour(data: GameDataLoader, board_id: int, parlour_num: int) -> MilkingParlour:
    for p in data.milking_parlours:
        if p.board_id == board_id and p.parlour_num == parlour_num:
            return p
    raise IllegalActionError(f"Milking parlour {parlour_num} on board {board_id} not found")


# ---------------------------------------------------------------------------
# Private inplace helpers (mutate an already-copied GameState)
# ---------------------------------------------------------------------------

def _gain_resource_inplace(
    state: GameState,
    player_id: int,
    resource: ResourceType,
    amount: int,
    data: GameDataLoader,
    ctx: _TurnCtx,
) -> None:
    """Mutate *state* in place: add *amount* of *resource* to player; handle ORDER draw
    and Greenhouse trigger."""
    player = state.players[player_id]
    if resource == ResourceType.ORDER:
        drawn = state.order_card_deck[:amount]
        state.order_card_deck = state.order_card_deck[amount:]
        player.order_cards_held.extend(drawn)
    else:
        player.resources[resource] = player.resources.get(resource, 0) + amount

        # Greenhouse: if unlocked and resource matches board's greenhouse_resource,
        # add 1 extra unit (at most once per turn).
        if not ctx.greenhouse_fired and player.structures_unlocked[_GREENHOUSE_IDX]:
            board_struct = _get_board_struct(data, player.board_id)
            if resource == board_struct.greenhouse_resource:
                ctx.greenhouse_fired = True
                player.resources[resource] += 1
                logger.debug("Greenhouse triggered for player %d (+1 %s)", player_id, resource)


def _check_order_completion_inplace(player: PlayerState, placed: PlacedCheese) -> None:
    """Move the first matching order card from held → completed."""
    for i, card in enumerate(player.order_cards_held):
        if card.cheese_type == placed.cheese_type and card.age == placed.age:
            player.orders_completed.append(player.order_cards_held.pop(i))
            logger.debug("Order completed: %s/%s for player %d", placed.cheese_type, placed.age, player.player_id)
            return


def _apply_fromagerie_shelf_bonus(
    state: GameState,
    player_id: int,
    shelf: FromagerieShelf,
    data: GameDataLoader,
    ctx: _TurnCtx,
) -> None:
    """Apply the immediate bonus for a resource-bonus Fromagerie shelf.

    Deterministic fallback for simulation:
      - gain_1_resource_any      → gain 1 STRUCTURE
      - gain_2_diff_resources    → gain 1 STRUCTURE + 1 LIVESTOCK
      - trade_resource_for_any   → no net gain (skipped; requires UI choice)
    """
    bonus = shelf.immediate_bonus
    if bonus == "none":
        return
    if bonus == "gain_1_resource_any":
        _gain_resource_inplace(state, player_id, ResourceType.STRUCTURE, 1, data, ctx)
    elif bonus == "gain_2_diff_resources":
        _gain_resource_inplace(state, player_id, ResourceType.STRUCTURE, 1, data, ctx)
        _gain_resource_inplace(state, player_id, ResourceType.LIVESTOCK, 1, data, ctx)
    elif bonus == "trade_resource_for_any":
        pass  # Requires player choice; skipped in simulation (no net gain)
    else:
        logger.warning("Unknown Fromagerie shelf bonus '%s' — ignored", bonus)


def _apply_gather_inplace(
    state: GameState,
    player_id: int,
    action: GatherAction,
    data: GameDataLoader,
    ctx: _TurnCtx,
) -> None:
    """Mutate *state*: place a worker on the resource tile, gain resources, optionally use Barn."""
    from src.game.types import WorkerLocation  # local to avoid circular at module level

    player = state.players[player_id]

    # Find the first IN_HAND worker to place on the resource tile
    gather_worker = next(
        (w for w in player.workers if w.location == WorkerLocation.IN_HAND), None
    )
    if gather_worker is None:
        raise IllegalActionError(f"Player {player_id} has no worker in hand to gather")

    gather_worker.location = WorkerLocation.ON_RESOURCE_TILE
    gather_worker.venue = None
    gather_worker.space_id = action.resource_space.turns  # 1/2/3 for Bronze/Silver/Gold
    gather_worker.return_after_rotation = (state.rotation_index + action.resource_space.turns) % 4

    # Gain the resource facing this player
    resource = state.resource_facing(player_id)
    _gain_resource_inplace(state, player_id, resource, action.resource_space.turns, data, ctx)

    # Barn: place a second worker and gain 1 of the board's barn resource
    if action.use_barn and player.structures_unlocked[_BARN_IDX]:
        barn_worker = next(
            (w for w in player.workers if w.location == WorkerLocation.IN_HAND), None
        )
        if barn_worker is not None:
            barn_worker.location = WorkerLocation.ON_BARN
            barn_worker.venue = None
            barn_worker.space_id = None
            barn_worker.return_after_rotation = (state.rotation_index + 1) % 4
            board_struct = _get_board_struct(data, player.board_id)
            _gain_resource_inplace(state, player_id, board_struct.barn_resource, 1, data, ctx)


def _build_placed_cheese(
    action: MakeCheeseAction | None,
    player_id: int,
    cheese_type,
    age,
    table_id=None,
) -> PlacedCheese:
    """Helper to build PlacedCheese from a MakeCheeseAction."""
    from src.game.state import PlacedCheese
    return PlacedCheese(
        cheese_type=cheese_type,
        age=age,
        venue=action.venue,
        player_id=player_id,
        space_id=action.space_id,
        row=action.row,
        col=action.col,
        table_id=table_id,
    )


def _place_token_inplace(
    state: GameState,
    player_id: int,
    placed: PlacedCheese,
    data: GameDataLoader,
    ctx: _TurnCtx,
    worker_type=None,
    space_age=None,
) -> None:
    """Place a cheese token (PlacedCheese) onto the board.

    If worker_type is provided, the matching worker is deployed.
    Handles: order completion, Loading Dock trigger, game_end_triggered.
    """
    player = state.players[player_id]
    player.cheese_tokens_on_board.append(placed)
    player.cheese_tokens_remaining -= 1

    # Deploy worker if applicable (make-cheese, not milking parlour)
    if worker_type is not None:
        worker = next(
            (w for w in player.workers
             if w.cheese_type == worker_type and w.location == WorkerLocation.IN_HAND),
            None,
        )
        if worker is None:
            raise IllegalActionError(
                f"Player {player_id} has no {worker_type} worker in hand"
            )
        worker.location = WorkerLocation.ON_CHEESE_SPACE
        worker.venue = placed.venue
        worker.space_id = placed.space_id
        worker.row = placed.row
        worker.col = placed.col
        worker.return_after_rotation = (state.rotation_index + space_age.turns) % 4

    _check_order_completion_inplace(player, placed)

    # Loading Dock trigger: gain 1 of the dock reward if venue matches
    if player.structures_unlocked[_LOADING_DOCK_IDX]:
        board_struct = _get_board_struct(data, player.board_id)
        if placed.venue == board_struct.loading_dock_venue:
            _gain_resource_inplace(state, player_id, board_struct.loading_dock_reward, 1, data, ctx)

    if player.cheese_tokens_remaining == 0:
        state.game_end_triggered = True
        logger.info("Game end triggered: player %d placed last token", player_id)


def _deduct_fruit_inplace(player: PlayerState, fruit_req: FruitRequirement) -> None:
    """Deduct 1 Fruit and increment the appropriate fruit-spent counter."""
    if fruit_req == FruitRequirement.NONE:
        return
    if player.resources.get(ResourceType.FRUIT, 0) < 1:
        raise IllegalActionError("Not enough Fruit to pay for fruited/jam space")
    player.resources[ResourceType.FRUIT] -= 1
    if fruit_req == FruitRequirement.FRUIT:
        player.fruit_spent_on_fruited += 1
    else:
        player.fruit_spent_on_jam += 1


# ---------------------------------------------------------------------------
# Public action-application functions
# ---------------------------------------------------------------------------

def gain_resource(
    state: GameState,
    player_id: int,
    resource: ResourceType,
    amount: int,
    data: GameDataLoader,
    _ctx: _TurnCtx | None = None,
) -> GameState:
    """Return a new GameState with *amount* of *resource* added to the player.

    Draws Order Cards from the deck when resource==ORDER.
    Triggers Greenhouse if unlocked and resource matches (once per turn, via _ctx).
    """
    new = copy.deepcopy(state)
    ctx = _ctx if _ctx is not None else _TurnCtx()
    _gain_resource_inplace(new, player_id, resource, amount, data, ctx)
    return new


def apply_gather(
    state: GameState,
    player_id: int,
    action: GatherAction,
    data: GameDataLoader,
) -> GameState:
    """Return a new GameState after applying a GatherAction for *player_id*."""
    new = copy.deepcopy(state)
    ctx = _TurnCtx()
    _apply_gather_inplace(new, player_id, action, data, ctx)
    return new


def apply_make_cheese(
    state: GameState,
    player_id: int,
    action: MakeCheeseAction,
    data: GameDataLoader,
) -> GameState:
    """Return a new GameState after placing a cheese token for *player_id*.

    Raises IllegalActionError if the action is not currently valid.
    """
    new = copy.deepcopy(state)
    ctx = _TurnCtx()
    _apply_make_cheese_inplace(new, player_id, action, data, ctx)
    return new


def _apply_make_cheese_inplace(
    state: GameState,
    player_id: int,
    action: MakeCheeseAction,
    data: GameDataLoader,
    ctx: _TurnCtx,
) -> None:
    """Mutate *state*: place a worker + cheese token at the target space."""
    player = state.players[player_id]

    if player.cheese_tokens_remaining <= 0:
        raise IllegalActionError(f"Player {player_id} has no cheese tokens remaining")

    venue = action.venue
    if venue == VenueType.FROMAGERIE:
        sp = _get_fromagerie_space(data, action.space_id)
        _deduct_fruit_inplace(player, sp.fruit_requirement)
        placed = _build_placed_cheese(action, player_id, sp.cheese_type, sp.age)
        _place_token_inplace(state, player_id, placed, data, ctx,
                             worker_type=action.worker_type, space_age=sp.age)
        # Apply immediate shelf bonus for resource-bonus shelves
        shelf = _get_fromagerie_shelf(data, sp.shelf_id)
        if shelf.column == "resource_bonus":
            _apply_fromagerie_shelf_bonus(state, player_id, shelf, data, ctx)

    elif venue == VenueType.BISTRO:
        sp = _get_bistro_space(data, action.space_id)
        _deduct_fruit_inplace(player, sp.fruit_requirement)
        placed = _build_placed_cheese(action, player_id, sp.cheese_type, sp.plate_age,
                                      table_id=sp.table_id)
        _place_token_inplace(state, player_id, placed, data, ctx,
                             worker_type=action.worker_type, space_age=sp.plate_age)

    elif venue == VenueType.VILLES:
        sp = _get_villes_space(data, action.space_id)
        _deduct_fruit_inplace(player, sp.fruit_requirement)
        placed = _build_placed_cheese(action, player_id, sp.cheese_type, sp.age)
        _place_token_inplace(state, player_id, placed, data, ctx,
                             worker_type=action.worker_type, space_age=sp.age)

    elif venue == VenueType.FESTIVAL:
        sp = _get_festival_space(data, action.row, action.col)
        _deduct_fruit_inplace(player, sp.fruit_requirement)
        placed = _build_placed_cheese(action, player_id, sp.cheese_type, sp.age)
        _place_token_inplace(state, player_id, placed, data, ctx,
                             worker_type=action.worker_type, space_age=sp.age)

    else:
        raise IllegalActionError(f"Unknown venue: {venue}")


def apply_milking_parlour(
    state: GameState,
    player_id: int,
    action: MilkingParlourAction,
    data: GameDataLoader,
) -> GameState:
    """Return a new GameState after applying a MilkingParlourAction."""
    new = copy.deepcopy(state)
    ctx = _TurnCtx()
    _apply_milking_parlour_inplace(new, player_id, action, data, ctx)
    return new


def _apply_milking_parlour_inplace(
    state: GameState,
    player_id: int,
    action: MilkingParlourAction,
    data: GameDataLoader,
    ctx: _TurnCtx,
) -> None:
    """Mutate *state*: use a milking parlour to place a bonus cheese token."""
    from src.game.state import PlacedCheese

    player = state.players[player_id]
    parlour = _get_milking_parlour(data, player.board_id, action.parlour_num)

    idx = action.parlour_num - 1
    if player.resources.get(ResourceType.LIVESTOCK, 0) < parlour.livestock_cost:
        raise IllegalActionError(f"Not enough Livestock for milking parlour {action.parlour_num}")
    if player.cheese_tokens_remaining <= 0:
        raise IllegalActionError(f"Player {player_id} has no cheese tokens remaining")

    player.resources[ResourceType.LIVESTOCK] -= parlour.livestock_cost
    player.milking_parlours_used[idx] += 1

    # Resolve cheese type/age (wild parlour → use chosen; else use parlour's fixed type)
    cheese_type = action.chosen_cheese_type if parlour.bonus_cheese_type is None else parlour.bonus_cheese_type
    age = action.chosen_age if parlour.bonus_cheese_age is None else parlour.bonus_cheese_age

    # Determine fruit_requirement from the target space and deduct if needed.
    # action.target_venue tells us exactly which venue to look in.
    if action.target_row is not None and action.target_col is not None:
        sp = _get_festival_space(data, action.target_row, action.target_col)
        _deduct_fruit_inplace(player, sp.fruit_requirement)
        placed = PlacedCheese(
            cheese_type=cheese_type, age=age, venue=VenueType.FESTIVAL, player_id=player_id,
            row=action.target_row, col=action.target_col, from_milking_parlour=True,
        )
    else:
        venue = action.target_venue
        fruit_req = FruitRequirement.NONE
        table_id = None
        if venue == VenueType.FROMAGERIE:
            sp = _get_fromagerie_space(data, action.target_space_id)
            fruit_req = sp.fruit_requirement
        elif venue == VenueType.BISTRO:
            sp = _get_bistro_space(data, action.target_space_id)
            fruit_req = sp.fruit_requirement
            table_id = sp.table_id
        elif venue == VenueType.VILLES:
            sp = _get_villes_space(data, action.target_space_id)
            fruit_req = sp.fruit_requirement
        else:
            raise IllegalActionError(
                f"MilkingParlourAction has no valid target (target_venue={venue})"
            )
        _deduct_fruit_inplace(player, fruit_req)
        placed = PlacedCheese(
            cheese_type=cheese_type, age=age, venue=venue, player_id=player_id,
            space_id=action.target_space_id, table_id=table_id, from_milking_parlour=True,
        )

    # No worker is placed for milking parlour actions
    _place_token_inplace(state, player_id, placed, data, ctx, worker_type=None, space_age=None)


def apply_unlock_structure(
    state: GameState,
    player_id: int,
    action: UnlockStructureAction,
    data: GameDataLoader,
) -> GameState:
    """Return a new GameState after unlocking a structure slot."""
    new = copy.deepcopy(state)
    _apply_unlock_structure_inplace(new, player_id, action, data)
    return new


def _apply_unlock_structure_inplace(
    state: GameState,
    player_id: int,
    action: UnlockStructureAction,
    data: GameDataLoader,
) -> None:
    """Mutate *state*: spend Structure tokens to unlock slot *action.slot*."""
    player = state.players[player_id]
    idx = action.slot - 1
    if player.structures_unlocked[idx]:
        raise IllegalActionError(f"Structure slot {action.slot} is already unlocked")
    cost = _get_board_struct(data, player.board_id).structure_costs[idx]
    if player.resources.get(ResourceType.STRUCTURE, 0) < cost:
        raise IllegalActionError(
            f"Not enough Structure tokens to unlock slot {action.slot} (cost {cost})"
        )
    player.resources[ResourceType.STRUCTURE] -= cost
    player.structures_unlocked[idx] = True


def apply_turn(
    state: GameState,
    player_id: int,
    action: TurnAction,
    data: GameDataLoader,
) -> GameState:
    """Return a new GameState after applying the full TurnAction for *player_id*.

    Order: gather → unlock → make-cheese → milking parlours.
    (Gather first so resources from gathering are available for unlock costs.)
    """
    if len(action.make_cheese) > 1:
        raise IllegalActionError(
            f"Player {player_id} attempted {len(action.make_cheese)} make-cheese actions; only 1 is allowed per turn"
        )

    new = copy.deepcopy(state)
    ctx = _TurnCtx()

    if action.gather is not None:
        _apply_gather_inplace(new, player_id, action.gather, data, ctx)

    for ua in action.unlock_structures:
        _apply_unlock_structure_inplace(new, player_id, ua, data)

    for mc in action.make_cheese:
        _apply_make_cheese_inplace(new, player_id, mc, data, ctx)

    for pa in action.milking_parlours:
        _apply_milking_parlour_inplace(new, player_id, pa, data, ctx)

    return new
