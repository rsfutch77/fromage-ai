"""Core enums and constants shared across the game module.

Defines CheeseType, AgeType, ResourceType, VenueType, SpaceType,
FruitRequirement, and WorkerLocation.

See requirements section 1.1 and 3.1.
"""

from enum import Enum


class IllegalActionError(Exception):
    """Raised when an illegal game action is attempted."""


class CheeseType(Enum):
    SOFT = "SOFT"
    HARD = "HARD"
    BLEU = "BLEU"


class AgeType(Enum):
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"

    @property
    def turns(self) -> int:
        """Number of turns this worker is away (1/2/3 for Bronze/Silver/Gold)."""
        _turns = {"BRONZE": 1, "SILVER": 2, "GOLD": 3}
        return _turns[self.value]


class ResourceType(Enum):
    STRUCTURE = "STRUCTURE"
    LIVESTOCK = "LIVESTOCK"
    FRUIT = "FRUIT"
    ORDER = "ORDER"


class VenueType(Enum):
    FROMAGERIE = "FROMAGERIE"
    BISTRO = "BISTRO"
    VILLES = "VILLES"
    FESTIVAL = "FESTIVAL"


class SpaceType(Enum):
    CHEESE = "CHEESE"
    FREE_SAMPLE = "FREE_SAMPLE"
    EMPTY = "EMPTY"


class FruitRequirement(Enum):
    """Whether a cheese space requires spending Fruit or Jam."""
    NONE = "NONE"
    FRUIT = "FRUIT"
    JAM = "JAM"


class WorkerLocation(Enum):
    IN_HAND = "IN_HAND"
    ON_RESOURCE_TILE = "ON_RESOURCE_TILE"
    ON_CHEESE_SPACE = "ON_CHEESE_SPACE"
    ON_BARN = "ON_BARN"


# Canonical ordering for board rotation and resource tile orientation.
# Index 0 faces player 0 at orientation/rotation 0.
VENUE_ORDER: list[VenueType] = [
    VenueType.FROMAGERIE,
    VenueType.BISTRO,
    VenueType.VILLES,
    VenueType.FESTIVAL,
]

RESOURCE_ORDER: list[ResourceType] = [
    ResourceType.STRUCTURE,
    ResourceType.LIVESTOCK,
    ResourceType.FRUIT,
    ResourceType.ORDER,
]
