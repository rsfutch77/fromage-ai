"""Tests for the scoring module. See 2-requirements.md section 5.9.4."""

import copy

import pytest

from src.game.board import setup_game
from src.game.data_loader import GameDataLoader, OrderCard
from src.game.scoring import (
    ScoreBreakdown,
    score_bistro,
    score_festival,
    score_fromagerie,
    score_fruit,
    score_game,
    score_orders,
    score_villes,
)
from src.game.state import PlacedCheese
from src.game.types import AgeType, CheeseType, SpaceType, VenueType


@pytest.fixture
def data():
    return GameDataLoader()


@pytest.fixture
def state(data):
    return setup_game(data, seed=1)


# ---------------------------------------------------------------------------
# Festival scoring (req 5.9.4)
# ---------------------------------------------------------------------------

def test_score_festival_simple_adjacency(data):
    """Two adjacent player tokens form a group and score > 0."""
    cheese_spaces = [sp for sp in data.festival_spaces if sp.space_type == SpaceType.CHEESE]
    if len(cheese_spaces) < 2:
        pytest.skip("Not enough cheese spaces in festival data")

    # Find two orthogonally adjacent cheese spaces
    positions = {(sp.row, sp.col): sp for sp in cheese_spaces}
    adjacent_pair = None
    for sp in cheese_spaces:
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            neighbour = (sp.row + dr, sp.col + dc)
            if neighbour in positions:
                adjacent_pair = (sp, positions[neighbour])
                break
        if adjacent_pair:
            break

    if adjacent_pair is None:
        pytest.skip("No adjacent festival cheese spaces found")

    sp1, sp2 = adjacent_pair
    placed = [
        PlacedCheese(cheese_type=sp1.cheese_type, age=sp1.age,
                     venue=VenueType.FESTIVAL, player_id=0,
                     row=sp1.row, col=sp1.col),
        PlacedCheese(cheese_type=sp2.cheese_type, age=sp2.age,
                     venue=VenueType.FESTIVAL, player_id=0,
                     row=sp2.row, col=sp2.col),
    ]
    scoring_table = data.scoring_festival
    score = score_festival(0, placed, data.festival_spaces, scoring_table)
    # Group size >= 2 (may include adjacent free samples), so score >= scoring_table[2]
    assert score >= scoring_table[2]
    # An isolated single token would score 0 (size=1 not in table), so > 0 confirms adjacency
    assert score > 0


def test_score_festival_free_sample_included_in_group(data):
    """FREE_SAMPLE spaces count toward group size if adjacent to player tokens."""
    free_samples = [sp for sp in data.festival_spaces if sp.space_type == SpaceType.FREE_SAMPLE]
    cheese_spaces = [sp for sp in data.festival_spaces if sp.space_type == SpaceType.CHEESE]
    if not free_samples or not cheese_spaces:
        pytest.skip("No free sample or cheese spaces in festival data")

    # Find a player cheese space adjacent to a free sample
    fs_positions = {(sp.row, sp.col) for sp in free_samples}
    adjacent = None
    for sp in cheese_spaces:
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            if (sp.row + dr, sp.col + dc) in fs_positions:
                adjacent = sp
                break
        if adjacent:
            break

    if adjacent is None:
        pytest.skip("No cheese space adjacent to a free sample in festival data")

    placed = [
        PlacedCheese(cheese_type=adjacent.cheese_type, age=adjacent.age,
                     venue=VenueType.FESTIVAL, player_id=0,
                     row=adjacent.row, col=adjacent.col),
    ]
    scoring_table = data.scoring_festival

    # Score including free sample adjacency — group size should be 2
    score_with = score_festival(0, placed, data.festival_spaces, scoring_table)
    expected = scoring_table[2]  # group of 2 (player token + free sample)
    assert score_with == expected


def test_score_festival_no_tokens_returns_zero(data):
    """Score is 0 when the player has no Festival tokens."""
    score = score_festival(0, [], data.festival_spaces, data.scoring_festival)
    assert score == 0


# ---------------------------------------------------------------------------
# Bistro scoring (req 5.9.4)
# ---------------------------------------------------------------------------

