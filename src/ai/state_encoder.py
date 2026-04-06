"""Encodes a GameState into a fixed-length float32 numpy feature vector.

Used as input to the Q-learning agent's linear function approximator.
Exports STATE_VECTOR_SIZE constant and encode_state() function.

See requirements section 9.

Sub-vector layout
-----------------
Own-player (18):
  resources × 4 (FRUIT, LIVESTOCK, STRUCTURE, ORDER — normalised by 10)
  workers in hand × 3 binary (SOFT, HARD, BLEU)
  cheese_tokens_remaining (normalised by 15)
  structures_unlocked fraction (sum / 4)
  orders_completed (normalised by 6, clamped)
  orders_held (normalised by 6, clamped)
  fruit_spent_on_fruited (normalised by 15)
  fruit_spent_on_jam (normalised by 15)
  milking_parlours_used total (normalised by 4)
  board_id one-hot × 4

Board state (12):
  rotation_index one-hot × 4
  resource_facing one-hot × 4  (LIVESTOCK, ORDER, STRUCTURE, FRUIT)
  venue_facing one-hot × 4     (FROMAGERIE, BISTRO, VILLES, FESTIVAL)

Venue occupancy (158):
  For each of 79 spaces in canonical order: [own_token, any_token]
  Fromagerie 18 spaces × 2 = 36
  Bistro 18 spaces × 2 = 36
  Villes 18 spaces × 2 = 36
  Festival 25 spaces × 2 = 50  (FREE_SAMPLE spaces: own=0, any=1 always)

Opponent summary (9):
  Per opponent (3, ordered by player_id excluding self):
    cheese_tokens_remaining / 15
    orders_completed (normalised by 6, clamped)
    total cheese placed / 15 (clamped)

Total: 18 + 12 + 158 + 9 = 197
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from src.game.types import (
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

# Sub-vector sizes (must sum to STATE_VECTOR_SIZE)
_OWN_SIZE = 18
_BOARD_SIZE = 12
_FROMAGERIE_SPACES = 18
_BISTRO_SPACES = 18
_VILLES_SPACES = 18
_FESTIVAL_SPACES = 25
_OCCUPANCY_SIZE = (_FROMAGERIE_SPACES + _BISTRO_SPACES + _VILLES_SPACES + _FESTIVAL_SPACES) * 2
_OPPONENT_SIZE = 9

STATE_VECTOR_SIZE: int = _OWN_SIZE + _BOARD_SIZE + _OCCUPANCY_SIZE + _OPPONENT_SIZE  # 197


def encode_state(state: GameState, player_id: int, data: GameDataLoader) -> np.ndarray:
    """Encode *state* from *player_id*'s perspective.

    Returns a float32 array of length STATE_VECTOR_SIZE with all values in [0, 1].
    """
    vec = np.concatenate([
        _encode_own_player(state, player_id),
        _encode_board(state, player_id),
        _encode_occupancy(state, player_id, data),
        _encode_opponents(state, player_id),
    ]).astype(np.float32)
    assert len(vec) == STATE_VECTOR_SIZE, f"Expected {STATE_VECTOR_SIZE}, got {len(vec)}"
    return vec


# ---------------------------------------------------------------------------
# Sub-vector encoders
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

    # Fromagerie — sorted by space_id
    for sp in sorted(data.fromagerie_spaces, key=lambda s: s.space_id):
        key = (VenueType.FROMAGERIE, sp.space_id)
        parts.append(np.array([1.0 if key in own_set else 0.0,
                                1.0 if key in any_set else 0.0]))

    # Bistro — sorted by space_id
    for sp in sorted(data.bistro_spaces, key=lambda s: s.space_id):
        key = (VenueType.BISTRO, sp.space_id)
        parts.append(np.array([1.0 if key in own_set else 0.0,
                                1.0 if key in any_set else 0.0]))

    # Villes — sorted by space_id
    for sp in sorted(data.villes_spaces, key=lambda s: s.space_id):
        key = (VenueType.VILLES, sp.space_id)
        parts.append(np.array([1.0 if key in own_set else 0.0,
                                1.0 if key in any_set else 0.0]))

    # Festival — sorted by (row, col); FREE_SAMPLE always any=1, own=0
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
