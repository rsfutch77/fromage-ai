"""Loads all game data from CSV files into typed Python dataclasses.

Exposes a single GameDataLoader class whose properties return fully-typed
collections ready for use by the game engine.

See requirements section 1.2.
"""

import csv
from dataclasses import dataclass
from pathlib import Path

from src.game.types import AgeType, CheeseType, FruitRequirement, ResourceType, SpaceType, VenueType

# Module-level constants for scoring rules that extend beyond table limits.
FESTIVAL_BONUS_PER_EXTRA: int = 5  # Points per group member beyond size 7
ORDER_BONUS_PER_EXTRA: int = 4     # Points per order beyond 6


# ---------------------------------------------------------------------------
# Dataclasses returned by GameDataLoader
# ---------------------------------------------------------------------------

@dataclass
class FromagerieSpace:
    space_id: int
    shelf_id: int
    cheese_type: CheeseType
    age: AgeType
    fruit_requirement: FruitRequirement


@dataclass
class FromagerieShelf:
    shelf_id: int
    column: str          # "resource_bonus" or "point_bonus"
    age: AgeType
    immediate_bonus: str
    points_per_token: int


@dataclass
class BistroSpace:
    space_id: int
    table_id: int
    plate_age: AgeType
    cheese_type: CheeseType
    fruit_requirement: FruitRequirement


@dataclass
class VillesSpace:
    space_id: int
    city: str
    cheese_type: CheeseType
    age: AgeType
    fruit_requirement: FruitRequirement
    regions: list[str]


@dataclass
class FestivalSpace:
    row: int
    col: int
    space_type: SpaceType
    cheese_type: CheeseType | None
    age: AgeType | None
    fruit_requirement: FruitRequirement


@dataclass
class MilkingParlour:
    board_id: int
    parlour_num: int
    livestock_cost: int
    bonus_cheese_type: CheeseType | None  # None = wild (player's choice)
    bonus_cheese_age: AgeType | None      # None = wild (player's choice)


@dataclass
class PlayerBoardStructure:
    board_id: int
    barn_resource: ResourceType
    loading_dock_venue: VenueType
    loading_dock_reward: ResourceType
    greenhouse_resource: ResourceType
    headquarters_condition: str
    structure_costs: list[int]  # [cost_slot1, cost_slot2, cost_slot3, cost_slot4]


@dataclass
class CustomerToken:
    region_id: int
    region_name: str
    win_value: int
    tie_value: int


@dataclass
class OrderCard:
    cheese_type: CheeseType
    age: AgeType


@dataclass
class BistroScoringRow:
    pairings: int          # 3 means "3 or more"
    bronze: int
    silver: int
    gold: int


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _parse_fruit_requirement(raw: str) -> FruitRequirement:
    mapping = {"": FruitRequirement.NONE, "fruit": FruitRequirement.FRUIT, "jam": FruitRequirement.JAM}
    key = raw.strip().lower()
    if key not in mapping:
        raise ValueError(f"Unrecognised fruit requirement: {raw!r}")
    return mapping[key]


def _parse_age(raw: str) -> AgeType:
    try:
        return AgeType[raw.upper()]
    except KeyError:
        raise ValueError(f"Unrecognised AgeType: {raw!r}")


def _parse_cheese(raw: str) -> CheeseType:
    try:
        return CheeseType[raw.upper()]
    except KeyError:
        raise ValueError(f"Unrecognised CheeseType: {raw!r}")


def _parse_resource(raw: str) -> ResourceType:
    """Map plain-English words used in player_board_structures.csv to ResourceType."""
    mapping = {
        "animal": ResourceType.LIVESTOCK,
        "livestock": ResourceType.LIVESTOCK,
        "structure": ResourceType.STRUCTURE,
        "fruit": ResourceType.FRUIT,
        "order": ResourceType.ORDER,
    }
    key = raw.strip().lower()
    if key not in mapping:
        raise ValueError(f"Unrecognised resource: {raw!r}")
    return mapping[key]


def _parse_venue(raw: str) -> VenueType:
    mapping = {
        "fromagerie": VenueType.FROMAGERIE,
        "bistro": VenueType.BISTRO,
        "villes": VenueType.VILLES,
        "festival": VenueType.FESTIVAL,
    }
    key = raw.strip().lower()
    if key not in mapping:
        raise ValueError(f"Unrecognised venue: {raw!r}")
    return mapping[key]


