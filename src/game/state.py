"""Game state dataclasses: Worker, PlacedCheese, PlayerState, GameState.

GameState is the single source of truth for an in-progress game.
All state mutations return new GameState instances (no in-place mutation).

See requirements section 2.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from src.game.types import (
    AgeType,
    CheeseType,
    ResourceType,
    RESOURCE_ORDER,
    VenueType,
    VENUE_ORDER,
    WorkerLocation,
)
from src.game.data_loader import OrderCard


# ---------------------------------------------------------------------------
# PlacedCheese
# ---------------------------------------------------------------------------

@dataclass
class PlacedCheese:
    """A cheese token placed on any venue board."""
    cheese_type: CheeseType
    age: AgeType
    venue: VenueType
    player_id: int
    space_id: int | None = None           # Fromagerie, Bistro, Villes
    row: int | None = None                # Festival grid
    col: int | None = None                # Festival grid
    table_id: int | None = None           # Bistro (denormalised convenience)
    from_milking_parlour: bool = False    # True when placed via milking parlour (no worker sent)


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

@dataclass
class Worker:
    """One of a player's three workers, each dedicated to one CheeseType."""
    worker_id: int
    cheese_type: CheeseType
    location: WorkerLocation = WorkerLocation.IN_HAND
    venue: VenueType | None = None
    space_id: int | None = None
    row: int | None = None   # Festival grid row (when venue == FESTIVAL)
    col: int | None = None   # Festival grid col (when venue == FESTIVAL)
    return_after_rotation: int | None = None

    def is_available(self, current_rotation: int) -> bool:
        """True if the worker is in hand or due to return this rotation."""
        if self.location == WorkerLocation.IN_HAND:
            return True
        return self.return_after_rotation == current_rotation


# ---------------------------------------------------------------------------
# PlayerState
# ---------------------------------------------------------------------------

@dataclass
class PlayerState:
    """All state belonging to a single player."""
    player_id: int
    board_id: int
    resources: dict[ResourceType, int] = field(default_factory=lambda: {r: 0 for r in ResourceType})
    workers: list[Worker] = field(default_factory=list)
    cheese_tokens_remaining: int = 15
    cheese_tokens_on_board: list[PlacedCheese] = field(default_factory=list)
    order_cards_held: list[OrderCard] = field(default_factory=list)
    orders_completed: list[OrderCard] = field(default_factory=list)
    structures_unlocked: list[bool] = field(default_factory=lambda: [False, False, False, False])  # slot 1–4
    milking_parlours_used: list[int] = field(default_factory=lambda: [0, 0, 0, 0])  # use count per parlour slot
    fruit_spent_on_fruited: int = 0
    fruit_spent_on_jam: int = 0


# ---------------------------------------------------------------------------
# GameState
# ---------------------------------------------------------------------------

@dataclass
class GameState:
    """Complete, serialisable snapshot of an in-progress game."""
    rotation_index: int
    turn_number: int
    players: list[PlayerState]
    game_end_triggered: bool
    game_over: bool
    order_card_deck: list[OrderCard]
    resource_tile_orientation: int        # 0–3; initial offset set at setup; rotation applied via rotation_index
    villes_customer_token_holders: dict[str, int | None]  # region → player_id or None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def venue_facing(self, player_id: int) -> VenueType:
        """Which venue is currently facing *player_id* given rotation_index."""
        return VENUE_ORDER[(player_id + self.rotation_index) % 4]

    def resource_facing(self, player_id: int) -> ResourceType:
        """Which resource type the Resource Tile shows to *player_id*.

        The resource tile rotates with the board (counter-clockwise relative
        to players), so rotation_index is subtracted.
        """
        return RESOURCE_ORDER[(player_id + self.resource_tile_orientation - self.rotation_index) % 4]

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_json(self) -> str:
        """Serialise the full game state to a JSON string."""
        return json.dumps(_state_to_dict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, data: str) -> GameState:
        """Deserialise a JSON string back into a GameState.

        Raises ValueError on malformed input.
        """
        try:
            raw = json.loads(data)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed GameState JSON: {exc}") from exc
        try:
            return _state_from_dict(raw)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid GameState structure: {exc}") from exc


# ---------------------------------------------------------------------------
# Serialisation helpers (private)
# ---------------------------------------------------------------------------

def _placed_cheese_to_dict(pc: PlacedCheese) -> dict:
    return {
        "cheese_type": pc.cheese_type.name,
        "age": pc.age.name,
        "venue": pc.venue.name,
        "player_id": pc.player_id,
        "space_id": pc.space_id,
        "row": pc.row,
        "col": pc.col,
        "table_id": pc.table_id,
        "from_milking_parlour": pc.from_milking_parlour,
    }


