"""Board rotation, worker retrieval, and game setup.

Functions: rotate_board, retrieve_workers, setup_game, is_game_over.
All functions are pure (return new GameState, do not mutate input).

See requirements section 2.4.
"""

from __future__ import annotations

import copy
import random

from src.game.data_loader import GameDataLoader
from src.game.state import GameState, PlayerState, Worker
from src.game.types import CheeseType, RESOURCE_ORDER, WorkerLocation


def rotate_board(state: GameState) -> GameState:
    """Increment rotation_index by 1 (mod 4); return a new GameState."""
    new = copy.deepcopy(state)
    new.rotation_index = (state.rotation_index + 1) % 4
    return new


def retrieve_workers(state: GameState) -> GameState:
    """Return any worker whose return_after_rotation equals current rotation_index.

    Called at the *start* of each turn before players act.
    Workers are returned to IN_HAND and their placement fields cleared.
    """
    new = copy.deepcopy(state)
    for player in new.players:
        for worker in player.workers:
            if (
                worker.location != WorkerLocation.IN_HAND
                and worker.return_after_rotation == new.rotation_index
            ):
                worker.location = WorkerLocation.IN_HAND
                worker.venue = None
                worker.space_id = None
                worker.return_after_rotation = None
    return new


def setup_game(data: GameDataLoader, seed: int | None = None) -> GameState:
    """Initialise a new GameState ready for turn 1.

    - Shuffles the 36-card order deck (reproducible with *seed*).
    - Assigns board IDs to 4 players randomly.
    - Sets resource_tile_orientation randomly.
    - Distributes starting resources:
        * 2 of the resource to the player's left
        * 1 of the resource opposite the player
    """
    rng = random.Random(seed)

    # Shuffle order deck
    order_deck = list(data.order_cards)
    rng.shuffle(order_deck)

    # Assign board IDs randomly (boards 1–4, one per player)
    board_ids = [1, 2, 3, 4]
    rng.shuffle(board_ids)

    # Set resource tile orientation (0–3)
    resource_tile_orientation = rng.randint(0, 3)

    # Build initial villes token holders (all unclaimed)
    region_names = [ct.region_name for ct in data.customer_tokens]
    villes_holders: dict[str, int | None] = {r: None for r in region_names}

    # Create players
    players: list[PlayerState] = []
    for pid in range(4):
        workers = [
            Worker(worker_id=i, cheese_type=ct)
            for i, ct in enumerate(CheeseType)
        ]
        player = PlayerState(
            player_id=pid,
            board_id=board_ids[pid],
            workers=workers,
        )

        # Starting resources:
        # "Left" = one step clockwise from the player's facing resource
        # "Opposite" = two steps from facing
        facing_idx = (pid + resource_tile_orientation) % 4
        left_resource = RESOURCE_ORDER[(facing_idx + 1) % 4]
        opposite_resource = RESOURCE_ORDER[(facing_idx + 2) % 4]
        player.resources[left_resource] = 2
        player.resources[opposite_resource] = 1

        players.append(player)

    return GameState(
        rotation_index=0,
        turn_number=1,
        players=players,
        game_end_triggered=False,
        game_over=False,
        order_card_deck=order_deck,
        resource_tile_orientation=resource_tile_orientation,
        villes_customer_token_holders=villes_holders,
    )


def is_game_over(state: GameState) -> bool:
    """Return True if state.game_over is set."""
    return state.game_over