def _parse_loading_dock(raw: str) -> tuple[VenueType, ResourceType]:
    """Parse strings like 'cheese in fromagerie = order' or 'each cheese in villes = structure'."""
    # Normalise to lowercase and strip leading "each "
    text = raw.strip().lower().lstrip("each ").strip()
    # Expected format: "cheese in {venue} = {resource}"
    if "=" not in text or " in " not in text:
        raise ValueError(f"Cannot parse loading dock spec: {raw!r}")
    left, right = text.split("=", 1)
    # left: "cheese in {venue} " → extract venue
    venue_part = left.split("in", 1)[1].strip().rstrip()
    venue = _parse_venue(venue_part)
    resource = _parse_resource(right.strip())
    return venue, resource


def _parse_greenhouse(raw: str) -> ResourceType:
    """Parse strings like 'gain up to 1 fruit per turn each time you gain frut'."""
    text = raw.strip().lower()
    for keyword, resource in [
        ("fruit", ResourceType.FRUIT),
        ("frut", ResourceType.FRUIT),   # typo in CSV
        ("order", ResourceType.ORDER),
        ("animal", ResourceType.LIVESTOCK),
        ("structure", ResourceType.STRUCTURE),
    ]:
        if keyword in text:
            return resource
    raise ValueError(f"Cannot parse greenhouse resource from: {raw!r}")


def _load_csv(path: Path) -> list[dict[str, str]]:
    """Load a CSV, skipping comment lines (lines starting with '#')."""
    if not path.exists():
        raise FileNotFoundError(f"Required data file not found: {path}")
    rows: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(
            line for line in fh if not line.lstrip().startswith("#")
        )
        for row in reader:
            rows.append(dict(row))
    return rows


# ---------------------------------------------------------------------------
# GameDataLoader
# ---------------------------------------------------------------------------

