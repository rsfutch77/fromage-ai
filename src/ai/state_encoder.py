"""Encodes a GameState into a fixed-length float32 numpy feature vector.

Used as input to the Q-learning agent's linear function approximator.
Exports STATE_VECTOR_SIZE constant and encode_state() function.
See requirements section 9.

Sub-vector layout (enhanced=True, total 292):
  Own-player (18) | Board (12) | Occupancy (158) | Opponents (9)
  | Venue lookahead (16) | Resource lookahead (12) | Worker avail (12)
  | Festival derived (5) | Fromagerie derived (6) | Bistro derived (8)
  | Villes derived (36)

Legacy mode (enhanced=False): first 197 features only (base encoder).
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

import numpy as np

from src.game.types import (
    AgeType,
    CheeseType,
    ResourceType,
    SpaceType,
    VenueType,
    VENUE_ORDER,
    RESOURCE_ORDER,
    WorkerLocation,
)

if TYPE_CHECKING:
    from src.game.data_loader import GameDataLoader
    from src.game.state import GameState

# ---------------------------------------------------------------------------
# Sub-vector sizes
# ---------------------------------------------------------------------------
_OWN_SIZE = 18
_BOARD_SIZE = 12
_FROMAGERIE_SPACES = 18
_BISTRO_SPACES = 18
_VILLES_SPACES = 18
_FESTIVAL_SPACES = 25
_OCCUPANCY_SIZE = (_FROMAGERIE_SPACES + _BISTRO_SPACES + _VILLES_SPACES + _FESTIVAL_SPACES) * 2
_OPPONENT_SIZE = 9

_BASE_SIZE: int = _OWN_SIZE + _BOARD_SIZE + _OCCUPANCY_SIZE + _OPPONENT_SIZE  # 197

_VENUE_LOOK_SIZE = 16   # 4 offsets × one-hot(4)
_RESOURCE_LOOK_SIZE = 12  # 3 offsets × one-hot(4)
_WORKER_AVAIL_SIZE = 12  # 3 types × one-hot(4)
_FESTIVAL_DERIVED_SIZE = 5
_FROMAGERIE_DERIVED_SIZE = 6
_BISTRO_DERIVED_SIZE = 8
_VILLES_DERIVED_SIZE = 36  # 6 regions × 6 features

_ENHANCED_SIZE: int = (
    _VENUE_LOOK_SIZE + _RESOURCE_LOOK_SIZE + _WORKER_AVAIL_SIZE
    + _FESTIVAL_DERIVED_SIZE + _FROMAGERIE_DERIVED_SIZE
    + _BISTRO_DERIVED_SIZE + _VILLES_DERIVED_SIZE
)  # 95

STATE_VECTOR_SIZE: int = _BASE_SIZE + _ENHANCED_SIZE  # 292

# Normalisation constants
_FESTIVAL_SCORE_NORM = 30.0
_FESTIVAL_ADJ_NORM = 12.0
_INFLUENCE_NORM = 6.0

# Canonical region order for Villes (matches customer_tokens.csv order)
_REGION_ORDER: list[str] = ["purple", "blue", "green", "white", "yellow", "pink"]


def encode_state(
    state: GameState,
    player_id: int,
    data: GameDataLoader,
    *,
    enhanced: bool = True,
) -> np.ndarray:
    """Encode *state* from *player_id*'s perspective.

    Returns a float32 array of length STATE_VECTOR_SIZE (292 when enhanced,
    197 when not) with all values in [0, 1].

    Set *enhanced* = False to get the legacy 197-feature vector (for loading
    old saved models).
    """
    parts = [
        _encode_own_player(state, player_id),
        _encode_board(state, player_id),
        _encode_occupancy(state, player_id, data),
        _encode_opponents(state, player_id),
    ]
    if enhanced:
        parts.extend([
            _encode_venue_lookahead(state, player_id),
            _encode_resource_lookahead(state, player_id),
            _encode_worker_availability(state, player_id),
            _encode_festival_derived(state, player_id, data),
            _encode_fromagerie_derived(state, player_id, data),
            _encode_bistro_derived(state, player_id, data),
            _encode_villes_derived(state, player_id, data),
        ])

    vec = np.concatenate(parts).astype(np.float32)
    expected = STATE_VECTOR_SIZE if enhanced else _BASE_SIZE
    assert len(vec) == expected, f"Expected {expected}, got {len(vec)}"
    return vec


# ---------------------------------------------------------------------------
# Base sub-vector encoders (unchanged from Milestone 8)
# ---------------------------------------------------------------------------

def _encode_own_player(state: GameState, player_id: int) -> np.ndarray:
    """Encode own-player features (18 values)."""
    player = state.players[player_id]
    res = player.resources

    resources = np.array([
        min(res.get(ResourceType.FRUIT, 0) / 10.0, 1.0),
        min(res.get(ResourceType.LIVESTOCK, 0) / 10.0, 1.0),
        min(res.get(ResourceType.STRUCTURE, 0) / 10.0, 1.0),
        min(res.get(ResourceType.ORDER, 0) / 10.0, 1.0),
    ])

    in_hand: set[CheeseType] = {
        w.cheese_type for w in player.workers
        if w.location == WorkerLocation.IN_HAND
    }
    workers = np.array([
        1.0 if CheeseType.SOFT in in_hand else 0.0,
        1.0 if CheeseType.HARD in in_hand else 0.0,
        1.0 if CheeseType.BLEU in in_hand else 0.0,
    ])

    tokens_remaining = player.cheese_tokens_remaining / 15.0
    structs_frac = sum(player.structures_unlocked) / 4.0
    orders_done = min(len(player.orders_completed) / 6.0, 1.0)
    orders_held = min(len(player.order_cards_held) / 6.0, 1.0)
    fruit_fruited = min(player.fruit_spent_on_fruited / 15.0, 1.0)
    fruit_jam = min(player.fruit_spent_on_jam / 15.0, 1.0)
    parlours_used = min(sum(player.milking_parlours_used) / 4.0, 1.0)

    board_onehot = np.zeros(4)
    if 1 <= player.board_id <= 4:
        board_onehot[player.board_id - 1] = 1.0

    scalars = np.array([tokens_remaining, structs_frac, orders_done, orders_held,
                        fruit_fruited, fruit_jam, parlours_used])
    return np.concatenate([resources, workers, scalars, board_onehot])


def _encode_board(state: GameState, player_id: int) -> np.ndarray:
    """Encode board-state features (12 values)."""
    rotation_oh = np.zeros(4)
    rotation_oh[state.rotation_index % 4] = 1.0

    resource_facing = state.resource_facing(player_id)
    resource_oh = np.zeros(4)
    resource_oh[RESOURCE_ORDER.index(resource_facing)] = 1.0

    venue_facing = state.venue_facing(player_id)
    venue_oh = np.zeros(4)
    venue_oh[VENUE_ORDER.index(venue_facing)] = 1.0

    return np.concatenate([rotation_oh, resource_oh, venue_oh])


def _encode_occupancy(state: GameState, player_id: int, data: GameDataLoader) -> np.ndarray:
    """Encode venue occupancy for all 79 spaces (158 values)."""
    own_set: set = set()
    any_set: set = set()
    for player in state.players:
        for pc in player.cheese_tokens_on_board:
            if pc.venue == VenueType.FESTIVAL:
                key = (VenueType.FESTIVAL, pc.row, pc.col)
            else:
                key = (pc.venue, pc.space_id)
            any_set.add(key)
            if player.player_id == player_id:
                own_set.add(key)

    parts: list[np.ndarray] = []

    for sp in sorted(data.fromagerie_spaces, key=lambda s: s.space_id):
        key = (VenueType.FROMAGERIE, sp.space_id)
        parts.append(np.array([1.0 if key in own_set else 0.0,
                                1.0 if key in any_set else 0.0]))

    for sp in sorted(data.bistro_spaces, key=lambda s: s.space_id):
        key = (VenueType.BISTRO, sp.space_id)
        parts.append(np.array([1.0 if key in own_set else 0.0,
                                1.0 if key in any_set else 0.0]))

    for sp in sorted(data.villes_spaces, key=lambda s: s.space_id):
        key = (VenueType.VILLES, sp.space_id)
        parts.append(np.array([1.0 if key in own_set else 0.0,
                                1.0 if key in any_set else 0.0]))

    for sp in sorted(data.festival_spaces, key=lambda s: (s.row, s.col)):
        key = (VenueType.FESTIVAL, sp.row, sp.col)
        if sp.space_type == SpaceType.FREE_SAMPLE:
            parts.append(np.array([0.0, 1.0]))
        else:
            parts.append(np.array([1.0 if key in own_set else 0.0,
                                    1.0 if key in any_set else 0.0]))

    return np.concatenate(parts)


def _encode_opponents(state: GameState, player_id: int) -> np.ndarray:
    """Encode summary of each opponent's state (9 values = 3 opponents × 3)."""
    opponent_ids = [p.player_id for p in state.players if p.player_id != player_id]
    parts: list[float] = []
    for opp_id in opponent_ids:
        opp = state.players[opp_id]
        parts.append(opp.cheese_tokens_remaining / 15.0)
        parts.append(min(len(opp.orders_completed) / 6.0, 1.0))
        parts.append(min(len(opp.cheese_tokens_on_board) / 15.0, 1.0))
    return np.array(parts, dtype=np.float64)


