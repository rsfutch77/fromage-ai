from src.game.board import retrieve_workers, rotate_board, setup_game
from src.game.engine import apply_turn
from src.game.scoring import score_game, winner as find_winner
from src.game.simulation import MAX_TURNS_PER_GAME, run_turn
from src.game.types import ResourceType, RESOURCE_ORDER, VENUE_ORDER, WorkerLocation
from src.ai.random_agent import RandomAgent
from src.game.data_loader import GameDataLoader

data = GameDataLoader()
agents = [RandomAgent(data, seed=i) for i in range(4)]

SEED = 42
state = setup_game(data, SEED)

print(f"Starting game. Turn {state.turn_number}, rotation_index={state.rotation_index}")
for i, p in enumerate(state.players):
    venue = state.venue_facing(i)
    resource = state.resource_facing(i)
    in_hand = sum(1 for w in p.workers if w.location == WorkerLocation.IN_HAND)
    print(
        f"  Player {i} [facing {venue.value}, resource {resource.value}]:"
        f" S={p.resources.get(ResourceType.STRUCTURE,0)}"
        f" L={p.resources.get(ResourceType.LIVESTOCK,0)}"
        f" F={p.resources.get(ResourceType.FRUIT,0)}"
        f" orders_held={len(p.order_cards_held)}"
        f" workers_in_hand={in_hand}"
    )


def _board_line(p) -> str:
    in_hand = sum(1 for w in p.workers if w.location == WorkerLocation.IN_HAND)
    return (
        f"S={p.resources.get(ResourceType.STRUCTURE,0)}"
        f" L={p.resources.get(ResourceType.LIVESTOCK,0)}"
        f" F={p.resources.get(ResourceType.FRUIT,0)}"
        f" orders_held={len(p.order_cards_held)}"
        f" orders_done={len(p.orders_completed)}"
        f" workers_in_hand={in_hand}"
        f" tokens_remaining={p.cheese_tokens_remaining}"
    )


