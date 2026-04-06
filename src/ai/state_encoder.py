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
              Caveat: early game both counts are near zero so fruit spends look
              nearly worthless by the delta; the agent may undervalue fruit access
              in early turns. Watch for this during training evaluation.
"""