# ---------------------------------------------------------------------------
# Enhanced sub-vector encoders (Milestone 10)
# ---------------------------------------------------------------------------

def _encode_venue_lookahead(state: GameState, player_id: int) -> np.ndarray:
    """Venue at rotation+0..+3 as one-hot(4) each (16 values)."""
    parts = np.zeros(16)
    for offset in range(4):
        idx = (player_id + state.rotation_index + offset) % 4
        parts[offset * 4 + idx] = 1.0
    return parts


def _encode_resource_lookahead(state: GameState, player_id: int) -> np.ndarray:
    """Resource at rotation+0..+2 as one-hot(4) each (12 values)."""
    parts = np.zeros(12)
    for offset in range(3):
        idx = (player_id + state.resource_tile_orientation + state.rotation_index + offset) % 4
        parts[offset * 4 + idx] = 1.0
    return parts


def _encode_worker_availability(state: GameState, player_id: int) -> np.ndarray:
    """Turns-until-available for each cheese type as one-hot(4) (12 values).

    Index 0 = in hand now, 1/2/3 = returns in 1/2/3 rotations.
    """
    player = state.players[player_id]
    parts = np.zeros(12)
    for i, ctype in enumerate([CheeseType.SOFT, CheeseType.HARD, CheeseType.BLEU]):
        worker = next((w for w in player.workers if w.cheese_type == ctype), None)
        if worker is None or worker.location == WorkerLocation.IN_HAND:
            turns = 0
        elif worker.return_after_rotation is not None:
            turns = (worker.return_after_rotation - state.rotation_index) % 4
            if turns == 0:
                turns = 0  # due back this rotation = available now
        else:
            turns = 0
        parts[i * 4 + min(turns, 3)] = 1.0
    return parts