def test_score_bistro_zero_pairings(data):
    """With 0 pairings the score is based purely on per-age-tier tokens."""
    # Place one Bronze and one Silver token at DIFFERENT tables
    spaces = data.bistro_spaces
    if len(spaces) < 2:
        pytest.skip("Not enough bistro spaces")

    # Find two spaces on different tables
    by_table: dict = {}
    for sp in spaces:
        by_table.setdefault(sp.table_id, []).append(sp)
    tables = [t for t, sps in by_table.items() if sps]
    if len(tables) < 2:
        pytest.skip("Not enough bistro tables")

    sp1 = by_table[tables[0]][0]
    sp2 = by_table[tables[1]][0]

    placed = [
        PlacedCheese(cheese_type=sp1.cheese_type, age=sp1.plate_age,
                     venue=VenueType.BISTRO, player_id=0,
                     space_id=sp1.space_id, table_id=sp1.table_id),
        PlacedCheese(cheese_type=sp2.cheese_type, age=sp2.plate_age,
                     venue=VenueType.BISTRO, player_id=0,
                     space_id=sp2.space_id, table_id=sp2.table_id),
    ]
    from src.game.types import AgeType
    scoring = data.scoring_bistro
    score = score_bistro(0, placed, spaces, scoring)

    # 0 pairings → use the row for 0
    row = next(r for r in scoring if r.pairings == 0)
    expected = 0
    for pc in placed:
        if pc.age == AgeType.BRONZE:
            expected += row.bronze
        elif pc.age == AgeType.SILVER:
            expected += row.silver
        else:
            expected += row.gold
    assert score == expected


def test_score_bistro_no_tokens_returns_zero(data):
    assert score_bistro(0, [], data.bistro_spaces, data.scoring_bistro) == 0


# ---------------------------------------------------------------------------
# Fruit scoring (req 5.9.4)
# ---------------------------------------------------------------------------

def test_score_fruit_zero_when_either_factor_is_zero(state):
    player = state.players[0]
    player.fruit_spent_on_fruited = 0
    player.fruit_spent_on_jam = 5
    assert score_fruit(player) == 0

    player.fruit_spent_on_fruited = 3
    player.fruit_spent_on_jam = 0
    assert score_fruit(player) == 0


def test_score_fruit_multiplicative(state):
    player = state.players[0]
    player.fruit_spent_on_fruited = 3
    player.fruit_spent_on_jam = 4
    assert score_fruit(player) == 12


# ---------------------------------------------------------------------------
# Order scoring (req 5.9.4)
# ---------------------------------------------------------------------------

def test_score_orders_zero_orders(data):
    assert score_orders([], data.scoring_orders) == 0


def test_score_orders_within_table(data):
    rubric = data.scoring_orders
    for n in range(1, 7):
        orders = [OrderCard(cheese_type=CheeseType.SOFT, age=AgeType.BRONZE)] * n
        assert score_orders(orders, rubric) == rubric[n]


def test_score_orders_excess_triggers_bonus(data):
    """7+ orders apply ORDER_BONUS_PER_EXTRA = 4 per extra order."""
    from src.game.data_loader import ORDER_BONUS_PER_EXTRA
    rubric = data.scoring_orders
    orders_7 = [OrderCard(cheese_type=CheeseType.SOFT, age=AgeType.BRONZE)] * 7
    expected = rubric[6] + ORDER_BONUS_PER_EXTRA * 1
    assert score_orders(orders_7, rubric) == expected

    orders_9 = orders_7 + [OrderCard(cheese_type=CheeseType.SOFT, age=AgeType.BRONZE)] * 2
    expected9 = rubric[6] + ORDER_BONUS_PER_EXTRA * 3
    assert score_orders(orders_9, rubric) == expected9


# ---------------------------------------------------------------------------
# score_game sums categories (req 5.9.4)
# ---------------------------------------------------------------------------

def test_score_game_totals_match_sum_of_categories(data, state):
    """score_game total == sum of individual category scores."""
    scores = score_game(state, data)
    assert len(scores) == 4
    for sb in scores:
        expected_total = (
            sb.festival + sb.villes + sb.fromagerie + sb.bistro
            + sb.orders + sb.fruit + sb.headquarters + sb.unused_resources
        )
        assert sb.total == expected_total


def test_score_game_all_scores_non_negative(data, state):
    """All scoring categories should be >= 0 for a fresh game state."""
    scores = score_game(state, data)
    for sb in scores:
        assert sb.festival >= 0
        assert sb.villes >= 0
        assert sb.fromagerie >= 0
        assert sb.bistro >= 0
        assert sb.orders >= 0
        assert sb.fruit >= 0
        assert sb.headquarters >= 0
        assert sb.unused_resources >= 0
        assert sb.total >= 0