class GameDataLoader:
    """Loads and caches all game data from CSV files in *data_dir*."""

    def __init__(self, data_dir: Path = Path("data/")) -> None:
        self._dir = data_dir
        self._cache: dict[str, object] = {}

    # ------------------------------------------------------------------
    # Venue spaces
    # ------------------------------------------------------------------

    @property
    def fromagerie_spaces(self) -> list[FromagerieSpace]:
        if "fromagerie_spaces" not in self._cache:
            rows = _load_csv(self._dir / "fromagerie_spaces.csv")
            result = []
            for row in rows:
                result.append(FromagerieSpace(
                    space_id=int(row["space_id"]),
                    shelf_id=int(row["shelf_id"]),
                    cheese_type=_parse_cheese(row["cheese_type"]),
                    age=_parse_age(row["direction"]),
                    fruit_requirement=_parse_fruit_requirement(row.get("requires_fruit", "").strip()),
                ))
            self._cache["fromagerie_spaces"] = result
        return self._cache["fromagerie_spaces"]  # type: ignore[return-value]

    @property
    def fromagerie_shelves(self) -> list[FromagerieShelf]:
        if "fromagerie_shelves" not in self._cache:
            rows = _load_csv(self._dir / "fromagerie_shelves.csv")
            result = []
            for row in rows:
                result.append(FromagerieShelf(
                    shelf_id=int(row["shelf_id"]),
                    column=row["column"].strip(),
                    age=_parse_age(row["age"]),
                    immediate_bonus=row["immediate_bonus"].strip(),
                    points_per_token=int(row["points_per_token"]),
                ))
            self._cache["fromagerie_shelves"] = result
        return self._cache["fromagerie_shelves"]  # type: ignore[return-value]

    @property
    def bistro_spaces(self) -> list[BistroSpace]:
        if "bistro_spaces" not in self._cache:
            rows = _load_csv(self._dir / "bistro_spaces.csv")
            result = []
            for row in rows:
                result.append(BistroSpace(
                    space_id=int(row["space_id"]),
                    table_id=int(row["table_id"]),
                    plate_age=_parse_age(row["plate_age"]),
                    cheese_type=_parse_cheese(row["cheese_type"]),
                    fruit_requirement=_parse_fruit_requirement(row.get("requires_fruit", "").strip()),
                ))
            self._cache["bistro_spaces"] = result
        return self._cache["bistro_spaces"]  # type: ignore[return-value]

    @property
    def villes_spaces(self) -> list[VillesSpace]:
        if "villes_spaces" not in self._cache:
            rows = _load_csv(self._dir / "villes_spaces.csv")
            result = []
            for row in rows:
                regions = [
                    row[k].strip()
                    for k in ("region_1", "region_2", "region_3")
                    if row.get(k, "").strip()
                ]
                result.append(VillesSpace(
                    space_id=int(row["space_id"]),
                    city=row["city"].strip(),
                    cheese_type=_parse_cheese(row["cheese_type"]),
                    age=_parse_age(row["direction"]),
                    fruit_requirement=_parse_fruit_requirement(row.get("fruit", "").strip()),
                    regions=regions,
                ))
            self._cache["villes_spaces"] = result
        return self._cache["villes_spaces"]  # type: ignore[return-value]

    @property
    def festival_spaces(self) -> list[FestivalSpace]:
        if "festival_spaces" not in self._cache:
            rows = _load_csv(self._dir / "festival_spaces.csv")
            result = []
            _space_type_map = {
                "cheese": SpaceType.CHEESE,
                "free_sample": SpaceType.FREE_SAMPLE,
                "empty": SpaceType.EMPTY,
            }
            for row in rows:
                raw_type = row["space_type"].strip().lower()
                if raw_type not in _space_type_map:
                    raise ValueError(f"Unrecognised space_type: {row['space_type']!r}")
                space_type = _space_type_map[raw_type]
                if space_type == SpaceType.CHEESE:
                    cheese_type = _parse_cheese(row["cheese_type"])
                    age = _parse_age(row["direction"])
                    fruit_req = _parse_fruit_requirement(row.get("requires_fruit", "").strip())
                else:
                    cheese_type = None
                    age = None
                    fruit_req = FruitRequirement.NONE
                result.append(FestivalSpace(
                    row=int(row["row"]),
                    col=int(row["col"]),
                    space_type=space_type,
                    cheese_type=cheese_type,
                    age=age,
                    fruit_requirement=fruit_req,
                ))
            self._cache["festival_spaces"] = result
        return self._cache["festival_spaces"]  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Player board data
    # ------------------------------------------------------------------

    @property
    def milking_parlours(self) -> list[MilkingParlour]:
        if "milking_parlours" not in self._cache:
            rows = _load_csv(self._dir / "milking_parlours.csv")
            result = []
            for row in rows:
                raw_type = row["bonus_cheese_type"].strip()
                raw_age = row["bonus_cheese_age"].strip()
                bonus_type = None if raw_type.lower() == "any" else _parse_cheese(raw_type)
                bonus_age = None if raw_age.lower() == "any" else _parse_age(raw_age)
                result.append(MilkingParlour(
                    board_id=int(row["board_id"]),
                    parlour_num=int(row["parlour_num"]),
                    livestock_cost=int(row["livestock_cost"]),
                    bonus_cheese_type=bonus_type,
                    bonus_cheese_age=bonus_age,
                ))
            self._cache["milking_parlours"] = result
        return self._cache["milking_parlours"]  # type: ignore[return-value]

    @property
    def player_board_structures(self) -> list[PlayerBoardStructure]:
        if "player_board_structures" not in self._cache:
            rows = _load_csv(self._dir / "player_board_structures.csv")
            result = []
            for row in rows:
                barn_resource = _parse_resource(row["structure_size_1"].strip())
                dock_venue, dock_reward = _parse_loading_dock(row["structure_size_2"])
                greenhouse_resource = _parse_greenhouse(row["structure_size_3"])
                hq_condition = row["structure_size_4"].strip()
                costs = [
                    int(row["structure_size_1_cost"]),
                    int(row["structure_size_2_cost"]),
                    int(row["structure_size_3_cost"]),
                    int(row["structure_size_4_cost"]),
                ]
                result.append(PlayerBoardStructure(
                    board_id=int(row["board_id"]),
                    barn_resource=barn_resource,
                    loading_dock_venue=dock_venue,
                    loading_dock_reward=dock_reward,
                    greenhouse_resource=greenhouse_resource,
                    headquarters_condition=hq_condition,
                    structure_costs=costs,
                ))
            self._cache["player_board_structures"] = result
        return self._cache["player_board_structures"]  # type: ignore[return-value]

    @property
    def customer_tokens(self) -> list[CustomerToken]:
        if "customer_tokens" not in self._cache:
            rows = _load_csv(self._dir / "customer_tokens.csv")
            result = []
            for row in rows:
                result.append(CustomerToken(
                    region_id=int(row["region_id"]),
                    region_name=row["region_name"].strip().lower(),
                    win_value=int(row["win_value_4p"]),
                    tie_value=int(row["tie_value_4p"]),
                ))
            self._cache["customer_tokens"] = result
        return self._cache["customer_tokens"]  # type: ignore[return-value]

    @property
    def order_cards(self) -> list[OrderCard]:
        """Programmatically generate 36 OrderCards (4 per CheeseType × AgeType combo)."""
        if "order_cards" not in self._cache:
            cards: list[OrderCard] = []
            for cheese in CheeseType:
                for age in AgeType:
                    for _ in range(4):
                        cards.append(OrderCard(cheese_type=cheese, age=age))
            self._cache["order_cards"] = cards
        return self._cache["order_cards"]  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Scoring tables
    # ------------------------------------------------------------------

    @property
    def scoring_fromagerie(self) -> dict[int, int]:
        """Return {shelves_occupied: base_points} for 0–6 (0 and 1 score 0)."""
        if "scoring_fromagerie" not in self._cache:
            rows = _load_csv(self._dir / "scoring_fromagerie.csv")
            rubric: dict[int, int] = {0: 0, 1: 0}
            for row in rows:
                rubric[int(row["shelves_occupied"])] = int(row["base_points"])
            self._cache["scoring_fromagerie"] = rubric
        return self._cache["scoring_fromagerie"]  # type: ignore[return-value]

    @property
    def scoring_festival(self) -> dict[int, int]:
        """Return {group_size: points} for sizes 0–7. Also sets FESTIVAL_BONUS_PER_EXTRA."""
        if "scoring_festival" not in self._cache:
            rows = _load_csv(self._dir / "scoring_festival.csv")
            rubric: dict[int, int] = {0: 0, 1: 0}
            for row in rows:
                size_raw = row["orthoganal_group_size"].strip()
                try:
                    size = int(size_raw)
                except ValueError:
                    continue  # skip "each additional beyond 7" text row
                rubric[size] = int(row["points"])
            self._cache["scoring_festival"] = rubric
        return self._cache["scoring_festival"]  # type: ignore[return-value]

    @property
    def scoring_bistro(self) -> list[BistroScoringRow]:
        if "scoring_bistro" not in self._cache:
            rows = _load_csv(self._dir / "scoring_bistro.csv")
            result = []
            for row in rows:
                raw_pairings = row["pairings"].strip()
                pairings = 3 if raw_pairings == "3+" else int(raw_pairings)
                result.append(BistroScoringRow(
                    pairings=pairings,
                    bronze=int(row["points_per_bronze"]),
                    silver=int(row["points_per_silver"]),
                    gold=int(row["points_per_gold"]),
                ))
            self._cache["scoring_bistro"] = result
        return self._cache["scoring_bistro"]  # type: ignore[return-value]

    def bistro_score_for(self, pairings: int) -> BistroScoringRow:
        """Return the BistroScoringRow for the given pairing count, clamped at 3+."""
        rows = self.scoring_bistro
        clamped = min(pairings, 3)
        for row in rows:
            if row.pairings == clamped:
                return row
        raise ValueError(f"No bistro scoring row found for pairings={pairings}")

    @property
    def scoring_orders(self) -> dict[int, int]:
        """Return {order_count: points} for 1–6. ORDER_BONUS_PER_EXTRA applies beyond 6."""
        if "scoring_orders" not in self._cache:
            rows = _load_csv(self._dir / "order_scoring.csv")
            rubric: dict[int, int] = {}
            for row in rows:
                count_raw = row["order_count"].strip()
                try:
                    count = int(count_raw)
                except ValueError:
                    continue  # skip "points for each additional beyond 6" text row
                rubric[count] = int(row["points"])
            self._cache["scoring_orders"] = rubric
        return self._cache["scoring_orders"]  # type: ignore[return-value]
