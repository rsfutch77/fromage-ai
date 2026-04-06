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
"""
