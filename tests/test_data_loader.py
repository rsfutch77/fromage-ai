"""Tests for the GameDataLoader module. See 2-requirements.md req 1.2.16."""

import pytest
from src.game.data_loader import GameDataLoader, FESTIVAL_BONUS_PER_EXTRA, ORDER_BONUS_PER_EXTRA
from src.game.types import CheeseType, AgeType, SpaceType, FruitRequirement


@pytest.fixture(scope="module")
def loader() -> GameDataLoader:
    return GameDataLoader()


def test_fromagerie_spaces_non_empty(loader):
    spaces = loader.fromagerie_spaces
    assert len(spaces) > 0


def test_fromagerie_shelves_non_empty(loader):
    assert len(loader.fromagerie_shelves) > 0


def test_bistro_spaces_non_empty(loader):
    assert len(loader.bistro_spaces) > 0


def test_villes_spaces_non_empty(loader):
    assert len(loader.villes_spaces) > 0


def test_festival_spaces_non_empty(loader):
    assert len(loader.festival_spaces) > 0


def test_milking_parlours_non_empty(loader):
    assert len(loader.milking_parlours) > 0


def test_player_board_structures_non_empty(loader):
    assert len(loader.player_board_structures) > 0


def test_customer_tokens_non_empty(loader):
    assert len(loader.customer_tokens) > 0


def test_scoring_fromagerie_non_empty(loader):
    assert len(loader.scoring_fromagerie) > 0


def test_scoring_festival_non_empty(loader):
    assert len(loader.scoring_festival) > 0


def test_order_cards_exactly_36(loader):
    """Req 1.2.10: exactly 36 cards total."""
    cards = loader.order_cards
    assert len(cards) == 36


def test_order_cards_4_per_type_age(loader):
    """Req 1.2.10: exactly 4 of each CheeseType × AgeType combination."""
    from collections import Counter
    cards = loader.order_cards
    counts = Counter((c.cheese_type, c.age) for c in cards)
    for cheese in CheeseType:
        for age in AgeType:
            assert counts[(cheese, age)] == 4, f"Expected 4 for {cheese}×{age}, got {counts[(cheese, age)]}"


def test_bistro_score_for_clamps_at_3_plus(loader):
    """Req 1.2.13: bistro_score_for(5) returns the 3+ row."""
    row = loader.bistro_score_for(5)
    assert row.pairings == 3
    row3 = loader.bistro_score_for(3)
    assert row3.pairings == 3


def test_free_sample_festival_space_has_none_type_and_age(loader):
    """Req 1.2.16: FREE_SAMPLE spaces have None for cheese_type and age."""
    free_samples = [s for s in loader.festival_spaces if s.space_type == SpaceType.FREE_SAMPLE]
    assert len(free_samples) > 0, "Expected at least one FREE_SAMPLE space"
    for s in free_samples:
        assert s.cheese_type is None, f"FREE_SAMPLE space has cheese_type {s.cheese_type}"
        assert s.age is None, f"FREE_SAMPLE space has age {s.age}"
        assert s.fruit_requirement == FruitRequirement.NONE


def test_festival_bonus_per_extra_constant():
    assert FESTIVAL_BONUS_PER_EXTRA == 5


def test_order_bonus_per_extra_constant():
    assert ORDER_BONUS_PER_EXTRA == 4


def test_scoring_fromagerie_includes_zero_and_one(loader):
    rubric = loader.scoring_fromagerie
    assert rubric[0] == 0
    assert rubric[1] == 0


def test_scoring_festival_includes_zero_and_one(loader):
    rubric = loader.scoring_festival
    assert rubric[0] == 0
    assert rubric[1] == 0


def test_customer_tokens_region_names_lowercase(loader):
    """Req 1.2.9: region_name normalised to lowercase."""
    for ct in loader.customer_tokens:
        assert ct.region_name == ct.region_name.lower()


def test_milking_parlour_wild_is_none(loader):
    """Parlour 4 on every board has bonus_cheese_type=None and bonus_cheese_age=None."""
    wild_parlours = [p for p in loader.milking_parlours if p.parlour_num == 4]
    assert len(wild_parlours) > 0
    for p in wild_parlours:
        assert p.bonus_cheese_type is None
        assert p.bonus_cheese_age is None


def test_file_not_found_raises(tmp_path):
    """Req 1.2.15: FileNotFoundError raised for missing CSV."""
    loader_bad = GameDataLoader(data_dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        _ = loader_bad.fromagerie_spaces
