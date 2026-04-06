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

Suggested full vector layout (~129 features):
  Global (7):     rotation one-hot(4), turn/60, game_end, deck_size/36
  Venue look (16): offsets 0–3 × one-hot(4)
  Resource look (12): offsets 0–2 × one-hot(4)
  Workers (12):   3 types × turns-until-available one-hot(4)
  Self resources (4): fruit, livestock, structure, order_count
  Self status (21): tokens_remaining, structures×4, parlours×4,
                    order_cards 3×3 grid, orders_completed, fruit_spent×2
  Opponents (3×16=48): per opp — tokens, venue, resources×4,
                        workers_now×3, workers_next_turn×3, orders_completed
  Board (9):      own/opp cheese per venue×4, villes regions held
"""
