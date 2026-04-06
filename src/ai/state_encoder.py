"""Encodes a GameState into a fixed-length float32 numpy feature vector.

Used as input to the Q-learning agent's linear function approximator.
Exports STATE_VECTOR_SIZE constant and encode_state() function.

See requirements section 9.

Design notes for implementation
---------------------------------
The vector should be encoded from the perspective of one player (player_id).
Because board rotation is fully deterministic, future venues and resources are
perfectly predictable — encode them directly to enable multi-turn lookahead:

  Self venue lookahead: one-hot(4) for venues at rotation+0, +1, +2, +3.
  Self resource lookahead: one-hot(4) for resources at rotation+0, +1, +2.
  Self workers: for each cheese type (Soft/Hard/Bleu), encode turns-until-
    available as one-hot(4) where 0=in hand now, 1/2/3=returns next/2nd/3rd
    rotation. Paired with the venue lookahead this lets the agent plan which
    worker types to reserve for upcoming turns.

Scoring-driven features (critical for the agent to learn value correctly)
-------------------------------------------------------------------------
These are not derivable from raw positions by a linear approximator — they
must be pre-computed and included explicitly.

Festival (score_festival uses BFS connected components):
  A raw grid of occupied spaces is insufficient — linear function
  approximation cannot learn to count orthogonal connected components from
  individual space flags. Pre-compute and encode:
    - Current festival score for this player (call score_festival directly)
    - Size of each connected group the player participates in (sorted desc,
      e.g. top 3 group sizes) — tells the agent how close groups are to
      the size-7 bonus threshold
    - Count of empty festival spaces orthogonally adjacent to the player's
      existing groups — marginal expansion value per additional placement
  Free-sample spaces always participate in adjacency (already handled by
  score_festival), so their positions should be treated as occupied when
  computing adjacency counts.

Fromagerie (score_fromagerie uses distinct-shelf rubric):
  The rubric gives increasing points for occupying more distinct shelves, so
  the marginal value of a new shelf depends on how many you already have.
  Encode:
    - Count of distinct shelves currently occupied by this player
    - Count of distinct shelves still available (have at least one empty space)
    - Opponents' distinct shelf counts (competition for the same spaces)
  Fromagerie shelf bonus awareness — action encoding vs. state encoding:
    Point-bonus shelves (shelf.column == "point_bonus", gives points_per_token
    at end-game) do NOT naturally encode themselves: the agent can't distinguish
    a high-value space from a regular one unless the information is explicit.
    Resource-bonus shelves (gain_1_resource_any, gain_2_diff_resources, etc.)
    are partially self-encoding because the agent sees the resource gain in the
    next state, but credit assignment is cleaner if flagged explicitly.
    The shelf bonus info belongs primarily in the ACTION encoding (Q(s,a) gets
    features describing the target space's shelf type and bonus magnitude), not
    the state vector. However, the state should include a summary:
    - Count of unoccupied point-bonus fromagerie spaces still available to this
      player (useful for planning future placements)

  Stretch goal — trade_resource_for_any (shelf 1, Bronze resource-bonus):
    This bonus requires a two-part player choice: which resource to give up and
    which to receive. It is currently a no-op in the engine (see engine.py
    _apply_fromagerie_shelf_bonus). To support it properly:
      - Add resource_to_give: ResourceType | None and
        resource_to_receive: ResourceType | None fields to MakeCheeseAction.
      - legal_make_cheese_actions must emit separate action variants for each
        valid (give, receive) pair when the target space lands on shelf 1.
      - The action encoder should include one-hot features for resource_to_give
        and resource_to_receive so Q(s,a) can distinguish swap variants.
      - The state vector already carries self resource counts (fruit, livestock,
        structure), so the agent has the information needed to evaluate trades;
        no additional state features are required for this stretch goal.

Bistro (score_bistro uses pairings = tables with ≥2 player tokens):
  The scoring row depends on total pairings, and per-token points scale by
  age tier, so both pairing count and age mix matter.
  Encode:
    - Current pairings count (tables where player has ≥2 tokens)
    - Tables where player has exactly 1 token (potential pairing candidates)
    - Age distribution of player's bistro tokens (Bronze/Silver/Gold counts)
    - Whether opponents have already paired a table (blocking info)

Villes (score_villes awards per-region customer tokens):
  Points are winner-takes-most per region; a tie gives only the tie_value.
  The agent needs to know whether it's dominating, tied, or trailing each
  region to evaluate the marginal value of adding another villes token.
  Encode per region:
    - Self influence count in the region
    - Max opponent influence count in the region
    - Delta (self − max_opponent): positive = leading, negative = trailing
    - Current winner (self/tied/opponent) as a 3-way one-hot

Suggested full vector layout (~129 base features + scoring-derived features):
  Global (7):        rotation one-hot(4), turn/60, game_end, deck_size/36
  Venue look (16):   offsets 0–3 × one-hot(4)
  Resource look (12): offsets 0–2 × one-hot(4)
  Workers (12):      3 types × turns-until-available one-hot(4)
  Self resources (4): fruit, livestock, structure, order_count
  Self status (21):  tokens_remaining, structures×4, parlours×4,
                     order_cards 3×3 grid, orders_completed, fruit_spent×2
  Opponents (3×16=48): per opp — tokens, venue, resources×4,
                        workers_now×3, workers_next_turn×3, orders_completed
  Board (9):         own/opp cheese per venue×4, villes regions held
  Festival derived:  current score, top-3 group sizes, adjacent empty count
  Fromagerie derived: own shelf count, available shelf count, opp shelf counts×3
  Bistro derived:    pairings, half-tables, age counts×3, opp pairings×3
  Villes derived:    per region × (self_inf, max_opp_inf, delta, status one-hot(3))

Reward shaping design
----------------------
Terminal reward:
  At game end, the agent's reward encodes both the score and the tiebreaker:

    terminal_reward = score_total + tokens_placed / 16

  tokens_placed = 15 − cheese_tokens_remaining, so the fractional bonus is
  in [0, 0.9375) — always less than 1 point. Score differences always dominate;
  token deployment only distinguishes tied scores. The agent therefore learns
  both objectives in the correct priority order: maximise score first, maximise
  cheese placed second.

  Using the raw score (not a win/loss binary) preserves cardinal information —
  a binary signal collapses a 45-point game and a 12-point game into the same
  reward. The /16 tiebreaker makes the tiebreaker rule trainable rather than
  a post-hoc evaluation label; the agent will develop a preference for deploying
  all its tokens even when it cannot improve its score.

  Win/loss labels for evaluation statistics still use scoring.winner(), which
  applies the same tiebreaker logic (most tokens placed, then shared victory).

The training reward function should use intermediate (per-placement) rewards,
not only a terminal reward. The credit assignment problem is severe over a
~15-action horizon per player; early placements become nearly invisible under
terminal-only rewards.

This game is unusually well-suited for shaping: the intermediate events ARE
the score, not proxies for it. The safe approach is potential-based shaping:

  r(s, a, s') = partial_score(s') - partial_score(s)

This is provably policy-invariant (Ng et al. 1999) — it accelerates learning
without changing what the optimal policy is. All scoring functions are already
implemented in scoring.py and can be called after each placement.

Per-venue approach:
  Festival:   BFS score delta after placement. Non-linear (the 6→7 group-size
              jump is especially valuable) — marginal delta captures this well.
  Fromagerie: rubric[new_shelf_count] - rubric[old_shelf_count] on each
              placement that occupies a new shelf. Point-bonus shelf tokens
              should be rewarded immediately at their points_per_token value.
  Bistro:     Full bistro score delta (pairing count × age-weighted row)
              after each placement. Captures both new pairings and age mix.
  Villes:     Reward at terminal only. Region leads flip mid-game, so
              intermediate villes rewards add noise rather than signal.
              Include villes influence deltas in the state features instead.
  Orders:     Reward immediately when an order is completed (order drawn →
              placed → completion check in engine.py already detects this).
  Emergent strategies (no explicit shaping needed):
              Venue focus and order timing should emerge naturally from marginal
              delta rewards without explicit encoding.
              Venue focus: Festival/Fromagerie/Bistro/Villes scoring functions
              all have increasing returns for concentration (superlinear group
              sizes, rubric jumps, pairing rows, region dominance). The agent
              learns that extending an existing group beats scattering to a new
              venue because the marginal delta is higher. The rotation mechanic
              also limits true multi-venue spreading — you can only place at the
              facing venue, so focus is partially enforced by the game structure.
              Order timing: orders complete automatically on a matching placement;
              the agent is really choosing which space to place at. A better shelf
              or group extension will show a higher score delta than the order-
              completing space, and the agent learns the tradeoff through the
              combined reward. No separate "don't rush orders" signal needed.
              Both patterns are medium-horizon (several turns), so they depend on
              a high discount factor (γ ≈ 0.97–0.99) and sufficient training
              volume rather than reward shaping.
  Negative rewards:
              Avoid a direct penalty for "3 workers available simultaneously."
              The opportunity cost is already implicit — a turn with 3 workers
              in hand produces at most 2 workers' worth of reward, which is
              weaker than a turn where the agent had pre-staged workers well.
              A blanket negative also punishes unavoidable situations (game
              start, forced alignment) and fires at the wrong moment (the bad
              decision was the deployment 1–3 rotations earlier).
              Instead, if staggering fails to emerge naturally from training,
              reward the positive signal: turns where the agent uses BOTH a
              gather worker AND a make-cheese worker (efficient 2-worker turns).
              This rewards the behaviour without punishing unavoidable states.
  Structures: Do NOT shape structure unlock rewards directly. Structures are
              multipliers on future actions, not direct score contributors (except
              HQ). Their value is captured transitively: Barn/Loading Dock/
              Greenhouse give resources, and the agent is already rewarded for
              what it does with those resources downstream. Rewarding the unlock
              itself would be double-counting at an unpredictable rate that varies
              by board and turns remaining.
              HQ is the exception — it is a direct end-game scorer and belongs
              in the terminal reward only.
              The state features carry the structural signal: structures_unlocked×4
              lets the Q-function learn that "Barn unlocked" is a valuable state.
              Add to the state vector: Structure token cost to unlock each remaining
              slot (from player_board_structures.structure_costs), so the agent can
              weigh unlock spending against other uses of Structure tokens.
  Fruit:      Multiplicative scoring (fruit_spent_on_fruited × fruit_spent_on_jam)
              means the marginal delta approach works cleanly without special logic:
                spend on fruited → delta = jam_count  (current jam total)
                spend on jam     → delta = fruit_count (current fruited total)
              This naturally rewards balance — the agent earns more for whichever
              type it has less of, incentivizing an even mix automatically.
              Zero-count boundary: if either count is 0 the score is 0, so the
              delta is also 0 — the agent correctly receives NO reward for jam
              placements while it has zero fruited (and vice versa). Do NOT add
              a minimum-value floor or partial credit here; both types must be
              non-zero before any fruit points are earned.
              Caveat: early game both counts are near zero so fruit spends look
              nearly worthless by the delta; the agent may undervalue fruit access
              in early turns. Watch for this during training evaluation.

Current sub-vector layout (implemented)
-----------------------------------------
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