# ---------------------------------------------------------------------------
# Detailed 5-turn loop
# ---------------------------------------------------------------------------
for turn in range(5):
    print(f"\n{'='*60}")
    print(f"=== Turn {turn + 1} (rotation_index={state.rotation_index}) ===")

    # --- 1. Retrieve workers ---
    pre_retrieve = state
    state = retrieve_workers(state)
    any_returned = False
    for i in range(4):
        pre_p = pre_retrieve.players[i]
        post_p = state.players[i]
        for w_post in post_p.workers:
            w_pre = next(w for w in pre_p.workers if w.worker_id == w_post.worker_id)
            if w_pre.location != WorkerLocation.IN_HAND and w_post.location == WorkerLocation.IN_HAND:
                if w_pre.location == WorkerLocation.ON_RESOURCE_TILE:
                    loc_str = f"resource_tile space_id={w_pre.space_id}"
                elif w_pre.location == WorkerLocation.ON_BARN:
                    loc_str = "barn"
                else:
                    venue_str = w_pre.venue.value if w_pre.venue else "?"
                    if w_pre.space_id is not None:
                        loc_str = f"{venue_str} space_id={w_pre.space_id}"
                    else:
                        loc_str = f"{venue_str} (festival space)"
                print(f"  [RETURN] Player {i} worker ({w_pre.cheese_type.value}) returned from {loc_str}")
                any_returned = True
    if not any_returned:
        print("  (no workers returned this rotation)")

    # --- 2. Each player takes their action ---
    for player_id in range(4):
        venue_faced = state.venue_facing(player_id)
        resource_faced = state.resource_facing(player_id)
        pre_p = state.players[player_id]
        pre_res = {r: pre_p.resources.get(r, 0) for r in ResourceType}
        pre_orders = len(pre_p.order_cards_held)
        pre_tokens = len(pre_p.cheese_tokens_on_board)
        pre_deployed_ids = {w.worker_id for w in pre_p.workers if w.location != WorkerLocation.IN_HAND}
        pre_in_hand = sum(1 for w in pre_p.workers if w.location == WorkerLocation.IN_HAND)

        action = agents[player_id].choose_action(state, player_id)
        state = apply_turn(state, player_id, action, data)
        post_p = state.players[player_id]

        print(
            f"\n  Player {player_id} [facing {venue_faced.value}, resource={resource_faced.value}]"
            f"  workers_in_hand={pre_in_hand}"
        )

        # Newly deployed workers
        new_workers = [
            w for w in post_p.workers
            if w.location != WorkerLocation.IN_HAND and w.worker_id not in pre_deployed_ids
        ]
        # New cheese tokens placed (1:1 with ON_CHEESE_SPACE workers by placement order)
        new_tokens = post_p.cheese_tokens_on_board[pre_tokens:]
        cheese_workers = [w for w in new_workers if w.location == WorkerLocation.ON_CHEESE_SPACE]

        for w in new_workers:
            if w.location == WorkerLocation.ON_RESOURCE_TILE:
                amount = w.space_id  # resource_space encodes the amount
                print(
                    f"    [GATHER] worker ({w.cheese_type.value}) placed on resource tile"
                    f" (space={w.space_id}), gained {amount}x {resource_faced.value},"
                    f" returns rot {w.return_after_rotation}"
                )
            elif w.location == WorkerLocation.ON_BARN:
                print(
                    f"    [BARN]   worker ({w.cheese_type.value}) placed on barn,"
                    f" returns rot {w.return_after_rotation}"
                )
            elif w.location == WorkerLocation.ON_CHEESE_SPACE:
                venue_str = w.venue.value if w.venue is not None else "?"
                # Festival workers have no space_id; look up row/col from matching token
                idx = cheese_workers.index(w)
                pc = new_tokens[idx] if idx < len(new_tokens) else None
                if pc is not None and pc.row is not None:
                    loc_str = f"row={pc.row},col={pc.col}"
                elif w.space_id is not None:
                    loc_str = f"space_id={w.space_id}"
                else:
                    loc_str = "?"
                print(
                    f"    [WORKER] ({w.cheese_type.value}) deployed @ {venue_str} {loc_str},"
                    f" returns rot {w.return_after_rotation}"
                )

        for pc in new_tokens:
            loc = f"row={pc.row},col={pc.col}" if pc.row is not None else f"space_id={pc.space_id}"
            print(f"    [CHEESE] {pc.cheese_type.value} {pc.age.value} placed @ {pc.venue.value} {loc}")

        # Resource changes
        for r in ResourceType:
            pre_v = pre_res[r]
            post_v = post_p.resources.get(r, 0)
            if post_v != pre_v:
                sign = "+" if post_v > pre_v else ""
                print(f"    [RES]   {r.value}: {pre_v} -> {post_v} ({sign}{post_v - pre_v})")
        post_orders = len(post_p.order_cards_held)
        if post_orders != pre_orders:
            delta = post_orders - pre_orders
            sign = "+" if delta > 0 else ""
            print(f"    [RES]   ORDERS: {pre_orders} → {post_orders} ({sign}{delta})")

        # Full board state after this player's action
        print(f"    [BOARD] {_board_line(post_p)}")

    # --- 3. Rotate board ---
    state = rotate_board(state)
    state.turn_number += 1
    if state.game_end_triggered:
        state.game_over = True

    # --- 4. End-of-turn summary ---
    prev_rotation = (state.rotation_index - 1) % 4
    print(f"\n--- After turn {turn + 1} (rotation {state.rotation_index}) ---")
    for i, p in enumerate(state.players):
        faced_venue = VENUE_ORDER[(i + prev_rotation) % 4]
        faced_res = RESOURCE_ORDER[(i + state.resource_tile_orientation - prev_rotation) % 4]
        deployed = [w for w in p.workers if w.location != WorkerLocation.IN_HAND]
        in_hand = len(p.workers) - len(deployed)
        print(
            f"  Player {i} [faced {faced_venue.value}, resource {faced_res.value}]:"
            f" resources={dict(p.resources)},"
            f" tokens_on_board={15 - p.cheese_tokens_remaining},"
            f" orders_done={len(p.orders_completed)},"
            f" workers_in_hand={in_hand}"
        )
        worker_at = {(w.venue, w.space_id): w for w in deployed if w.venue is not None}
        accounted: set = set()
        for pc in p.cheese_tokens_on_board:
            loc = f"row={pc.row},col={pc.col}" if pc.row is not None else f"space_id={pc.space_id}"
            w = worker_at.get((pc.venue, pc.space_id))
            worker_note = f"  [worker returns rot {w.return_after_rotation}]" if w else ""
            if w:
                accounted.add((w.venue, w.space_id))
            print(f"    -> {pc.venue.value} | {pc.cheese_type.value} {pc.age.value} | {loc}{worker_note}")
        for w in deployed:
            if (w.venue, w.space_id) not in accounted:
                if w.location == WorkerLocation.ON_RESOURCE_TILE:
                    loc_str = f"space_id={w.space_id}" if w.space_id is not None else "?"
                    print(f"    [gather] {w.cheese_type.value} @ resource_tile {loc_str}, returns rot {w.return_after_rotation}")
                elif w.location == WorkerLocation.ON_BARN:
                    print(f"    [barn]   {w.cheese_type.value}, returns rot {w.return_after_rotation}")
    print(f"  game_end_triggered={state.game_end_triggered}, game_over={state.game_over}")

# ---------------------------------------------------------------------------
# Run remaining turns to end
# ---------------------------------------------------------------------------
print("\nRunning to end...")
while not state.game_over:
    state = run_turn(state, agents, data)
    if state.turn_number >= MAX_TURNS_PER_GAME:
        state.game_over = True
        break

scores = score_game(state, data)
winner_ids = find_winner(scores)
print(f"Total turns: {state.turn_number}")
for sb in scores:
    print(
        f"  Player {sb.player_id}: {sb.total} pts"
        f" (festival={sb.festival}, villes={sb.villes}, frm={sb.fromagerie},"
        f" bistro={sb.bistro}, orders={sb.orders}, fruit={sb.fruit},"
        f" hq={sb.headquarters}, unused={sb.unused_resources})"
    )
print(f"Winner(s): {winner_ids}")