def _encode_festival_derived(
    state: GameState, player_id: int, data: GameDataLoader,
) -> np.ndarray:
    """Festival scoring-derived features (5 values).

    [score_norm, group1_size/7, group2_size/7, group3_size/7, adj_empty_norm]
    """
    all_placed = [pc for p in state.players for pc in p.cheese_tokens_on_board]

    # Player's festival positions
    player_positions: set[tuple[int, int]] = {
        (pc.row, pc.col)
        for pc in all_placed
        if pc.venue == VenueType.FESTIVAL and pc.player_id == player_id
    }
    free_sample_positions: set[tuple[int, int]] = {
        (sp.row, sp.col)
        for sp in data.festival_spaces
        if sp.space_type == SpaceType.FREE_SAMPLE
    }
    own_occupied = player_positions | free_sample_positions

    if not player_positions:
        return np.zeros(5)

    # BFS for connected groups (same logic as scoring.score_festival)
    visited: set[tuple[int, int]] = set()
    group_sizes: list[int] = []
    scoring_table = data.scoring_festival

    total_score = 0
    for start in own_occupied:
        if start in visited:
            continue
        group: set[tuple[int, int]] = set()
        queue = [start]
        while queue:
            pos = queue.pop()
            if pos in visited or pos not in own_occupied:
                continue
            visited.add(pos)
            group.add(pos)
            r, c = pos
            for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if (nr, nc) not in visited and (nr, nc) in own_occupied:
                    queue.append((nr, nc))

        if not (group & player_positions):
            continue
        size = len(group)
        group_sizes.append(size)
        points = scoring_table.get(min(size, 7), 0)
        if size > 7:
            from src.game.data_loader import FESTIVAL_BONUS_PER_EXTRA
            points += FESTIVAL_BONUS_PER_EXTRA * (size - 7)
        total_score += points

    # Top-3 group sizes (descending), padded with 0
    group_sizes.sort(reverse=True)
    top3 = (group_sizes + [0, 0, 0])[:3]

    # Count empty festival spaces adjacent to player's groups
    all_festival_positions: set[tuple[int, int]] = {
        (sp.row, sp.col) for sp in data.festival_spaces
    }
    occupied_any: set[tuple[int, int]] = {
        (pc.row, pc.col)
        for pc in all_placed
        if pc.venue == VenueType.FESTIVAL
    } | free_sample_positions
    adj_empty = 0
    for pos in own_occupied:
        r, c = pos
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if (nr, nc) in all_festival_positions and (nr, nc) not in occupied_any:
                adj_empty += 1

    return np.array([
        min(total_score / _FESTIVAL_SCORE_NORM, 1.0),
        min(top3[0] / 7.0, 1.0),
        min(top3[1] / 7.0, 1.0),
        min(top3[2] / 7.0, 1.0),
        min(adj_empty / _FESTIVAL_ADJ_NORM, 1.0),
    ])


