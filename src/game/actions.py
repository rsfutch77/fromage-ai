"""Action dataclasses and legal move generation.

Defines GatherAction, MakeCheeseAction, MilkingParlourAction,
UnlockStructureAction, TurnAction, and the all_legal_turn_actions()
enumeration function.

See requirements section 3.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from itertools import combinations, product
from typing import TYPE_CHECKING

from src.game.types import (
    AgeType,
    CheeseType,
    FruitRequirement,
    ResourceType,
    SpaceType,
    VenueType,
    WorkerLocation,
)

if TYPE_CHECKING:
    from src.game.data_loader import GameDataLoader
    from src.game.state import GameState

logger = logging.getLogger(__name__)

# Maximum number of TurnAction combinations returned by all_legal_turn_actions.
MAX_ACTIONS_PER_TURN: int = 200

# 0-based indices into structures_unlocked list[bool].
_BARN_IDX = 0       # slot 1
_LOADING_DOCK_IDX = 1  # slot 2
_GREENHOUSE_IDX = 2    # slot 3
_HQ_IDX = 3            # slot 4


# ---------------------------------------------------------------------------
# Action dataclasses
# ---------------------------------------------------------------------------

@dataclass
class GatherAction:
    """Place a worker on the Resource Tile to gather resources.

    resource_space: Bronze, Silver, or Gold — the age tier of the space.
        Bronze = 1 resource / 1 rotation away; Silver = 2; Gold = 3.
    Worker type (Soft/Hard/Bleu) does not matter when gathering.
    """
    resource_space: AgeType


@dataclass
class MakeCheeseAction:
    """Place a worker and cheese token on a venue space.

    venue: the target venue.
    worker_type: the CheeseType of the worker being committed.
    space_id: for Fromagerie / Villes / Bistro spaces.
    row, col: for Festival grid spaces.
    """
    venue: VenueType
    worker_type: CheeseType
    space_id: int | None = None   # Fromagerie / Villes / Bistro
    row: int | None = None        # Festival
    col: int | None = None        # Festival
    resource_to_give: ResourceType | None = None
    resource_to_receive: ResourceType | None = None


@dataclass
class MilkingParlourAction:
    """Use one milking parlour to place a bonus cheese token.

    parlour_num: 1–4 (identifies the parlour on the player's board).
    chosen_cheese_type: only required for the wild parlour (bonus_cheese_type is None).
    chosen_age: only required for the wild parlour (bonus_cheese_age is None).
    target_space_id: target space for Fromagerie / Villes / Bistro.
    target_row, target_col: target position for Festival grid.
    """
    parlour_num: int
    chosen_cheese_type: CheeseType | None = None
    chosen_age: AgeType | None = None
    target_venue: VenueType | None = None   # which venue the target space is in
    target_space_id: int | None = None
    target_row: int | None = None
    target_col: int | None = None


@dataclass
class UnlockStructureAction:
    """Unlock the next sequential structure slot.

    slot: 1–4 (any unlocked order; costs `slot` Structure tokens).
    """
    slot: int


@dataclass
class TurnAction:
    """The complete plan for one player's turn.

    Any field may be None/empty to skip that sub-action.
    make_cheese may contain at most one MakeCheeseAction per turn (one cheese placement per turn).
    use_barn: True to place a worker on the Barn and gain its resource (requires Barn unlocked,
              worker in hand). Independent of gather — both can happen in the same turn.
    """
    gather: GatherAction | None = None
    use_barn: bool = False
    make_cheese: list[MakeCheeseAction] = field(default_factory=list)
    milking_parlours: list[MilkingParlourAction] = field(default_factory=list)
    unlock_structures: list[UnlockStructureAction] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Private helpers — occupied-space tracking
# ---------------------------------------------------------------------------

def _occupied_set(state: GameState) -> set:
    """Return a set of keys for all occupied cheese spaces across all players.

    For Fromagerie/Villes/Bistro: (VenueType, space_id).
    For Festival: (VenueType, row, col).
    """
    occupied: set = set()
    for player in state.players:
        for pc in player.cheese_tokens_on_board:
            if pc.venue == VenueType.FESTIVAL:
                occupied.add((pc.venue, pc.row, pc.col))
            else:
                occupied.add((pc.venue, pc.space_id))
    return occupied


def _frm_key(space_id: int) -> tuple:
    return (VenueType.FROMAGERIE, space_id)


def _bis_key(space_id: int) -> tuple:
    return (VenueType.BISTRO, space_id)


def _vil_key(space_id: int) -> tuple:
    return (VenueType.VILLES, space_id)


def _fes_key(row: int, col: int) -> tuple:
    return (VenueType.FESTIVAL, row, col)


def _target_key(target: tuple) -> tuple:
    """Hashable key for a target tuple (venue, cheese_type, age, space_id, row, col)."""
    venue, _, _, space_id, row, col = target
    if venue == VenueType.FESTIVAL:
        return (venue, row, col)
    return (venue, space_id)


# ---------------------------------------------------------------------------
# Private helper — empty cheese spaces for milking parlour
# ---------------------------------------------------------------------------

def _all_empty_cheese_spaces(
    data: GameDataLoader,
    occupied: set,
) -> list[tuple]:
    """Return all unoccupied cheese spaces across all 4 venues.

    Each entry: (venue, cheese_type, age, space_id, row, col).
    space_id is None for Festival; row/col are None for others.
    """
    results: list[tuple] = []

    for sp in data.fromagerie_spaces:
        if _frm_key(sp.space_id) not in occupied:
            results.append((VenueType.FROMAGERIE, sp.cheese_type, sp.age, sp.space_id, None, None))

    for sp in data.bistro_spaces:
        if _bis_key(sp.space_id) not in occupied:
            results.append((VenueType.BISTRO, sp.cheese_type, sp.plate_age, sp.space_id, None, None))

    for sp in data.villes_spaces:
        if _vil_key(sp.space_id) not in occupied:
            results.append((VenueType.VILLES, sp.cheese_type, sp.age, sp.space_id, None, None))

    for sp in data.festival_spaces:
        if sp.space_type != SpaceType.CHEESE:
            continue
        if _fes_key(sp.row, sp.col) not in occupied:
            results.append((VenueType.FESTIVAL, sp.cheese_type, sp.age, None, sp.row, sp.col))

    return results


def _valid_parlour_targets(
    parlour,
    occupied: set,
    data: GameDataLoader,
    facing_venue: VenueType,
) -> list[tuple]:
    """Return valid target tuples for *parlour*, restricted to *facing_venue*.

    Each tuple: (chosen_type, chosen_age, venue, space_id, row, col).
    For a wild parlour, chosen_type/age = the space's own type/age.
    """
    results: list[tuple] = []
    all_spaces = _all_empty_cheese_spaces(data, occupied)

    for (venue, cheese_type, age, space_id, row, col) in all_spaces:
        if venue != facing_venue:
            continue
        if parlour.bonus_cheese_type is None:
            # Wild parlour — any space, type/age taken from the space itself.
            results.append((cheese_type, age, venue, space_id, row, col))
        else:
            if cheese_type == parlour.bonus_cheese_type and age == parlour.bonus_cheese_age:
                results.append((parlour.bonus_cheese_type, parlour.bonus_cheese_age,
                                 venue, space_id, row, col))
    return results


# ---------------------------------------------------------------------------
# Private helper — affordability check for full turn combination
# ---------------------------------------------------------------------------

def _fruit_req_for_milking_target(action: MilkingParlourAction, data: GameDataLoader) -> FruitRequirement:
    """Look up the FruitRequirement for the target space of a MilkingParlourAction."""
    venue = action.target_venue
    if action.target_row is not None and action.target_col is not None:
        for sp in data.festival_spaces:
            if sp.row == action.target_row and sp.col == action.target_col:
                return sp.fruit_requirement
    elif action.target_space_id is not None:
        if venue == VenueType.FROMAGERIE:
            for sp in data.fromagerie_spaces:
                if sp.space_id == action.target_space_id:
                    return sp.fruit_requirement
        elif venue == VenueType.BISTRO:
            for sp in data.bistro_spaces:
                if sp.space_id == action.target_space_id:
                    return sp.fruit_requirement
        elif venue == VenueType.VILLES:
            for sp in data.villes_spaces:
                if sp.space_id == action.target_space_id:
                    return sp.fruit_requirement
        else:
            # venue unknown — search all (less efficient but safe fallback)
            for sp in data.fromagerie_spaces:
                if sp.space_id == action.target_space_id:
                    return sp.fruit_requirement
            for sp in data.bistro_spaces:
                if sp.space_id == action.target_space_id:
                    return sp.fruit_requirement
            for sp in data.villes_spaces:
                if sp.space_id == action.target_space_id:
                    return sp.fruit_requirement
    return FruitRequirement.NONE


def _fruit_req_for_action(action: MakeCheeseAction, data: GameDataLoader) -> FruitRequirement:
    """Look up the FruitRequirement of the target space for a MakeCheeseAction."""
    if action.venue == VenueType.FROMAGERIE:
        for sp in data.fromagerie_spaces:
            if sp.space_id == action.space_id:
                return sp.fruit_requirement
    elif action.venue == VenueType.BISTRO:
        for sp in data.bistro_spaces:
            if sp.space_id == action.space_id:
                return sp.fruit_requirement
    elif action.venue == VenueType.VILLES:
        for sp in data.villes_spaces:
            if sp.space_id == action.space_id:
                return sp.fruit_requirement
    elif action.venue == VenueType.FESTIVAL:
        for sp in data.festival_spaces:
            if sp.row == action.row and sp.col == action.col:
                return sp.fruit_requirement
    return FruitRequirement.NONE


def _is_affordable(
    state: GameState,
    player_id: int,
    data: GameDataLoader,
    gather: GatherAction | None,
    use_barn: bool,
    make_cheese: list[MakeCheeseAction],
    parlour_actions: list[MilkingParlourAction],
    unlock_actions: list[UnlockStructureAction],
) -> bool:
    """Check whether the combination of sub-actions is collectively affordable.

    Accounts for gather and barn income arriving before spending (same turn).
    """
    player = state.players[player_id]
    avail = dict(player.resources)

    # Apply gather gain
    if gather is not None:
        rtype = state.resource_facing(player_id)
        avail[rtype] = avail.get(rtype, 0) + gather.resource_space.turns

    # Apply barn gain (1 of the board's barn resource)
    board_struct = next(b for b in data.player_board_structures if b.board_id == player.board_id)
    if use_barn:
        avail[board_struct.barn_resource] = avail.get(board_struct.barn_resource, 0) + 1

    # Cheese token budget: make_cheese + milking parlours must not exceed tokens remaining
    tokens_avail = player.cheese_tokens_remaining - len(make_cheese) - len(parlour_actions)
    if tokens_avail < 0:
        return False

    # Unlock structure costs (Structure tokens)
    for ua in unlock_actions:
        avail[ResourceType.STRUCTURE] -= board_struct.structure_costs[ua.slot - 1]
        if avail[ResourceType.STRUCTURE] < 0:
            return False

    # Make-cheese fruit costs (one per action with a fruit requirement)
    # and resource swap costs/gains from trade_resource_for_any
    for mc in make_cheese:
        fr = _fruit_req_for_action(mc, data)
        if fr != FruitRequirement.NONE:
            avail[ResourceType.FRUIT] -= 1
            if avail[ResourceType.FRUIT] < 0:
                return False
        if mc.resource_to_give is not None and mc.resource_to_receive is not None:
            avail[mc.resource_to_give] = avail.get(mc.resource_to_give, 0) - 1
            if avail[mc.resource_to_give] < 0:
                return False
            avail[mc.resource_to_receive] = avail.get(mc.resource_to_receive, 0) + 1

    # Milking parlour livestock + fruit costs
    parlour_map = {p.parlour_num: p for p in data.milking_parlours
                   if p.board_id == player.board_id}
    for pa in parlour_actions:
        parlour = parlour_map.get(pa.parlour_num)
        if parlour is None:
            return False
        avail[ResourceType.LIVESTOCK] -= parlour.livestock_cost
        if avail[ResourceType.LIVESTOCK] < 0:
            return False
        fr = _fruit_req_for_milking_target(pa, data)
        if fr != FruitRequirement.NONE:
            avail[ResourceType.FRUIT] -= 1
            if avail[ResourceType.FRUIT] < 0:
                return False

    return True


# ---------------------------------------------------------------------------
# Legal move generators
# ---------------------------------------------------------------------------

def legal_gather_actions(
    state: GameState,
    player_id: int,
    data: GameDataLoader,
) -> list[GatherAction | None]:
    """Return all legal gather choices for *player_id* this turn.

    Includes None (skip gather).
    A resource space is legal if this player has no worker currently occupying it.
    Barn usage is handled separately in TurnAction.use_barn.
    """
    player = state.players[player_id]

    workers_in_hand = [w for w in player.workers if w.location == WorkerLocation.IN_HAND]
    n_in_hand = len(workers_in_hand)

    # Find which resource spaces (stored as .turns int) this player already occupies.
    occupied_spaces: set[int] = set()
    for worker in player.workers:
        if worker.location == WorkerLocation.ON_RESOURCE_TILE and worker.space_id is not None:
            occupied_spaces.add(worker.space_id)

    actions: list[GatherAction | None] = [None]  # Always legal to skip gather.

    if n_in_hand == 0:
        return actions  # No worker available to place on the resource tile.

    for space in AgeType:
        if space.turns in occupied_spaces:
            continue
        actions.append(GatherAction(resource_space=space))

    return actions


def legal_make_cheese_actions(
    state: GameState,
    player_id: int,
    data: GameDataLoader,
    extra_fruit: int = 0,
) -> list[MakeCheeseAction | None]:
    """Return all legal cheese-placement choices for *player_id* this turn.

    Includes None (skip make-cheese).
    extra_fruit: additional fruit to treat as available (for gather-then-spend combos).
    A space is legal if the venue faces the player, is unoccupied, the player has
    a matching worker in hand, has tokens remaining, and can afford the fruit cost.
    """
    player = state.players[player_id]
    actions: list[MakeCheeseAction | None] = [None]

    if player.cheese_tokens_remaining <= 0:
        return actions

    facing_venue = state.venue_facing(player_id)
    occupied = _occupied_set(state)
    workers_in_hand: set[CheeseType] = {
        w.cheese_type for w in player.workers if w.location == WorkerLocation.IN_HAND
    }
    effective_fruit = player.resources.get(ResourceType.FRUIT, 0) + extra_fruit

    def _has_fruit(req: FruitRequirement) -> bool:
        return req == FruitRequirement.NONE or effective_fruit >= 1

    _SWAPPABLE = [ResourceType.FRUIT, ResourceType.LIVESTOCK, ResourceType.STRUCTURE]

    if facing_venue == VenueType.FROMAGERIE:
        for sp in data.fromagerie_spaces:
            if _frm_key(sp.space_id) not in occupied and sp.cheese_type in workers_in_hand and _has_fruit(sp.fruit_requirement):
                shelf = next(sh for sh in data.fromagerie_shelves if sh.shelf_id == sp.shelf_id)
                if shelf.immediate_bonus == "trade_resource_for_any":
                    # Compute fruit available after paying the space's fruit cost.
                    fruit_after_cost = effective_fruit - (1 if sp.fruit_requirement != FruitRequirement.NONE else 0)
                    has_any_swap = False
                    for give in _SWAPPABLE:
                        available = player.resources.get(give, 0)
                        if give == ResourceType.FRUIT:
                            available = fruit_after_cost
                        if available < 1:
                            continue
                        for receive in _SWAPPABLE:
                            if receive == give:
                                continue
                            has_any_swap = True
                            actions.append(MakeCheeseAction(
                                venue=VenueType.FROMAGERIE, worker_type=sp.cheese_type,
                                space_id=sp.space_id,
                                resource_to_give=give, resource_to_receive=receive,
                            ))
                    if not has_any_swap:
                        # Fallback: player cannot swap, emit no-swap action.
                        actions.append(MakeCheeseAction(
                            venue=VenueType.FROMAGERIE, worker_type=sp.cheese_type,
                            space_id=sp.space_id,
                        ))
                else:
                    actions.append(MakeCheeseAction(venue=VenueType.FROMAGERIE, worker_type=sp.cheese_type, space_id=sp.space_id))
    elif facing_venue == VenueType.BISTRO:
        for sp in data.bistro_spaces:
            if _bis_key(sp.space_id) not in occupied and sp.cheese_type in workers_in_hand and _has_fruit(sp.fruit_requirement):
                actions.append(MakeCheeseAction(venue=VenueType.BISTRO, worker_type=sp.cheese_type, space_id=sp.space_id))
    elif facing_venue == VenueType.VILLES:
        for sp in data.villes_spaces:
            if _vil_key(sp.space_id) not in occupied and sp.cheese_type in workers_in_hand and _has_fruit(sp.fruit_requirement):
                actions.append(MakeCheeseAction(venue=VenueType.VILLES, worker_type=sp.cheese_type, space_id=sp.space_id))
    elif facing_venue == VenueType.FESTIVAL:
        for sp in data.festival_spaces:
            if sp.space_type != SpaceType.CHEESE:
                continue
            if _fes_key(sp.row, sp.col) not in occupied and sp.cheese_type in workers_in_hand and _has_fruit(sp.fruit_requirement):
                actions.append(MakeCheeseAction(venue=VenueType.FESTIVAL, worker_type=sp.cheese_type, row=sp.row, col=sp.col))

    return actions


def legal_milking_parlour_actions(
    state: GameState,
    player_id: int,
    data: GameDataLoader,
) -> list[list[MilkingParlourAction]]:
    """Return all legal combinations of milking parlour uses for *player_id*.

    Always includes the empty combination (use none).
    A parlour is usable if:
      (a) not already used this game,
      (b) player has enough Livestock,
      (c) at least one matching empty target space exists in any venue.
    """
    player = state.players[player_id]
    available_livestock = player.resources.get(ResourceType.LIVESTOCK, 0)
    tokens_available = player.cheese_tokens_remaining

    if tokens_available <= 0:
        return [[]]

    player_parlours = [p for p in data.milking_parlours if p.board_id == player.board_id]
    occupied = _occupied_set(state)
    facing_venue = state.venue_facing(player_id)

    # Gather individually usable parlours with their target options.
    usable: list[tuple] = []  # (parlour, [target_tuples])
    for parlour in player_parlours:
        if parlour.livestock_cost > available_livestock:
            continue
        targets = _valid_parlour_targets(parlour, occupied, data, facing_venue)
        if targets:
            usable.append((parlour, targets))

    result: list[list[MilkingParlourAction]] = [[]]  # empty combination

    # Generate all valid subsets of parlours, with one target choice per parlour.
    for size in range(1, len(usable) + 1):
        for parlour_subset in combinations(usable, size):
            if size > tokens_available:
                continue
            total_cost = sum(p.livestock_cost for p, _ in parlour_subset)
            if total_cost > available_livestock:
                continue
            # Cross-product of target options for each parlour in the subset.
            target_lists = [targets for _, targets in parlour_subset]
            for target_combo in product(*target_lists):
                # Reject if two actions target the same space.
                keys = [_target_key(t) for t in target_combo]
                if len(set(keys)) < len(keys):
                    continue
                action_list = []
                for (parlour, _), (ct, ca, venue, sid, row, col) in zip(parlour_subset, target_combo):
                    action_list.append(MilkingParlourAction(
                        parlour_num=parlour.parlour_num,
                        chosen_cheese_type=ct,
                        chosen_age=ca,
                        target_venue=venue,
                        target_space_id=sid,
                        target_row=row,
                        target_col=col,
                    ))
                result.append(action_list)

    return result


def legal_unlock_actions(
    state: GameState,
    player_id: int,
    data: "GameDataLoader",
) -> list[list[UnlockStructureAction]]:
    """Return all affordable structure unlock subsets for *player_id*.

    Always includes the empty list (no unlock).
    Returns every affordable subset of currently-locked slots.
    """
    player = state.players[player_id]
    available = player.resources.get(ResourceType.STRUCTURE, 0)
    board_struct = next(b for b in data.player_board_structures if b.board_id == player.board_id)

    locked = [slot for slot in range(1, 5) if not player.structures_unlocked[slot - 1]]

    result: list[list[UnlockStructureAction]] = [[]]
    for size in range(1, len(locked) + 1):
        for subset in combinations(locked, size):
            if sum(board_struct.structure_costs[s - 1] for s in subset) <= available:
                result.append([UnlockStructureAction(slot=s) for s in subset])

    return result


def _workers_available_after_gather(
    player: PlayerState,
    gather: GatherAction | None,
    use_barn: bool = False,
) -> set[CheeseType]:
    """Return CheeseTypes still in hand after gather and optional barn worker deployment."""
    in_hand = [w for w in player.workers if w.location == WorkerLocation.IN_HAND]
    consumed: list[CheeseType] = []
    if gather is not None and in_hand:
        consumed.append(in_hand[0].cheese_type)
    # Barn uses next available in-hand worker (after gather worker if both are used).
    if use_barn and len(in_hand) > len(consumed):
        consumed.append(in_hand[len(consumed)].cheese_type)
    return {w.cheese_type for w in in_hand} - set(consumed)


def _make_cheese_space_key(a: MakeCheeseAction) -> tuple:
    """Hashable key for the target space of a MakeCheeseAction."""
    if a.venue == VenueType.FESTIVAL:
        return (a.venue, a.row, a.col)
    return (a.venue, a.space_id)


def _legal_cheese_combos(
    available_types: set[CheeseType],
    single_cheese_actions: list[MakeCheeseAction | None],
    max_placements: int,
) -> list[list[MakeCheeseAction]]:
    """Return all valid subsets of simultaneous cheese placements.

    Each returned list is a set of non-conflicting MakeCheeseActions using
    distinct worker types from *available_types*.  Always includes the empty
    list (place no cheese this turn).

    *max_placements* caps subset size at the player's remaining cheese-token
    count so we never generate a combo that would exceed the supply.
    """
    candidates = [
        a for a in single_cheese_actions
        if a is not None and a.worker_type in available_types
    ]
    by_type: dict[CheeseType, list[MakeCheeseAction]] = {}
    for a in candidates:
        by_type.setdefault(a.worker_type, []).append(a)

    types = list(by_type.keys())
    result: list[list[MakeCheeseAction]] = [[]]

    max_size = min(len(types), max_placements)
    for size in range(1, max_size + 1):
        for type_subset in combinations(types, size):
            target_lists = [by_type[t] for t in type_subset]
            for target_combo in product(*target_lists):
                keys = [_make_cheese_space_key(a) for a in target_combo]
                if len(set(keys)) < len(keys):
                    continue  # two actions targeting the same space
                result.append(list(target_combo))

    return result


def all_legal_turn_actions(
    state: GameState,
    player_id: int,
    data: GameDataLoader,
) -> list[TurnAction]:
    """Enumerate all legal TurnAction combinations for *player_id*.

    Takes the cross-product of gather choices, make-cheese choices, parlour
    combinations, and unlock sequences, then filters combinations where
    the total resource cost exceeds available resources (accounting for
    gather income arriving in the same turn).

    Caps output at MAX_ACTIONS_PER_TURN to prevent combinatorial explosion.
    """
    gather_choices = legal_gather_actions(state, player_id, data)
    parlour_combos = legal_milking_parlour_actions(state, player_id, data)
    unlock_seqs = legal_unlock_actions(state, player_id, data)

    player = state.players[player_id]
    barn_unlocked = player.structures_unlocked[_BARN_IDX]
    n_in_hand = sum(1 for w in player.workers if w.location == WorkerLocation.IN_HAND)
    results: list[TurnAction] = []

    for gc in gather_choices:
        # Workers remaining after gather; barn needs one of these.
        workers_after_gather = n_in_hand - (1 if gc is not None else 0)
        barn_choices = [False]
        if barn_unlocked and workers_after_gather >= 1:
            barn_choices.append(True)

        for use_barn in barn_choices:
            available_for_cheese: set[CheeseType] = _workers_available_after_gather(player, gc, use_barn)

            extra_fruit = (gc.resource_space.turns if gc is not None and state.resource_facing(player_id) == ResourceType.FRUIT else 0)
            all_cheese = legal_make_cheese_actions(state, player_id, data, extra_fruit)
            cheese_combos = _legal_cheese_combos(
                available_for_cheese, all_cheese, min(1, player.cheese_tokens_remaining)
            )

            for combo in cheese_combos:
                for pc in parlour_combos:
                    for uc in unlock_seqs:
                        if not _is_affordable(state, player_id, data, gc, use_barn, combo, pc, uc):
                            continue
                        results.append(TurnAction(
                            gather=gc,
                            use_barn=use_barn,
                            make_cheese=list(combo),
                            milking_parlours=list(pc),
                            unlock_structures=list(uc),
                        ))
                        if len(results) >= MAX_ACTIONS_PER_TURN:
                            logger.debug(
                                "all_legal_turn_actions: hit cap %d for player %d",
                                MAX_ACTIONS_PER_TURN, player_id,
                            )
                            return results

    return results


