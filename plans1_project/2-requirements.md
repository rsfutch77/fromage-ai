## Phase 1: Game Simulation Engine

---

[x] 1. Game Data Models & Configuration Loading
  [x] 1.1 Core Enums & Constants
    [x] 1.1.1 Define `CheeseType` enum in `src/game/types.py` with values: `SOFT`, `HARD`, `BLEU`.
    [x] 1.1.2 Define `AgeType` enum in `src/game/types.py` with values: `BRONZE`, `SILVER`, `GOLD`; add property `turns: int` returning 1/2/3 respectively.
    [x] 1.1.3 Define `ResourceType` enum in `src/game/types.py` with values: `STRUCTURE`, `LIVESTOCK`, `FRUIT`, `ORDER`.
    [x] 1.1.4 Define `VenueType` enum in `src/game/types.py` with values: `FROMAGERIE`, `BISTRO`, `VILLES`, `FESTIVAL`.
    [x] 1.1.5 Define `SpaceType` enum in `src/game/types.py` with values: `CHEESE`, `FREE_SAMPLE`, `EMPTY` (for Festival grid positions).
  [x] 1.2 Data Loader
    [x] 1.2.1 Implement `GameDataLoader` class in `src/game/data_loader.py`; constructor takes `data_dir: Path` defaulting to `Path("data/")`; loads all CSV files on init and exposes typed properties.
    [x] 1.2.2 Implement `GameDataLoader.fromagerie_spaces -> list[FromagerieSpace]`: load `fromagerie_spaces.csv`; each row maps to a `FromagerieSpace` dataclass with fields `space_id: int`, `shelf_id: int`, `cheese_type: CheeseType`, `age: AgeType` (from `direction` column), `fruit_requirement: FruitRequirement` (from `requires_fruit` column: `""` → `NONE`, `"Fruit"` → `FRUIT`, `"Jam"` → `JAM`; see section 3.1 for enum definition).
    [x] 1.2.3 Implement `GameDataLoader.fromagerie_shelves -> list[FromagerieShelf]`: load `fromagerie_shelves.csv`; each row maps to a `FromagerieShelf` dataclass with fields `shelf_id: int`, `column: str` (`resource_bonus` or `point_bonus`), `age: AgeType`, `immediate_bonus: str`, `points_per_token: int`.
    [x] 1.2.4 Implement `GameDataLoader.bistro_spaces -> list[BistroSpace]`: load `bistro_spaces.csv`; each row maps to a `BistroSpace` dataclass with fields `space_id: int`, `table_id: int`, `plate_age: AgeType`, `cheese_type: CheeseType`, `fruit_requirement: FruitRequirement` (same mapping as 1.2.2).
    [x] 1.2.5 Implement `GameDataLoader.villes_spaces -> list[VillesSpace]`: load `villes_spaces.csv`; each row maps to a `VillesSpace` dataclass with fields `space_id: int`, `city: str`, `cheese_type: CheeseType`, `age: AgeType` (from `direction` column), `fruit_requirement: FruitRequirement` (from `fruit` column — added in Milestone 2 when CSV was updated), `regions: list[str]` (non-empty region columns only).
    [x] 1.2.6 Implement `GameDataLoader.festival_spaces -> list[FestivalSpace]`: load `festival_spaces.csv`; each row maps to a `FestivalSpace` dataclass with fields `row: int`, `col: int`, `space_type: SpaceType`, `cheese_type: CheeseType | None`, `age: AgeType | None` (from `direction` column), `fruit_requirement: FruitRequirement`; for `FREE_SAMPLE` and `EMPTY` spaces, `cheese_type` and `age` are `None` and `fruit_requirement` is `NONE`.
    [x] 1.2.7 Implement `GameDataLoader.milking_parlours -> list[MilkingParlour]`: load `milking_parlours.csv`; each row maps to a `MilkingParlour` dataclass with fields `board_id: int`, `parlour_num: int`, `livestock_cost: int`, `bonus_cheese_type: CheeseType | None`, `bonus_cheese_age: AgeType | None`; rows where type/age is `Any` map to `None` (wild parlour — player's choice at time of use).
    [x] 1.2.8 Implement `GameDataLoader.player_board_structures -> list[PlayerBoardStructure]`: load `player_board_structures.csv`; each row maps to a `PlayerBoardStructure` dataclass with fields `board_id: int`, `barn_resource: ResourceType`, `loading_dock_venue: VenueType`, `loading_dock_reward: ResourceType`, `greenhouse_resource: ResourceType`, `headquarters_condition: str`.
    [x] 1.2.9 Implement `GameDataLoader.customer_tokens -> list[CustomerToken]`: load `customer_tokens.csv`; normalise `region_name` to lowercase on load (handles the `pruple`→`purple` correction at source); each row maps to a `CustomerToken` dataclass with fields `region_id: int`, `region_name: str`, `win_value: int`, `tie_value: int`.
    [x] 1.2.10 Implement `GameDataLoader.order_cards -> list[OrderCard]`: generate programmatically (no CSV); produce exactly 4 cards for each combination of `CheeseType × AgeType` = 36 cards total; each `OrderCard` dataclass has fields `cheese_type: CheeseType`, `age: AgeType`.
    [x] 1.2.11 Implement `GameDataLoader.scoring_fromagerie -> dict[int, int]`: load `scoring_fromagerie.csv`; return mapping of `{shelves_occupied: base_points}` for 0–6.
    [x] 1.2.12 Implement `GameDataLoader.scoring_festival -> dict[int, int]`: load `scoring_festival.csv`; return mapping of `{group_size: points}` for sizes 0–7; store the `+5` per-additional rule as a module constant `FESTIVAL_BONUS_PER_EXTRA = 5`.
    [x] 1.2.13 Implement `GameDataLoader.scoring_bistro -> list[BistroScoringRow]`: load `scoring_bistro.csv`; each row maps to a `BistroScoringRow` dataclass with fields `pairings: int | str` (`3+` row stored as `3`), `bronze: int`, `silver: int`, `gold: int`; expose a helper method `bistro_score_for(pairings: int) -> BistroScoringRow` that clamps to the `3+` row for any input ≥ 3.
    [x] 1.2.14 Implement `GameDataLoader.scoring_orders -> dict[int, int]`: load `order_scoring.csv`; return mapping of `{order_count: points}` for 1–6; store the `+4` per-additional rule as a module constant `ORDER_BONUS_PER_EXTRA = 4`.
    [x] 1.2.15 All `GameDataLoader` loading methods must raise `FileNotFoundError` with a clear message if their CSV is missing, and `ValueError` if any row contains an unrecognised enum value.
    [x] 1.2.16 Write `tests/test_data_loader.py`: verify that all 10 loaders return non-empty collections; verify `order_cards` has exactly 36 entries with 4 of each type×age; verify `scoring_bistro.bistro_score_for(5)` returns the `3+` row; verify a `FREE_SAMPLE` festival space has `None` for cheese_type and age.

---

[x] 2. Board State & Rotation
  [x] 2.1 Worker Dataclass
    [x] 2.1.1 Define `Worker` dataclass in `src/game/state.py` with fields `worker_id: int`, `cheese_type: CheeseType` (the type of cheese this worker can make), `location: WorkerLocation` (enum: `IN_HAND`, `ON_RESOURCE_TILE`, `ON_CHEESE_SPACE`, `ON_BARN`), `venue: VenueType | None` (venue the worker is placed at, or `None` if in hand), `space_id: int | None` (space within that venue, or `None`), `return_after_rotation: int | None` (absolute rotation index on which this worker is retrieved; `None` if in hand).
    [x] 2.1.2 Add method `Worker.is_available(current_rotation: int) -> bool`: returns `True` if `location == IN_HAND`; also returns `True` if `return_after_rotation == current_rotation` (worker due for retrieval this turn).
  [x] 2.2 PlayerState Dataclass
    [x] 2.2.1 Define `PlayerState` dataclass in `src/game/state.py` with fields: `player_id: int`, `board_id: int`, `resources: dict[ResourceType, int]` (unbounded; all start at 0 then set per starting-resource rules), `workers: list[Worker]` (3 workers, one per CheeseType), `cheese_tokens_remaining: int` (starts at 15), `cheese_tokens_on_board: list[PlacedCheese]`, `order_cards_held: list[OrderCard]`, `orders_completed: list[OrderCard]`, `structures_unlocked: list[bool]` (4 booleans, one per slot; **any order** — structures may be unlocked in any order, not sequentially), `milking_parlours_used: list[bool]` (4 booleans, one per parlour; reset to all-False at start of each game), `fruit_spent_on_fruited: int`, `fruit_spent_on_jam: int`.
    [x] 2.2.2 Define `PlacedCheese` dataclass with fields `cheese_type: CheeseType`, `age: AgeType`, `venue: VenueType`, `space_id: int` (for Villes and Fromagerie); `row: int | None`, `col: int | None` (for Festival grid); `table_id: int | None` (for Bistro).
  [x] 2.3 GameState Dataclass
    [x] 2.3.1 Define `GameState` dataclass in `src/game/state.py` with fields: `rotation_index: int` (starts at 0; increments by 1 each turn; wraps at 4), `turn_number: int` (starts at 1), `players: list[PlayerState]` (exactly 4), `game_end_triggered: bool`, `game_over: bool`, `order_card_deck: list[OrderCard]` (shuffled 36-card deck, consumed as players draw), `resource_tile_orientation: int` (0–3; determines which ResourceType faces which player this turn; set randomly at setup), `villes_customer_token_holders: dict[str, int | None]` (region_name → player_id or None if unclaimed).
    [x] 2.3.2 Add method `GameState.venue_facing(player_id: int) -> VenueType`: compute which venue is currently facing this player given `rotation_index` and `resource_tile_orientation`.
    [x] 2.3.3 Add method `GameState.resource_facing(player_id: int) -> ResourceType`: compute which resource type is currently facing this player on the Resource Tile.
    [x] 2.3.4 Add method `GameState.to_json() -> str`: serialize full game state to a JSON string (all enums serialised as their string names); must be round-trippable.
    [x] 2.3.5 Add class method `GameState.from_json(data: str) -> GameState`: deserialise a JSON string back into a `GameState`; raise `ValueError` on malformed input.
  [x] 2.4 Board Rotation
    [x] 2.4.1 Implement `rotate_board(state: GameState) -> GameState` in `src/game/board.py`: increment `rotation_index` by 1 (mod 4); return new state (do not mutate in place).
    [x] 2.4.2 Implement `retrieve_workers(state: GameState) -> GameState` in `src/game/board.py`: at the start of each turn, for each player, set any worker whose `return_after_rotation == state.rotation_index` back to `location=IN_HAND`, clearing `venue`, `space_id`, and `return_after_rotation`.
    [x] 2.4.3 Implement `setup_game(data: GameDataLoader, seed: int | None = None) -> GameState` in `src/game/board.py`: shuffle order deck (using `seed` if provided); assign board IDs to players randomly; set `resource_tile_orientation` randomly; distribute starting resources per rulebook (2 of the resource to your left, 1 of the resource opposite you); return a fully initialised `GameState` ready for turn 1.
    [x] 2.4.4 Implement `is_game_over(state: GameState) -> bool` in `src/game/board.py`: returns `True` if `state.game_over`; `game_over` is set to `True` at the end of the turn during which `game_end_triggered` was first set (i.e. all 4 players finish the triggering turn, then the game ends).
  [x] 2.5 Tests
    [x] 2.5.1 Write `tests/test_board.py`: verify `rotate_board` increments `rotation_index` and wraps at 4.
    [x] 2.5.2 Verify `retrieve_workers` correctly returns workers due this rotation and leaves others on board.
    [x] 2.5.3 Verify `setup_game` produces a state with exactly 4 players, 3 workers each, 15 cheese tokens each, and correct starting resources for 2 different seeds.
    [x] 2.5.4 Verify `GameState.to_json` / `from_json` round-trip preserves all fields including nested lists and enum values.
    [x] 2.5.5 Verify `venue_facing` and `resource_facing` return correct values across all 4 rotation steps for a known starting orientation.

---

[x] 3. Actions & Legal Move Generation
  [x] 3.1 Action Types
    [x] 3.1.1 Define `FruitRequirement` enum in `src/game/types.py` with values: `NONE`, `FRUIT`, `JAM`. Used in all venue space dataclasses (supersedes the `requires_fruit: bool` / `is_jam: bool` pattern — see corrections in 1.2.2, 1.2.4, 1.2.6).
    [x] 3.1.2 Define `GatherAction` dataclass in `src/game/actions.py` with fields `resource_space: int` (1, 2, or 3 — the numbered space on the Resource Tile) and `use_barn: bool` (if True, player also places a Worker on the Barn this turn; Barn does not consume the Gather action).
    [x] 3.1.3 Define `MakeCheeseAction` dataclass in `src/game/actions.py` with fields `venue: VenueType`, `space_id: int` (for Fromagerie/Villes/Bistro) or `row: int`, `col: int` (for Festival), `worker_type: CheeseType`.
    [x] 3.1.4 Define `MilkingParlourAction` dataclass in `src/game/actions.py` with fields `parlour_num: int` (1–4), `chosen_cheese_type: CheeseType | None` (only required for wild parlour 4), `chosen_age: AgeType | None` (only required for wild parlour 4), `target_space_id: int | None`, `target_row: int | None`, `target_col: int | None` (space to place the bonus token — must match parlour's type/age).
    [x] 3.1.5 Define `UnlockStructureAction` dataclass in `src/game/actions.py` with field `slot: int` (1–4; the structure slot to unlock; must be the next sequential slot — cannot skip).
    [x] 3.1.6 Define `TurnAction` dataclass in `src/game/actions.py` as the complete turn plan with fields `gather: GatherAction | None` (None = skip gather), `make_cheese: MakeCheeseAction | None` (None = skip), `milking_parlours: list[MilkingParlourAction]` (empty list = use none), `unlock_structures: list[UnlockStructureAction]` (empty = unlock none). A fully skipped turn is a `TurnAction` with all fields None/empty.
  [x] 3.2 Legal Move Generation
    [x] 3.2.1 Implement `legal_gather_actions(state: GameState, player_id: int) -> list[GatherAction | None]` in `src/game/actions.py`: return all legal gather choices for this player this turn; a space is legal if no Worker belonging to this player is currently occupying it; include `None` (skip) always; include Barn use only if the Barn structure is unlocked.
    [x] 3.2.2 Implement `legal_make_cheese_actions(state: GameState, player_id: int) -> list[MakeCheeseAction | None]`: return all legal cheese placements; a space is legal if (a) it is in the venue currently facing the player, (b) no cheese token already occupies it, (c) the player has a matching worker type in hand, (d) the player has `cheese_tokens_remaining > 0`, (e) if `fruit_requirement != NONE`, the player has at least 1 Fruit in resources; include `None` (skip) always.
    [x] 3.2.3 Implement `legal_milking_parlour_actions(state: GameState, player_id: int) -> list[list[MilkingParlourAction]]`: return all legal combinations of milking parlour uses (including the empty combination = use none); a parlour is usable if (a) it has not been used this game (`milking_parlours_used[parlour_num - 1]` is False), (b) the player has enough Livestock, (c) a matching empty target space exists in any currently-accessible venue (bonus cheese is not restricted to the facing venue — interpreted as: any venue, not just the facing one).
    [x] 3.2.4 Implement `legal_unlock_actions(state: GameState, player_id: int) -> list[list[UnlockStructureAction]]`: return all affordable subsets of currently-locked slots; unlocking slot N costs N Structure tokens; **any unlock order is valid** (confirmed from rules — no sequential constraint).
    [x] 3.2.5 Implement `all_legal_turn_actions(state: GameState, player_id: int) -> list[TurnAction]`: enumerate all legal `TurnAction` combinations by taking the cross-product of gather choices, make-cheese choices, parlour combinations, and unlock sequences; filter out combinations where the total resource cost exceeds available resources (accounting for interactions, e.g. gathering resources and then spending them in the same turn); cap enumeration at a configurable `MAX_ACTIONS_PER_TURN` (default 200) to prevent combinatorial explosion.
    [x] 3.2.6 Write `tests/test_actions.py`: verify that `all_legal_turn_actions` for a fresh game state returns a non-empty list; verify a player with no workers in hand and no tokens cannot make cheese; verify a parlour with insufficient livestock is excluded; verify structure unlock is excluded when player has 0 Structure resources.

---

[x] 4. Game Action Application
  [x] 4.1 Resource Gain Helper
    [x] 4.1.1 Implement `gain_resource(state: GameState, player_id: int, resource: ResourceType, amount: int) -> GameState` in `src/game/engine.py`: add `amount` to `player.resources[resource]`; if `resource == ORDER`, draw that many Order Cards from `state.order_card_deck` and append to `player.order_cards_held` (draw as many as available if deck runs low — no error); trigger Greenhouse if unlocked and Greenhouse resource matches (see 4.5).
  [x] 4.2 Apply Gather Action
    [x] 4.2.1 Implement `apply_gather(state: GameState, player_id: int, action: GatherAction) -> GameState`: place the appropriate Worker onto the Resource Tile at `resource_space`; set `worker.return_after_rotation = (state.rotation_index + action.resource_space) % 4` (space 1 = returns after 1 turn, space 2 = 2 turns, space 3 = 3 turns); call `gain_resource` for the type facing this player, with `amount = action.resource_space`.
    [x] 4.2.2 If `action.use_barn` is True and the Barn structure is unlocked: place the Barn Worker (lowest-priority available worker) onto `ON_BARN` location; set `return_after_rotation = (state.rotation_index + 1) % 4`; call `gain_resource` for the board's Barn resource with `amount = 1`.
  [x] 4.3 Apply Make Cheese Action
    [x] 4.3.1 Implement `apply_make_cheese(state: GameState, player_id: int, action: MakeCheeseAction) -> GameState`: validate legality (raise `IllegalActionError` if invalid); deduct 1 Fruit if `fruit_requirement == FRUIT` (increment `player.fruit_spent_on_fruited`) or `fruit_requirement == JAM` (increment `player.fruit_spent_on_jam`); place the matching Worker onto the cheese space; set `worker.return_after_rotation = (state.rotation_index + space.age.turns) % 4`; append a `PlacedCheese` to `player.cheese_tokens_on_board`; decrement `player.cheese_tokens_remaining`.
    [x] 4.3.2 After placing, call `check_order_completion(state, player_id, placed_cheese)`: if the player holds an Order Card matching the placed cheese's type and age, move the first matching card from `order_cards_held` to `orders_completed`.
    [x] 4.3.3 After placing, trigger Loading Dock if that structure is unlocked and the venue matches the board's Loading Dock venue: call `gain_resource` for the Loading Dock reward type with `amount = 1`.
    [x] 4.3.4 If `player.cheese_tokens_remaining == 0` after placement, set `state.game_end_triggered = True`.
  [x] 4.4 Apply Milking Parlour Action
    [x] 4.4.1 Implement `apply_milking_parlour(state: GameState, player_id: int, action: MilkingParlourAction) -> GameState`: validate legality; deduct `livestock_cost` from `player.resources[LIVESTOCK]`; mark `player.milking_parlours_used[action.parlour_num - 1] = True`; place a `PlacedCheese` on the target space (no Worker is placed); decrement `player.cheese_tokens_remaining`; call `check_order_completion`; trigger Loading Dock if applicable; set `game_end_triggered` if tokens exhausted.
    [x] 4.4.2 If the target space has `fruit_requirement != NONE`, deduct 1 Fruit and increment the appropriate fruit counter before placing.
  [x] 4.5 Apply Greenhouse Trigger
    [x] 4.5.1 Implement `apply_greenhouse_trigger(state: GameState, player_id: int, resource: ResourceType, amount: int) -> GameState`: called inside `gain_resource` whenever a resource is gained; if the player's Greenhouse is unlocked and `resource == player_board.greenhouse_resource`, add 1 extra unit of that resource (trigger at most once per turn); track whether Greenhouse has fired this turn via a transient flag on the turn context (not persisted in GameState).
  [x] 4.6 Apply Unlock Structure Action
    [x] 4.6.1 Implement `apply_unlock_structure(state: GameState, player_id: int, action: UnlockStructureAction) -> GameState`: validate that `not player.structures_unlocked[action.slot - 1]` (slot not already unlocked); deduct `action.slot` Structure tokens from resources; set `player.structures_unlocked[action.slot - 1] = True`.
  [x] 4.7 Apply Full Turn
    [x] 4.7.1 Implement `apply_turn(state: GameState, player_id: int, action: TurnAction) -> GameState`: apply unlock actions first (player may want resources from gathering to unlock structures — note: unlock actions are processed after gather in this implementation); apply gather; apply make-cheese; apply each milking parlour action in order; return updated state.
    [x] 4.7.2 Write `tests/test_engine.py`: verify gather correctly sets worker return rotation and adds resources; verify make-cheese deducts Fruit for Fruit/Jam spaces; verify order completion triggers when cheese matches held card; verify game_end_triggered is set when last token placed; verify Greenhouse adds exactly 1 extra resource and does not double-trigger; verify milking parlour marks the slot used and cannot be reused.

---

[x] 5. Scoring Engine
  [x] 5.1 Festival Scoring
    [x] 5.1.1 Implement `score_festival(player_id: int, all_placed_cheese: list[PlacedCheese], festival_spaces: list[FestivalSpace], scoring_table: dict[int, int]) -> int` in `src/game/scoring.py`: collect all Festival spaces that have any player's token (for adjacency) or are `FREE_SAMPLE` (always count for adjacency); build a set of occupied (row, col) coordinates including free-sample positions; find connected groups of orthogonally adjacent occupied positions that contain at least one token belonging to `player_id`; for each such group, look up `scoring_table[min(group_size, 7)]`; add `FESTIVAL_BONUS_PER_EXTRA * max(0, group_size - 7)` for groups larger than 7; sum all group scores.
    [x] 5.1.2 A `FREE_SAMPLE` space always participates in adjacency for all players but does not itself belong to any player's group unless adjacent to that player's token.
  [x] 5.2 Villes Scoring
    [x] 5.2.1 Implement `score_villes(state: GameState, data: GameDataLoader) -> dict[int, int]` (returns player_id → points): for each of the 6 regions, count influence per player (a token at a Villes space contributes 1 influence per region that space touches, regardless of age); determine the player with highest influence; award `win_value`; if tied, award `tie_value` to all tied players; update `state.villes_customer_token_holders` in place.
    [x] 5.2.2 Influence from Bronze spaces counts for 1 region, Silver for 2, Gold for 3 — this is already encoded in the `regions` list length on each `VillesSpace`; simply sum presence per region.
  [x] 5.3 Fromagerie Scoring
    [x] 5.3.1 Implement `score_fromagerie(player_id: int, all_placed: list[PlacedCheese], shelves: list[FromagerieShelf], spaces: list[FromagerieSpace], rubric: dict[int, int]) -> int`: count how many distinct `shelf_id` values appear among the player's Fromagerie tokens; look up `rubric[shelves_occupied]` for base points; for each token on a shelf in the `point_bonus` column, add `shelf.points_per_token`; return total.
    [x] 5.3.2 Immediate Fromagerie shelf bonuses (resource gains) are applied at placement time in `apply_make_cheese` (section 4.3), not at scoring time. Scoring only handles end-game points.
  [x] 5.4 Bistro Scoring
    [x] 5.4.1 Implement `score_bistro(player_id: int, all_placed: list[PlacedCheese], bistro_spaces: list[BistroSpace], scoring: list[BistroScoringRow]) -> int`: count how many tables have exactly 2 tokens belonging to `player_id` (= pairings); look up the scoring row via `bistro_score_for(pairings)`; count all of the player's Bistro tokens by plate age (Bronze count, Silver count, Gold count, regardless of pairing status); return `bronze_count * row.bronze + silver_count * row.silver + gold_count * row.gold`.
  [x] 5.5 Order Scoring
    [x] 5.5.1 Implement `score_orders(completed: list[OrderCard], rubric: dict[int, int]) -> int`: `n = len(completed)`; if `n == 0` return 0; if `n <= 6` return `rubric[n]`; return `rubric[6] + ORDER_BONUS_PER_EXTRA * (n - 6)`.
  [x] 5.6 Fruit Scoring
    [x] 5.6.1 Implement `score_fruit(player: PlayerState) -> int`: return `player.fruit_spent_on_fruited * player.fruit_spent_on_jam` (multiplicative; zero if either is zero).
  [x] 5.7 Headquarters Scoring
    [x] 5.7.1 Implement `score_headquarters(player: PlayerState, board: PlayerBoardStructure, state: GameState) -> int`: if slot 4 (Headquarters) is not unlocked (`not player.structures_unlocked[3]`), return 0; otherwise compute the condition-specific score:
      - Board 1 ("per deployed Structure"): return `sum(player.structures_unlocked)` (count of True slots).
      - Board 2 ("per Fruit/Jam spent"): return `player.fruit_spent_on_fruited + player.fruit_spent_on_jam`.
      - Board 3 ("per completed Order"): return `len(player.orders_completed)`.
      - Board 4 ("per Livestock in Parlour"): return sum of `livestock_cost` for each Milking Parlour the player used this game (`milking_parlours_used[i]` is True).
  [x] 5.8 Unused Resource Scoring
    [x] 5.8.1 Implement `score_unused_resources(player: PlayerState) -> int`: sum all values in `player.resources`; return `total // 2` (1 PP per 2 resources, rounded down).
  [x] 5.9 Full Game Score
    [x] 5.9.1 Implement `score_game(state: GameState, data: GameDataLoader) -> dict[int, int]` (player_id → total PP): for each player, sum Festival + Villes + Fromagerie + Bistro + Orders + Fruit + Headquarters + Unused Resources; return the full breakdown as a `ScoreBreakdown` dataclass with one field per scoring category plus `total`.
    [x] 5.9.2 Define `ScoreBreakdown` dataclass in `src/game/scoring.py` with fields: `player_id: int`, `festival: int`, `villes: int`, `fromagerie: int`, `bistro: int`, `orders: int`, `fruit: int`, `headquarters: int`, `unused_resources: int`, `total: int`.
    [x] 5.9.3 Implement `winner(scores: list[ScoreBreakdown]) -> list[int]`: return list of player_ids who won; tiebreaker 1 = most cheese tokens placed (15 - remaining); tiebreaker 2 = shared victory (return all tied players).
    [x] 5.9.4 Write `tests/test_scoring.py`: verify `score_festival` correctly identifies adjacency groups including free-sample spaces; verify `score_bistro` with 0 pairings returns only Silver/Gold plate points; verify `score_fruit` returns 0 when either factor is 0; verify `score_orders` handles 7+ orders with the +4 bonus; verify `score_game` sums all categories correctly for a known state.

---

[x] 6. Full Game Simulation Loop
  [x] 6.1 Turn Orchestration
    [x] 6.1.1 Implement `run_turn(state: GameState, agents: list[Agent], data: GameDataLoader) -> GameState` in `src/game/simulation.py`: call `retrieve_workers(state)` at turn start; for each player in order (0, 1, 2, 3), call `agent.choose_action(state, player_id)` → `TurnAction`, then call `apply_turn(state, player_id, action)`; after all 4 players act, call `rotate_board(state)`; increment `state.turn_number`; if `state.game_end_triggered` was set during this turn, set `state.game_over = True`.
    [x] 6.1.2 Implement `run_game(agents: list[Agent], data: GameDataLoader, seed: int | None = None) -> GameResult` in `src/game/simulation.py`: call `setup_game(data, seed)`; loop `run_turn` until `state.game_over`; call `score_game`; return a `GameResult` dataclass containing `scores: list[ScoreBreakdown]`, `winner_ids: list[int]`, `total_turns: int`, `final_state: GameState`.
    [x] 6.1.3 Define `Agent` abstract base class in `src/ai/agent.py` with abstract method `choose_action(state: GameState, player_id: int) -> TurnAction`; all agent implementations must subclass this.
    [x] 6.1.4 Define `GameResult` dataclass in `src/game/simulation.py` with fields: `scores: list[ScoreBreakdown]`, `winner_ids: list[int]`, `total_turns: int`, `seed: int | None`, `final_state: GameState`.
  [x] 6.2 Simulation Config
    [x] 6.2.1 Create `config/simulation_config.json` with keys: `max_actions_per_turn` (int, default 200), `max_turns_per_game` (int, default 500 — safety cap to prevent infinite loops), `log_level` (string, default `"INFO"`), `data_dir` (string, default `"data/"`).
    [x] 6.2.2 If a game exceeds `max_turns_per_game`, log a WARNING and return the current scores as-is with `game_over = True`.
  [x] 6.3 Tests
    [x] 6.3.1 Write `tests/test_simulation.py`: run one full game with 4 RandomAgents (see section 7) and verify it completes without error, produces 4 `ScoreBreakdown` entries, and `total_turns >= 1`.
    [x] 6.3.2 Verify that two games run with the same seed produce identical `GameResult` objects.
    [x] 6.3.3 Verify that `game_end_triggered` is set on the turn a player places their last token and `game_over` is True after that turn completes.

---

## Phase 2: Random Baseline & Statistical Analysis

---

[x] 7. Random Agent
  [x] 7.1 Implementation
    [x] 7.1.1 Implement `RandomAgent` class in `src/ai/random_agent.py` subclassing `Agent`; `choose_action` calls `all_legal_turn_actions(state, player_id)` and returns a uniformly random choice using `random.choice`; accepts optional `seed` in constructor for reproducibility.
    [x] 7.1.2 `RandomAgent` must never raise an error even if `all_legal_turn_actions` returns only one option (the skip-everything turn); the skip turn is always legal and must always be in the list.
  [x] 7.2 Batch Runner
    [x] 7.2.1 Implement `run_batch(n_games: int, agents: list[Agent], data: GameDataLoader, base_seed: int | None = None) -> list[GameResult]` in `src/analysis/runner.py`: run `n_games` sequential games; if `base_seed` is provided, use `base_seed + i` as the seed for game `i`; return all results.
    [x] 7.2.2 Log progress via Python `logging` at INFO level every 100 games (e.g. "Completed 100/1000 games").
    [x] 7.2.3 Write `tests/test_runner.py`: verify `run_batch(10, ...)` returns exactly 10 `GameResult` objects; verify all 4 player scores are non-negative integers.

---

[x] 8. Results Storage & Baseline Statistics
  [x] 8.1 SQLite Storage
    [x] 8.1.1 Implement `ResultsDB` class in `src/analysis/results_db.py`; constructor takes `db_path: Path` (default `"data/results.db"`); creates schema on first connect.
    [x] 8.1.2 Schema — `games` table: `game_id INTEGER PRIMARY KEY AUTOINCREMENT`, `seed INTEGER`, `total_turns INTEGER`, `timestamp TEXT`, `agent_config TEXT` (JSON string describing agent types used).
    [x] 8.1.3 Schema — `scores` table: `score_id INTEGER PRIMARY KEY AUTOINCREMENT`, `game_id INTEGER REFERENCES games`, `player_id INTEGER`, `board_id INTEGER`, `festival INTEGER`, `villes INTEGER`, `fromagerie INTEGER`, `bistro INTEGER`, `orders INTEGER`, `fruit INTEGER`, `headquarters INTEGER`, `unused_resources INTEGER`, `total INTEGER`, `is_winner INTEGER` (0 or 1).
    [x] 8.1.4 Implement `ResultsDB.store_result(result: GameResult, agent_config: str)`: insert one row into `games` and 4 rows into `scores` in a single transaction.
    [x] 8.1.5 Implement `ResultsDB.fetch_scores(agent_config: str | None = None) -> list[dict]`: return all rows from `scores` joined with `games`; optionally filter by `agent_config`.
  [x] 8.2 Baseline Statistics
    [x] 8.2.1 Implement `BaselineStats` class in `src/analysis/stats.py`; constructor takes `list[GameResult]`; computes and exposes: `win_rate_by_board: dict[int, float]` (board_id → fraction of games won), `mean_score_by_category: dict[str, float]` (category name → mean points across all games/players), `score_std: float`, `mean_turns: float`, `score_percentiles: dict[int, float]` (10/25/50/75/90th percentiles of total scores).
    [x] 8.2.2 Implement `BaselineStats.summary_table() -> str`: return a rich-formatted table string showing win rates by board and mean points per scoring category; use the `rich` library's `Table`.
    [x] 8.2.3 Write `tests/test_stats.py`: run 50 RandomAgent games, construct `BaselineStats`, verify win rates sum to approximately 1.0 (within 0.05), verify all mean scores are non-negative.

[x] 8.3 Game Analysis Charts
  [x] 8.3.1 Extend `ResultsDB` schema to support chart data: add columns to `scores` table — `structures_unlocked TEXT` (JSON array of 4 bools), `fruit_spent_on_fruited INTEGER`, `fruit_spent_on_jam INTEGER`, `milking_parlours_used INTEGER`; add `placed_cheese` table with `game_id INTEGER REFERENCES games`, `player_id INTEGER`, `age TEXT`, `count INTEGER`; add `villes_control` table with `game_id INTEGER REFERENCES games`, `region INTEGER`, `controlling_player INTEGER` (−1 for tie).
  [x] 8.3.2 Update `ResultsDB.store_result` to populate the new columns and tables; ensure schema migration is safe when opening an existing DB without the new columns (use `ALTER TABLE … ADD COLUMN IF NOT EXISTS`).
  [x] 8.3.3 Implement `src/analysis/plots.py` with one function per chart (Charts 1–14); each function: `plot_<name>(db: ResultsDB, data: GameDataLoader, out_dir: Path) -> None`; reads from DB; saves a PNG to `out_dir`; skips silently if fewer than 10 rows found. See Milestone 6 in milestones for full per-chart spec.
  [x] 8.3.4 Charts: 1 structure frequency (4×4 grouped bar), 2 points per venue (bar), 3 win rate per board (bar), 4 fruit vs jam usage (bar), 5 orders share (histogram), 6 unused resources share (histogram), 7 winner vs loser radar (radar chart), 8 board×venue heatmap (4×4), 9 cheese age by outcome (grouped bar), 10 structure unlock winners vs losers (grouped bar per slot), 11 HQ score by board/outcome (bar), 12 parlour usage vs win rate (bar), 13 Villes region control (bar), 14 fruit balance scatter.
  [x] 8.3.5 Write `output/strategy_summary.md` from `src/analyze.py`: one finding block per chart, schema — `## Finding: <title>`, `source_chart:`, `confidence: high|medium|low`, `key_metric:`, `winner_vs_loser_delta:`, `finding:`, `implication:`.
  [x] 8.3.6 Update `src/analyze.py`: add `--charts` flag (default True); when set, call all 14 chart functions and write `output/strategy_summary.md`; add `--out` (default `output/`) CLI arg.
  [x] 8.3.7 Write `tests/test_plots.py`: run each of the 14 chart functions against a DB populated with 50 synthetic `GameResult` objects; verify the PNG file is created and non-empty.

---

## Phase 3: AI Training via Q-Learning

---

[x] 9. State Encoding
  [x] 9.1 Feature Vector
    [x] 9.1.1 Implement `encode_state(state: GameState, player_id: int, data: GameDataLoader) -> np.ndarray` in `src/ai/state_encoder.py`: produce a fixed-length float32 numpy vector representing the state from `player_id`'s perspective.
    [x] 9.1.2 Own-player features to include: resources (4 values), workers available in hand (3 binary), cheese_tokens_remaining (1 value, normalised 0–1), structures_unlocked (1 value, normalised 0–1), orders_completed count (1), orders_held count (1), fruit_spent_on_fruited (1), fruit_spent_on_jam (1), milking_parlours_used count (1), board_id one-hot (4 binary).
    [x] 9.1.3 Board state features: rotation_index one-hot (4 binary), resource_facing one-hot (4 binary), venue_facing one-hot (4 binary).
    [x] 9.1.4 Venue occupancy features: for each venue, binary vector of occupied spaces (own tokens vs. any token) — Fromagerie 18, Bistro 18, Villes 18, Festival 25 spaces = 79 binary features × 2 (own/any) = 158 features.
    [x] 9.1.5 Opponent summary features (per opponent, 3 opponents): cheese_tokens_remaining (normalised), orders_completed count, total cheese placed count = 3 features × 3 opponents = 9 features.
    [x] 9.1.6 Document the total vector length as a module constant `STATE_VECTOR_SIZE` and add an assertion in `encode_state` that the output length equals `STATE_VECTOR_SIZE`.
    [x] 9.1.7 Write `tests/test_state_encoder.py`: verify `encode_state` returns a vector of length `STATE_VECTOR_SIZE`; verify all values are in range [0, 1] (or known fixed range); verify output is deterministic for the same state.

---

[x] 10. Q-Learning Agent
  [x] 10.1 Q-Function
    [x] 10.1.1 Implement `QAgent` class in `src/ai/q_agent.py` subclassing `Agent`; use a linear Q-function approximator: `Q(s, a) = w · φ(s, a)` where `φ(s, a)` is the concatenation of `encode_state(s)` and a one-hot encoding of the action index; weight vector `w` stored as `np.ndarray` of shape `(STATE_VECTOR_SIZE + MAX_ACTIONS_PER_TURN,)`.
    [x] 10.1.2 Alternatively (configurable via `agent_config.json`): use a table-free approach where Q-values are estimated per legal action by passing state features through a small feedforward network (2 hidden layers, 64 units each, ReLU) using numpy only (no PyTorch/TensorFlow).
    [x] 10.1.3 Implement `QAgent.choose_action(state, player_id) -> TurnAction`: compute Q-values for all legal actions; apply ε-greedy policy — with probability `epsilon` choose a random legal action, otherwise choose the argmax action.
    [x] 10.1.4 Implement `QAgent.update(state, player_id, action, reward, next_state)`: apply the Q-learning update rule: `w ← w + α * (reward + γ * max_a' Q(s', a') - Q(s, a)) * ∇Q(s, a)`; use learning rate `alpha` and discount `gamma` from config.
    [x] 10.1.5 Implement `QAgent.save(path: Path)` and `QAgent.load(path: Path)`: serialise/deserialise the weight vector and hyperparameters as a `.npz` file.
    [x] 10.1.6 Create `config/agent_config.json` with keys: `epsilon_start` (float, default 1.0), `epsilon_end` (float, default 0.05), `epsilon_decay_games` (int, default 5000), `alpha` (float, default 0.001), `gamma` (float, default 0.95), `reward_win` (float, default 1.0), `reward_loss` (float, default 0.0), `reward_per_pp` (float, default 0.0 — set > 0 to reward intermediate scoring progress), `model_save_dir` (string, default `"models/"`).

---

[ ] 11. Training Loop
  [ ] 11.1 Self-Play Training
    [ ] 11.1.1 Implement `train(n_games: int, data: GameDataLoader, config_path: Path) -> QAgent` in `src/ai/training.py`: create 4 `QAgent` instances sharing the same weight vector (cooperative training against self); run `n_games` of self-play; after each game, compute rewards (win/loss + optional PP delta) and call `update` for each player's transitions; decay `epsilon` linearly from `epsilon_start` to `epsilon_end` over `epsilon_decay_games`.
    [ ] 11.1.2 After each game, store transitions as `(state_vector, action_index, reward, next_state_vector)` tuples; apply updates in reverse chronological order within the game (Monte Carlo-style within Q-learning).
    [ ] 11.1.3 Log training metrics every 500 games: mean total score, win rate vs. random agent over 100 evaluation games, current epsilon; use Python `logging`.
    [ ] 11.1.4 Save the model checkpoint every 1000 games to `models/checkpoint_{game_num}.npz`; always save the final model to `models/trained_agent.npz`.
    [ ] 11.1.5 Implement `evaluate(agent: QAgent, n_games: int, data: GameDataLoader) -> dict` in `src/ai/training.py`: run `n_games` with 1 trained `QAgent` vs. 3 `RandomAgents`; return `{win_rate: float, mean_pp: float, mean_pp_delta_vs_random: float}`.
  [ ] 11.2 Training Entry Point
    [ ] 11.2.1 Implement `src/train.py` as a runnable script: parse CLI args `--games` (default 10000), `--config` (default `config/agent_config.json`), `--seed` (optional); call `train()`; print final evaluation summary using `rich`.
    [ ] 11.2.2 Write `tests/test_training.py`: run a minimal training loop of 20 games; verify the agent's Q-weights change from their initial values; verify `evaluate` returns a dict with the expected keys and values in valid ranges.

---

## Phase 4: Move Recommender

---

[ ] 12. Move Recommender CLI
  [ ] 12.1 State Input
    [ ] 12.1.1 Implement `src/recommend.py` as the entry point; accepts `--model` (path to `.npz` model file, default `models/trained_agent.npz`) and `--state` (path to a JSON file containing a serialised `GameState`, or `--interactive` flag for manual input).
    [ ] 12.1.2 Implement `load_state_from_json(path: Path) -> GameState`: deserialise using `GameState.from_json`; validate that `game_over` is False before proceeding.
    [ ] 12.1.3 Implement an interactive state builder `build_state_interactively(data: GameDataLoader) -> GameState`: prompt the user (via `rich.prompt`) for: rotation index, resource tile orientation, each player's board ID and resource counts, which spaces are occupied; return a fully initialised `GameState`. This allows recommender use without saving/loading JSON state files.
  [ ] 12.2 Recommendation Output
    [ ] 12.2.1 Implement `recommend_moves(agent: QAgent, state: GameState, player_id: int, top_n: int = 5) -> list[tuple[TurnAction, float]]`: compute Q-values for all legal actions; return the top `top_n` actions sorted by Q-value descending, as (action, q_value) pairs.
    [ ] 12.2.2 Implement `display_recommendations(recommendations: list[tuple[TurnAction, float]])`: print a formatted `rich` table with columns: Rank, Action Description, Q-Value; each `TurnAction` is rendered as a human-readable string (e.g. "Gather 2 Livestock | Make Cheese: Soft/Silver in Fromagerie shelf 3").
    [ ] 12.2.3 Implement `TurnAction.__str__()` or a standalone `format_action(action: TurnAction, data: GameDataLoader) -> str` that converts a `TurnAction` to the human-readable format used above.
    [ ] 12.2.4 Write `tests/test_recommender.py`: load a freshly-trained or checkpointed model; build a known game state; verify `recommend_moves` returns exactly `top_n` results; verify all returned Q-values are finite floats.

---

## Phase 5: Analysis & Visualization

---

[ ] 13. Learning Performance Charts
  [ ] 13.1 Learning Curve Charts (require Q-training output in `output/training_log.jsonl` and `models/checkpoint_*.npz`)
    [ ] 13.1.1 Implement `plot_epsilon_decay(log_path: Path, config: dict, out_path: Path)` in `src/analysis/plots.py`: line chart of ε vs. game number; dashed line at `epsilon_end` from config; annotate convergence point; read `game`, `epsilon` fields from training log.
    [ ] 13.1.2 Implement `plot_win_rate_vs_training(log_path: Path, out_path: Path)`: line chart of win rate vs. game number; dashed baseline at 0.25; annotate final win rate; read `game`, `win_rate` fields.
    [ ] 13.1.3 Implement `plot_mean_score_training(log_path: Path, out_path: Path)`: line chart of mean score ± std dev band vs. game number; annotate peak; read `game`, `mean_score`, `std_score` fields.
    [ ] 13.1.4 Implement `plot_q_weight_norms(models_dir: Path, out_path: Path)`: line chart of L2 norm of weight vector per checkpoint; reads all `models/checkpoint_*.npz`; computes `np.linalg.norm(weights["w"])` for each.
  [ ] 13.2 Hyperparameter Signals Export
    [ ] 13.2.1 Write `output/hyperparameter_signals.csv` from `src/train.py` after training completes: schema `signal, value, unit, threshold, status, recommendation`; signals: `epsilon_final`, `epsilon_floor`, `games_to_epsilon_floor`, `win_rate_final`, `win_rate_peak`, `win_rate_plateau_game`, `score_mean_final`, `score_std_final`, `score_std_trend`, `weight_norm_final`, `weight_norm_delta`; `status` ∈ {`OK`, `WARN`, `CRIT`}.
  [ ] 13.3 Tests
    [ ] 13.3.1 Write `tests/test_learning_plots.py`: run each of the 4 learning chart functions on synthetic training log data (write a temp JSONL file); verify PNG files are created and non-empty.