def _encode_fromagerie_derived(
    state: GameState, player_id: int, data: GameDataLoader,
) -> np.ndarray:
    """Fromagerie scoring-derived features (6 values).

    [own_shelves/6, available_shelves/6, opp1_shelves/6, opp2_shelves/6,
     opp3_shelves/6, unoccupied_point_bonus_norm]
    """
    all_placed = [pc for p in state.players for pc in p.cheese_tokens_on_board]
    space_to_shelf: dict[int, int] = {sp.space_id: sp.shelf_id for sp in data.fromagerie_spaces}
    shelf_map = {sh.shelf_id: sh for sh in data.fromagerie_shelves}

    # Occupied spaces by any player
    occupied_space_ids: set[int] = {
        pc.space_id for pc in all_placed
        if pc.venue == VenueType.FROMAGERIE and pc.space_id is not None
    }

    # Per-player shelf counts
    def _shelf_count(pid: int) -> int:
        shelves: set[int] = set()
        for pc in all_placed:
            if pc.venue == VenueType.FROMAGERIE and pc.player_id == pid and pc.space_id is not None:
                sid = space_to_shelf.get(pc.space_id)
                if sid is not None:
                    shelves.add(sid)
        return len(shelves)

    own_shelves = _shelf_count(player_id)

    # Available shelves: shelves with at least 1 empty space
    available = 0
    shelves_with_empty: set[int] = set()
    for sp in data.fromagerie_spaces:
        if sp.space_id not in occupied_space_ids:
            shelves_with_empty.add(sp.shelf_id)
    available = len(shelves_with_empty)

    # Opponent shelf counts
    opp_ids = [p.player_id for p in state.players if p.player_id != player_id]
    opp_shelves = [_shelf_count(oid) for oid in opp_ids]

    # Unoccupied point-bonus spaces
    total_point_bonus = 0
    for sp in data.fromagerie_spaces:
        shelf = shelf_map.get(sp.shelf_id)
        if shelf and shelf.column == "point_bonus" and sp.space_id not in occupied_space_ids:
            total_point_bonus += 1

    # Normalise point-bonus count by total point-bonus spaces
    total_pb_spaces = sum(
        1 for sp in data.fromagerie_spaces
        if shelf_map.get(sp.shelf_id) and shelf_map[sp.shelf_id].column == "point_bonus"
    )
    pb_norm = total_point_bonus / max(total_pb_spaces, 1)

    return np.array([
        min(own_shelves / 6.0, 1.0),
        min(available / 6.0, 1.0),
        min(opp_shelves[0] / 6.0, 1.0) if len(opp_shelves) > 0 else 0.0,
        min(opp_shelves[1] / 6.0, 1.0) if len(opp_shelves) > 1 else 0.0,
        min(opp_shelves[2] / 6.0, 1.0) if len(opp_shelves) > 2 else 0.0,
        min(pb_norm, 1.0),
    ])


