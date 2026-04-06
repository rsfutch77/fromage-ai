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
    score_headquarters,
    score_orders,
    score_unused_resources,
    score_villes,
    winner,
)
from src.game.state import PlacedCheese
from src.game.types import AgeType, CheeseType, ResourceType, SpaceType, VenueType


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


# ---------------------------------------------------------------------------
# score_fromagerie (req 5.9.4)
# ---------------------------------------------------------------------------

def test_score_fromagerie_distinct_shelves(data):
    """Occupying N distinct shelves gives rubric[N] base points."""
    rubric = data.scoring_fromagerie
    # Two tokens on different shelves (shelf 4 = Bronze point_bonus, shelf 5 = Silver point_bonus)
    sp_shelf4 = next(sp for sp in data.fromagerie_spaces if sp.shelf_id == 4)
    sp_shelf5 = next(sp for sp in data.fromagerie_spaces if sp.shelf_id == 5)

    placed = [
        PlacedCheese(cheese_type=sp_shelf4.cheese_type, age=sp_shelf4.age,
                     venue=VenueType.FROMAGERIE, player_id=0, space_id=sp_shelf4.space_id),
        PlacedCheese(cheese_type=sp_shelf5.cheese_type, age=sp_shelf5.age,
                     venue=VenueType.FROMAGERIE, player_id=0, space_id=sp_shelf5.space_id),
    ]
    score = score_fromagerie(0, placed, data.fromagerie_shelves, data.fromagerie_spaces, rubric)
    # 2 distinct shelves → rubric[2], plus point_bonus per token
    shelf4 = next(sh for sh in data.fromagerie_shelves if sh.shelf_id == 4)
    shelf5 = next(sh for sh in data.fromagerie_shelves if sh.shelf_id == 5)
    expected = rubric[2] + shelf4.points_per_token + shelf5.points_per_token
    assert score == expected


def test_score_fromagerie_point_bonus_shelf(data):
    """Tokens on point_bonus shelves add points_per_token each."""
    shelf6 = next(sh for sh in data.fromagerie_shelves if sh.shelf_id == 6)
    sp = next(sp for sp in data.fromagerie_spaces
              if sp.shelf_id == 6 and sp.fruit_requirement.name == "NONE")

    placed = [
        PlacedCheese(cheese_type=sp.cheese_type, age=sp.age,
                     venue=VenueType.FROMAGERIE, player_id=0, space_id=sp.space_id),
    ]
    score = score_fromagerie(0, placed, data.fromagerie_shelves, data.fromagerie_spaces,
                              data.scoring_fromagerie)
    assert score == data.scoring_fromagerie[1] + shelf6.points_per_token


def test_score_fromagerie_no_tokens_returns_rubric_zero(data):
    """No tokens gives rubric.get(0, 0)."""
    score = score_fromagerie(0, [], data.fromagerie_shelves, data.fromagerie_spaces,
                              data.scoring_fromagerie)
    assert score == data.scoring_fromagerie.get(0, 0)


# ---------------------------------------------------------------------------
# score_villes (req 5.9.4)
# ---------------------------------------------------------------------------

def test_score_villes_single_winner(data, state):
    """Player dominating a region earns win_value for its customer token."""
    villes_sp = data.villes_spaces[0]
    region = villes_sp.regions[0]
    token = next(t for t in data.customer_tokens if t.region_name == region)

    # Give player 0 one token in that region; all others have none
    placed = PlacedCheese(cheese_type=villes_sp.cheese_type, age=villes_sp.age,
                          venue=VenueType.VILLES, player_id=0,
                          space_id=villes_sp.space_id)
    state.players[0].cheese_tokens_on_board.append(placed)

    points = score_villes(state, data)
    assert points.get(0, 0) >= token.win_value


def test_score_villes_tied_players_get_tie_value(data, state):
    """Two players tied in a region each earn tie_value."""
    villes_sp = data.villes_spaces[0]
    region = villes_sp.regions[0]
    token = next(t for t in data.customer_tokens if t.region_name == region)

    # Both player 0 and player 1 place one token in the same space (different players)
    for pid in (0, 1):
        placed = PlacedCheese(cheese_type=villes_sp.cheese_type, age=villes_sp.age,
                              venue=VenueType.VILLES, player_id=pid,
                              space_id=villes_sp.space_id)
        state.players[pid].cheese_tokens_on_board.append(placed)

    points = score_villes(state, data)
    assert points.get(0, 0) >= token.tie_value
    assert points.get(1, 0) >= token.tie_value


# ---------------------------------------------------------------------------
# score_headquarters (req 5.9.4)
# ---------------------------------------------------------------------------

