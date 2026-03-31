"""End-game scoring for all venues and bonus categories.

Functions: score_festival, score_villes, score_fromagerie, score_bistro,
score_orders, score_fruit, score_headquarters, score_unused_resources,
score_game, winner.

Defines ScoreBreakdown dataclass.

See requirements section 5.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.game.data_loader import (
    FESTIVAL_BONUS_PER_EXTRA,
    ORDER_BONUS_PER_EXTRA,
    BistroScoringRow,
)
from src.game.types import AgeType, ResourceType, SpaceType, VenueType

if TYPE_CHECKING:
    from src.game.data_loader import (
        BistroSpace,
        CustomerToken,
        FestivalSpace,
        FromagerieShelf,
        FromagerieSpace,
        GameDataLoader,
        PlayerBoardStructure,
    )
    from src.game.state import GameState, PlacedCheese, PlayerState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ScoreBreakdown
# ---------------------------------------------------------------------------

@dataclass
class ScoreBreakdown:
    """Per-player end-game score breakdown."""
    player_id: int
    festival: int
    villes: int
    fromagerie: int
    bistro: int
    orders: int
    fruit: int
    headquarters: int
    unused_resources: int
    total: int
    tokens_placed: int = 0  # 15 - cheese_tokens_remaining; used for tiebreaking


# ---------------------------------------------------------------------------
# Individual scoring functions
# ---------------------------------------------------------------------------

def score_festival(
    player_id: int,
    all_placed_cheese: list[PlacedCheese],
    festival_spaces: list[FestivalSpace],
    scoring_table: dict[int, int],
) -> int:
    """Score the Festival venue for *player_id*.

    Connected groups of orthogonally-adjacent occupied positions that contain
    at least one of the player's tokens are scored via *scoring_table*.
    FREE_SAMPLE spaces always participate in adjacency but count toward a
    player's group only if the group also contains one of their tokens.
    """
    # Positions where this player placed tokens
    player_positions: set[tuple[int, int]] = {
        (pc.row, pc.col)
        for pc in all_placed_cheese
        if pc.venue == VenueType.FESTIVAL and pc.player_id == player_id
    }

    # Free-sample positions (always participate in adjacency)
    free_sample_positions: set[tuple[int, int]] = {
        (sp.row, sp.col)
        for sp in festival_spaces
        if sp.space_type == SpaceType.FREE_SAMPLE
    }

    # All occupied positions (any player's token + free samples)
    all_occupied: set[tuple[int, int]] = free_sample_positions | {
        (pc.row, pc.col)
        for pc in all_placed_cheese
        if pc.venue == VenueType.FESTIVAL
    }

    if not all_occupied:
        return 0

    # BFS to find connected components
    visited: set[tuple[int, int]] = set()
    total = 0

    for start in all_occupied:
        if start in visited:
            continue
        # BFS
        group: set[tuple[int, int]] = set()
        queue = [start]
        while queue:
            pos = queue.pop()
            if pos in visited or pos not in all_occupied:
                continue
            visited.add(pos)
            group.add(pos)
            r, c = pos
            for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if (nr, nc) not in visited and (nr, nc) in all_occupied:
                    queue.append((nr, nc))

        # Only score this group if the player has at least one token in it
        if not (group & player_positions):
            continue

        size = len(group)
        points = scoring_table[min(size, 7)]
        if size > 7:
            points += FESTIVAL_BONUS_PER_EXTRA * (size - 7)
        total += points

    return total


def score_villes(
    state: GameState,
    data: GameDataLoader,
) -> dict[int, int]:
    """Score the Villes venue and update villes_customer_token_holders on *state*.

    Returns player_id → points earned from Villes customer tokens.
    Mutates state.villes_customer_token_holders in place (end-of-game only).
    """
    villes_spaces = data.villes_spaces
    customer_tokens = data.customer_tokens

    # Build influence map: {player_id: {region_name: count}}
    influence: dict[int, dict[str, int]] = {p.player_id: defaultdict(int) for p in state.players}
    for player in state.players:
        for pc in player.cheese_tokens_on_board:
            if pc.venue != VenueType.VILLES:
                continue
            for sp in villes_spaces:
                if sp.space_id == pc.space_id:
                    for region in sp.regions:
                        influence[player.player_id][region] += 1
                    break

    # Award points per region
    points: dict[int, int] = defaultdict(int)
    for token in customer_tokens:
        region = token.region_name
        player_influences = {pid: influence[pid][region] for pid in influence}
        max_inf = max(player_influences.values())
        if max_inf == 0:
            state.villes_customer_token_holders[region] = None
            continue
        leaders = [pid for pid, inf in player_influences.items() if inf == max_inf]
        if len(leaders) == 1:
            winner_id = leaders[0]
            points[winner_id] += token.win_value
            state.villes_customer_token_holders[region] = winner_id
        else:
            for pid in leaders:
                points[pid] += token.tie_value
            state.villes_customer_token_holders[region] = None  # tied

    return dict(points)


def score_fromagerie(
    player_id: int,
    all_placed_cheese: list[PlacedCheese],
    shelves: list[FromagerieShelf],
    spaces: list[FromagerieSpace],
    rubric: dict[int, int],
) -> int:
    """Score the Fromagerie venue for *player_id*.

    Base points from the number of distinct shelves occupied (via *rubric*),
    plus per-token points for tokens on point_bonus shelves.
    """
    player_tokens = [
        pc for pc in all_placed_cheese
        if pc.venue == VenueType.FROMAGERIE and pc.player_id == player_id
    ]
    if not player_tokens:
        return rubric.get(0, 0)

    # Map space_id → shelf_id for quick lookup
    space_to_shelf: dict[int, int] = {sp.space_id: sp.shelf_id for sp in spaces}
    shelf_map: dict[int, FromagerieShelf] = {sh.shelf_id: sh for sh in shelves}

    occupied_shelf_ids: set[int] = set()
    point_bonus_total = 0

    for pc in player_tokens:
        shelf_id = space_to_shelf.get(pc.space_id)
        if shelf_id is None:
            continue
        occupied_shelf_ids.add(shelf_id)
        shelf = shelf_map.get(shelf_id)
        if shelf and shelf.column == "point_bonus":
            point_bonus_total += shelf.points_per_token

    base = rubric.get(len(occupied_shelf_ids), 0)
    return base + point_bonus_total


def score_bistro(
    player_id: int,
    all_placed_cheese: list[PlacedCheese],
    bistro_spaces: list[BistroSpace],
    scoring: list[BistroScoringRow],
) -> int:
    """Score the Bistro venue for *player_id*.

    Pairings = tables where the player has exactly 2 tokens.
    Score = per-age-tier count × the age column from the scoring row for the pairing count.
    """
    player_tokens = [
        pc for pc in all_placed_cheese
        if pc.venue == VenueType.BISTRO and pc.player_id == player_id
    ]
    if not player_tokens:
        return 0

    def _bistro_score_for(pairings: int) -> BistroScoringRow:
        rows = sorted(scoring, key=lambda r: r.pairings)
        for row in rows:
            if pairings <= row.pairings:
                return row
        return rows[-1]  # clamp to max row (3+)

    # Map space_id → table_id
    space_to_table: dict[int, int] = {sp.space_id: sp.table_id for sp in bistro_spaces}

    # Count tokens per table
    table_counts: dict[int, int] = defaultdict(int)
    age_counts: dict[str, int] = defaultdict(int)

    for pc in player_tokens:
        tid = pc.table_id if pc.table_id is not None else space_to_table.get(pc.space_id)
        if tid is not None:
            table_counts[tid] += 1
        age_counts[pc.age.value] += 1

    pairings = sum(1 for cnt in table_counts.values() if cnt >= 2)
    row = _bistro_score_for(pairings)

    bronze = age_counts.get(AgeType.BRONZE.value, 0)
    silver = age_counts.get(AgeType.SILVER.value, 0)
    gold = age_counts.get(AgeType.GOLD.value, 0)

    return bronze * row.bronze + silver * row.silver + gold * row.gold


def score_orders(completed: list, rubric: dict[int, int]) -> int:
    """Score completed orders.

    Uses *rubric* for counts 1–6; applies ORDER_BONUS_PER_EXTRA beyond 6.
    """
    n = len(completed)
    if n == 0:
        return 0
    if n <= 6:
        return rubric.get(n, 0)
    return rubric.get(6, 0) + ORDER_BONUS_PER_EXTRA * (n - 6)


def score_fruit(player: PlayerState) -> int:
    """Multiplicative Fruit scoring: fruited_spent × jam_spent."""
    return player.fruit_spent_on_fruited * player.fruit_spent_on_jam


def score_headquarters(
    player: PlayerState,
    board: PlayerBoardStructure,
    state: GameState,
    data: GameDataLoader,
) -> int:
    """Score the Headquarters structure (slot 4) for *player*.

    Returns 0 if the Headquarters is not unlocked.
    Board-specific conditions:
      Board 1 — per deployed Structure (count of unlocked slots)
      Board 2 — per Fruit/Jam spent
      Board 3 — per completed Order
      Board 4 — per Livestock spent in Milking Parlours
    """
    if not player.structures_unlocked[3]:
        return 0

    condition = board.headquarters_condition.lower()

    if "structure" in condition:
        return sum(player.structures_unlocked)

    if "fruit" in condition or "jam" in condition:
        return player.fruit_spent_on_fruited + player.fruit_spent_on_jam

    if "order" in condition:
        return len(player.orders_completed)

    if "livestock" in condition or "parlour" in condition:
        total = 0
        for parlour in data.milking_parlours:
            if parlour.board_id == player.board_id:
                idx = parlour.parlour_num - 1
                total += parlour.livestock_cost * player.milking_parlours_used[idx]
        return total

    logger.warning("Unknown headquarters_condition '%s' for board %d — returning 0",
                   board.headquarters_condition, board.board_id)
    return 0


def score_unused_resources(player: PlayerState) -> int:
    """1 PP per 2 unused resources (rounded down)."""
    total = sum(player.resources.values())
    return total // 2


# ---------------------------------------------------------------------------
# Full-game scoring
# ---------------------------------------------------------------------------

def score_game(state: GameState, data: GameDataLoader) -> list[ScoreBreakdown]:
    """Compute end-game scores for all players.

    Returns one ScoreBreakdown per player.
    Also updates state.villes_customer_token_holders in place.
    """
    all_placed = [pc for p in state.players for pc in p.cheese_tokens_on_board]

    # Villes: scored once for all players
    villes_points = score_villes(state, data)

    # Scoring tables / reference data
    fest_table = data.scoring_festival
    frm_rubric = data.scoring_fromagerie
    ord_rubric = data.scoring_orders
    bistro_scoring = data.scoring_bistro

    breakdowns: list[ScoreBreakdown] = []
    for player in state.players:
        pid = player.player_id

        board_struct = next(
            (b for b in data.player_board_structures if b.board_id == player.board_id),
            None,
        )

        fest = score_festival(pid, all_placed, data.festival_spaces, fest_table)
        vil = villes_points.get(pid, 0)
        frm = score_fromagerie(pid, all_placed, data.fromagerie_shelves, data.fromagerie_spaces, frm_rubric)
        bis = score_bistro(pid, all_placed, data.bistro_spaces, bistro_scoring)
        ord_pts = score_orders(player.orders_completed, ord_rubric)
        frt = score_fruit(player)
        hq = score_headquarters(player, board_struct, state, data) if board_struct else 0
        unused = score_unused_resources(player)

        total = fest + vil + frm + bis + ord_pts + frt + hq + unused
        tokens_placed = 15 - player.cheese_tokens_remaining
        breakdowns.append(ScoreBreakdown(
            player_id=pid,
            festival=fest,
            villes=vil,
            fromagerie=frm,
            bistro=bis,
            orders=ord_pts,
            fruit=frt,
            headquarters=hq,
            unused_resources=unused,
            total=total,
            tokens_placed=tokens_placed,
        ))

    return breakdowns


def winner(scores: list[ScoreBreakdown]) -> list[int]:
    """Return the list of player_ids who won.

    Tiebreaker 1: most cheese tokens placed (tokens_placed field).
    Tiebreaker 2: shared victory (return all remaining tied players).
    """
    if not scores:
        return []

    max_total = max(s.total for s in scores)
    leaders = [s for s in scores if s.total == max_total]
    if len(leaders) == 1:
        return [leaders[0].player_id]

    # Tiebreaker 1: most tokens placed
    max_placed = max(s.tokens_placed for s in leaders)
    after_tb = [s for s in leaders if s.tokens_placed == max_placed]
    return [s.player_id for s in after_tb]