def _encode_bistro_derived(
    state: GameState, player_id: int, data: GameDataLoader,
) -> np.ndarray:
    """Bistro scoring-derived features (8 values).

    [pairings/9, half_tables/9, bronze/9, silver/9, gold/9,
     opp1_pairings/9, opp2_pairings/9, opp3_pairings/9]
    """
    all_placed = [pc for p in state.players for pc in p.cheese_tokens_on_board]
    space_to_table: dict[int, int] = {sp.space_id: sp.table_id for sp in data.bistro_spaces}

    def _bistro_stats(pid: int) -> tuple[int, int, int, int, int]:
        """Return (pairings, half_tables, bronze, silver, gold) for a player."""
        table_counts: dict[int, int] = defaultdict(int)
        age_counts: dict[AgeType, int] = defaultdict(int)
        for pc in all_placed:
            if pc.venue != VenueType.BISTRO or pc.player_id != pid:
                continue
            tid = pc.table_id if pc.table_id is not None else space_to_table.get(pc.space_id)
            if tid is not None:
                table_counts[tid] += 1
            age_counts[pc.age] += 1
        pairings = sum(1 for cnt in table_counts.values() if cnt >= 2)
        half_tables = sum(1 for cnt in table_counts.values() if cnt == 1)
        return (
            pairings, half_tables,
            age_counts.get(AgeType.BRONZE, 0),
            age_counts.get(AgeType.SILVER, 0),
            age_counts.get(AgeType.GOLD, 0),
        )

    own = _bistro_stats(player_id)
    opp_ids = [p.player_id for p in state.players if p.player_id != player_id]
    opp_pairings = [_bistro_stats(oid)[0] for oid in opp_ids]

    return np.array([
        min(own[0] / 9.0, 1.0),  # pairings
        min(own[1] / 9.0, 1.0),  # half-tables
        min(own[2] / 9.0, 1.0),  # bronze
        min(own[3] / 9.0, 1.0),  # silver
        min(own[4] / 9.0, 1.0),  # gold
        min(opp_pairings[0] / 9.0, 1.0) if len(opp_pairings) > 0 else 0.0,
        min(opp_pairings[1] / 9.0, 1.0) if len(opp_pairings) > 1 else 0.0,
        min(opp_pairings[2] / 9.0, 1.0) if len(opp_pairings) > 2 else 0.0,
    ])


def _encode_villes_derived(
    state: GameState, player_id: int, data: GameDataLoader,
) -> np.ndarray:
    """Villes influence-derived features (36 values = 6 regions × 6).

    Per region: [self_inf_norm, max_opp_norm, delta_norm,
                 is_winning, is_tied, is_losing]
    """
    # Build influence map: {player_id: {region: count}}
    influence: dict[int, dict[str, int]] = {p.player_id: defaultdict(int) for p in state.players}
    for player in state.players:
        for pc in player.cheese_tokens_on_board:
            if pc.venue != VenueType.VILLES:
                continue
            for sp in data.villes_spaces:
                if sp.space_id == pc.space_id:
                    for region in sp.regions:
                        influence[player.player_id][region] += 1
                    break

    parts = np.zeros(36)
    opp_ids = [p.player_id for p in state.players if p.player_id != player_id]

    for i, region in enumerate(_REGION_ORDER):
        self_inf = influence[player_id].get(region, 0)
        opp_infs = [influence[oid].get(region, 0) for oid in opp_ids]
        max_opp = max(opp_infs) if opp_infs else 0

        delta = self_inf - max_opp
        # Normalise to [0, 1]
        base = i * 6
        parts[base + 0] = min(self_inf / _INFLUENCE_NORM, 1.0)
        parts[base + 1] = min(max_opp / _INFLUENCE_NORM, 1.0)
        parts[base + 2] = min(max((delta + _INFLUENCE_NORM) / (2 * _INFLUENCE_NORM), 0.0), 1.0)

        # Winner status one-hot: [self_wins, tied, opp_wins]
        if self_inf > max_opp and self_inf > 0:
            parts[base + 3] = 1.0
        elif self_inf == max_opp and self_inf > 0:
            parts[base + 4] = 1.0
        elif max_opp > self_inf:
            parts[base + 5] = 1.0
        # else: all zeros (no one has influence)

    return parts