def _make_player_state_for_board(board_id: int, data):
    """Return a minimal PlayerState with the given board_id."""
    from src.game.state import PlayerState
    return PlayerState(player_id=0, board_id=board_id)


def test_score_headquarters_not_unlocked(data, state):
    """Returns 0 when HQ slot (index 3) is not unlocked."""
    player = state.players[0]
    player.structures_unlocked[3] = False
    board = next(b for b in data.player_board_structures if b.board_id == player.board_id)
    assert score_headquarters(player, board, state, data) == 0


def test_score_headquarters_structure_condition(data, state):
    """Board 1: HQ scores sum of structure costs for each deployed structure."""
    board = next(b for b in data.player_board_structures if b.board_id == 1)
    player = next(p for p in state.players if p.board_id == 1)
    if player is None:
        pytest.skip("No player on board 1 in this seed")
    player.structures_unlocked = [True, True, False, True]  # slots 0,1,3 unlocked: costs 2+2+5=9
    assert score_headquarters(player, board, state, data) == 9


def test_score_headquarters_fruit_condition(data, state):
    """Board 2: HQ scores per fruit+jam spent."""
    board = next(b for b in data.player_board_structures if b.board_id == 2)
    player = next(p for p in state.players if p.board_id == 2)
    if player is None:
        pytest.skip("No player on board 2 in this seed")
    player.structures_unlocked[3] = True
    player.fruit_spent_on_fruited = 3
    player.fruit_spent_on_jam = 2
    assert score_headquarters(player, board, state, data) == 5


def test_score_headquarters_order_condition(data, state):
    """Board 3: HQ scores per completed order."""
    from src.game.data_loader import OrderCard
    board = next(b for b in data.player_board_structures if b.board_id == 3)
    player = next(p for p in state.players if p.board_id == 3)
    if player is None:
        pytest.skip("No player on board 3 in this seed")
    player.structures_unlocked[3] = True
    player.orders_completed = [OrderCard(cheese_type=CheeseType.SOFT, age=AgeType.BRONZE)] * 4
    assert score_headquarters(player, board, state, data) == 4


def test_score_headquarters_livestock_condition(data, state):
    """Board 4: HQ scores per livestock spent in milking parlours."""
    board = next(b for b in data.player_board_structures if b.board_id == 4)
    player = next(p for p in state.players if p.board_id == 4)
    if player is None:
        pytest.skip("No player on board 4 in this seed")
    player.structures_unlocked[3] = True
    parlours = sorted([p for p in data.milking_parlours if p.board_id == 4],
                      key=lambda p: p.parlour_num)
    # Simulate using each parlour once
    player.milking_parlours_used = [1 if i < len(parlours) else 0 for i in range(4)]
    expected = sum(p.livestock_cost for p in parlours)
    assert score_headquarters(player, board, state, data) == expected


# ---------------------------------------------------------------------------
# score_unused_resources (req 5.9.4)
# ---------------------------------------------------------------------------

def test_score_unused_resources_floor_division(state):
    """1 PP per 2 unused resources, rounded down."""
    player = state.players[0]
    player.resources = {r: 0 for r in player.resources}
    player.resources[ResourceType.LIVESTOCK] = 5
    assert score_unused_resources(player) == 2


def test_score_unused_resources_zero_when_no_resources(state):
    player = state.players[0]
    player.resources = {r: 0 for r in player.resources}
    assert score_unused_resources(player) == 0


# ---------------------------------------------------------------------------
# winner (req 5.9.4)
# ---------------------------------------------------------------------------

def _make_breakdown(player_id: int, total: int, tokens_placed: int = 0) -> ScoreBreakdown:
    return ScoreBreakdown(
        player_id=player_id, festival=0, villes=0, fromagerie=0, bistro=0,
        orders=0, fruit=0, headquarters=0, unused_resources=0,
        total=total, tokens_placed=tokens_placed,
    )


def test_winner_single_winner():
    scores = [_make_breakdown(0, 30), _make_breakdown(1, 25),
              _make_breakdown(2, 20), _make_breakdown(3, 15)]
    assert winner(scores) == [0]


def test_winner_tiebreaker_by_tokens_placed():
    scores = [_make_breakdown(0, 30, tokens_placed=10),
              _make_breakdown(1, 30, tokens_placed=12),
              _make_breakdown(2, 20, tokens_placed=15),
              _make_breakdown(3, 15, tokens_placed=8)]
    assert winner(scores) == [1]


def test_winner_shared_victory_when_all_tied():
    scores = [_make_breakdown(i, 20, tokens_placed=10) for i in range(4)]
    result = winner(scores)
    assert sorted(result) == [0, 1, 2, 3]


def test_winner_empty_scores():
    assert winner([]) == []