def _placed_cheese_from_dict(d: dict) -> PlacedCheese:
    return PlacedCheese(
        cheese_type=CheeseType[d["cheese_type"]],
        age=AgeType[d["age"]],
        venue=VenueType[d["venue"]],
        player_id=d["player_id"],
        space_id=d.get("space_id"),
        row=d.get("row"),
        col=d.get("col"),
        table_id=d.get("table_id"),
        from_milking_parlour=d.get("from_milking_parlour", False),
    )


def _worker_to_dict(w: Worker) -> dict:
    return {
        "worker_id": w.worker_id,
        "cheese_type": w.cheese_type.name,
        "location": w.location.name,
        "venue": w.venue.name if w.venue else None,
        "space_id": w.space_id,
        "row": w.row,
        "col": w.col,
        "return_after_rotation": w.return_after_rotation,
    }


def _worker_from_dict(d: dict) -> Worker:
    return Worker(
        worker_id=d["worker_id"],
        cheese_type=CheeseType[d["cheese_type"]],
        location=WorkerLocation[d["location"]],
        venue=VenueType[d["venue"]] if d["venue"] else None,
        space_id=d.get("space_id"),
        row=d.get("row"),
        col=d.get("col"),
        return_after_rotation=d.get("return_after_rotation"),
    )


def _order_card_to_dict(oc: OrderCard) -> dict:
    return {"cheese_type": oc.cheese_type.name, "age": oc.age.name}


def _order_card_from_dict(d: dict) -> OrderCard:
    return OrderCard(cheese_type=CheeseType[d["cheese_type"]], age=AgeType[d["age"]])


def _player_to_dict(p: PlayerState) -> dict:
    return {
        "player_id": p.player_id,
        "board_id": p.board_id,
        "resources": {k.name: v for k, v in p.resources.items()},
        "workers": [_worker_to_dict(w) for w in p.workers],
        "cheese_tokens_remaining": p.cheese_tokens_remaining,
        "cheese_tokens_on_board": [_placed_cheese_to_dict(pc) for pc in p.cheese_tokens_on_board],
        "order_cards_held": [_order_card_to_dict(oc) for oc in p.order_cards_held],
        "orders_completed": [_order_card_to_dict(oc) for oc in p.orders_completed],
        "structures_unlocked": p.structures_unlocked,
        "milking_parlours_used": p.milking_parlours_used,
        "fruit_spent_on_fruited": p.fruit_spent_on_fruited,
        "fruit_spent_on_jam": p.fruit_spent_on_jam,
    }


def _player_from_dict(d: dict) -> PlayerState:
    return PlayerState(
        player_id=d["player_id"],
        board_id=d["board_id"],
        resources={ResourceType[k]: v for k, v in d["resources"].items()},
        workers=[_worker_from_dict(w) for w in d["workers"]],
        cheese_tokens_remaining=d["cheese_tokens_remaining"],
        cheese_tokens_on_board=[_placed_cheese_from_dict(pc) for pc in d["cheese_tokens_on_board"]],
        order_cards_held=[_order_card_from_dict(oc) for oc in d["order_cards_held"]],
        orders_completed=[_order_card_from_dict(oc) for oc in d["orders_completed"]],
        structures_unlocked=d["structures_unlocked"],
        milking_parlours_used=d["milking_parlours_used"],
        fruit_spent_on_fruited=d["fruit_spent_on_fruited"],
        fruit_spent_on_jam=d["fruit_spent_on_jam"],
    )


def _state_to_dict(s: GameState) -> dict:
    return {
        "rotation_index": s.rotation_index,
        "turn_number": s.turn_number,
        "players": [_player_to_dict(p) for p in s.players],
        "game_end_triggered": s.game_end_triggered,
        "game_over": s.game_over,
        "order_card_deck": [_order_card_to_dict(oc) for oc in s.order_card_deck],
        "resource_tile_orientation": s.resource_tile_orientation,
        "villes_customer_token_holders": s.villes_customer_token_holders,
    }


def _state_from_dict(d: dict) -> GameState:
    return GameState(
        rotation_index=d["rotation_index"],
        turn_number=d["turn_number"],
        players=[_player_from_dict(p) for p in d["players"]],
        game_end_triggered=d["game_end_triggered"],
        game_over=d["game_over"],
        order_card_deck=[_order_card_from_dict(oc) for oc in d["order_card_deck"]],
        resource_tile_orientation=d["resource_tile_orientation"],
        villes_customer_token_holders=d["villes_customer_token_holders"],
    )
