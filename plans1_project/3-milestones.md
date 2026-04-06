# Milestones

---

## Milestone 1: Game Data Models & Board State
- **Focus**: Establish all enums, constants, CSV data loading, and game state dataclasses; implement board rotation, worker retrieval, and game setup.

### Plan Review
- [x] Verify that the feature plan fully describes the intended feature, ensuring all details are present and unambiguous.
  - Requirements sections 1.1, 1.2, 2.1–2.5 are fully specified with field names, types, and behaviours. No ambiguity found.
- [x] Confirm that all aspects of the feature plan are adequately addressed and covered by the defined requirements.
  - All enums, dataclasses, data-loader properties, board helpers, and tests are explicitly listed in 2-requirements.md.
- [x] Ensure that all requirements pertinent to the feature are properly organized and allocated to the correct milestones.
  - Sections 1.1–2.5 form a clean foundational layer. Sections 3–6 (actions, engine, scoring, simulation) depend on this and are deferred to Milestone 2.
- [x] Check that the files designated as outputs for the milestone are capable of completely containing the features planned for that specific milestone.
  - `types.py` (<150 lines), `data_loader.py` (<400 lines), `state.py` (<200 lines), `board.py` (<150 lines) are all within the 500-line limit.
- [x] Define convenient feature flags.
  - No feature flags needed for pure data/state layer; `FESTIVAL_BONUS_PER_EXTRA` and `ORDER_BONUS_PER_EXTRA` module constants serve as the only configurable values in this milestone.

### Outputs
- `src/game/types.py` — All enums and WorkerLocation
- `src/game/data_loader.py` — GameDataLoader and all dataclasses it returns
- `src/game/state.py` — Worker, PlacedCheese, PlayerState, GameState dataclasses
- `src/game/board.py` — rotate_board, retrieve_workers, setup_game, is_game_over
- `tests/test_data_loader.py` — Data loader tests (req 1.2.16)
- `tests/test_board.py` — Board state tests (req 2.5)

### Coding Tasks
- [x] 1.1.1 Define `CheeseType` enum in `src/game/types.py`
- [x] 1.1.2 Define `AgeType` enum with `turns` property
- [x] 1.1.3 Define `ResourceType` enum
- [x] 1.1.4 Define `VenueType` enum
- [x] 1.1.5 Define `SpaceType` enum
- [x] 3.1.1 Define `FruitRequirement` enum (needed by data_loader)
- [x] Define `WorkerLocation` enum (needed by state)
- [x] 1.2.1 Implement `GameDataLoader` class
- [x] 1.2.2 `fromagerie_spaces` property
- [x] 1.2.3 `fromagerie_shelves` property
- [x] 1.2.4 `bistro_spaces` property
- [x] 1.2.5 `villes_spaces` property
- [x] 1.2.6 `festival_spaces` property
- [x] 1.2.7 `milking_parlours` property
- [x] 1.2.8 `player_board_structures` property
- [x] 1.2.9 `customer_tokens` property
- [x] 1.2.10 `order_cards` property (programmatic)
- [x] 1.2.11 `scoring_fromagerie` property
- [x] 1.2.12 `scoring_festival` property + `FESTIVAL_BONUS_PER_EXTRA`
- [x] 1.2.13 `scoring_bistro` property + `bistro_score_for`
- [x] 1.2.14 `scoring_orders` property + `ORDER_BONUS_PER_EXTRA`
- [x] 1.2.15 Error handling for missing CSV / bad enum values
- [x] 2.1.1 Define `Worker` dataclass
- [x] 2.1.2 `Worker.is_available` method
- [x] 2.2.1 Define `PlayerState` dataclass
- [x] 2.2.2 Define `PlacedCheese` dataclass
- [x] 2.3.1 Define `GameState` dataclass
- [x] 2.3.2 `GameState.venue_facing` method
- [x] 2.3.3 `GameState.resource_facing` method
- [x] 2.3.4 `GameState.to_json` method
- [x] 2.3.5 `GameState.from_json` class method
- [x] 2.4.1 `rotate_board` in `board.py`
- [x] 2.4.2 `retrieve_workers` in `board.py`
- [x] 2.4.3 `setup_game` in `board.py`
- [x] 2.4.4 `is_game_over` in `board.py`
- [x] 1.2.16 Write `tests/test_data_loader.py`
- [x] 2.5.1–2.5.5 Write `tests/test_board.py`

#### Code Review Tasks
- [x] Review if you made any files that are too long, try to keep them below around 500 lines
- [x] Review for duplicated code and try to consolidate and use imports instead
- [x] Review if you made any changes that need to be propagated to requirements, milestones, or plans
- [x] Check to make sure we have explicit imports and minimal coupling

---

## Milestone 2: Actions & Legal Move Generation
- **Focus**: Define all action dataclasses and implement legal move generation for gather, make-cheese, milking parlour, and unlock-structure actions; add `IllegalActionError` for use in section 4.

### Plan Review
- [x] Verify that the feature plan fully describes the intended feature, ensuring all details are present and unambiguous.
  - Section 3.1 specifies all action dataclass fields with types. Section 3.2 specifies preconditions for each legal-move function with clear bullet points. The `MakeCheeseAction` row/col vs space_id split is implicit (Festival uses grid coords, others use space_id); clarified in implementation with Optional fields.
- [x] Confirm that all aspects of the feature plan are adequately addressed and covered by the defined requirements.
  - All 5 action types covered (3.1.2–3.1.6). All 5 legal-move functions covered (3.2.1–3.2.5). Tests in 3.2.6.
- [x] Ensure that all requirements pertinent to the feature are properly organized and allocated to the correct milestones.
  - Sections 4–6 (engine, scoring, simulation) depend on these action types and are deferred to Milestone 3+. `IllegalActionError` is defined here for use by section 4.
- [x] Check that the files designated as outputs for the milestone are capable of completely containing the features planned for that specific milestone.
  - `actions.py` estimated ~350 lines (within 500). `test_actions.py` estimated ~120 lines.
- [x] Define convenient feature flags.
  - `MAX_ACTIONS_PER_TURN = 200` module constant in `actions.py`; caps `all_legal_turn_actions` enumeration to prevent combinatorial explosion.

### Outputs
- `src/game/types.py` — Add `IllegalActionError` exception class
- `src/game/actions.py` — All action dataclasses + legal move generators
- `tests/test_actions.py` — Legal move generation tests (req 3.2.6)

### Coding Tasks
- [x] 3.1.1 `FruitRequirement` enum (already done in Milestone 1)
- [x] Add `IllegalActionError` to `src/game/types.py` (needed by section 4)
- [x] 3.1.2 Define `GatherAction` dataclass in `src/game/actions.py`
- [x] 3.1.3 Define `MakeCheeseAction` dataclass
- [x] 3.1.4 Define `MilkingParlourAction` dataclass
- [x] 3.1.5 Define `UnlockStructureAction` dataclass
- [x] 3.1.6 Define `TurnAction` dataclass + `MAX_ACTIONS_PER_TURN` constant
- [x] 3.2.1 `legal_gather_actions(state, player_id, data) -> list[GatherAction | None]`
- [x] 3.2.2 `legal_make_cheese_actions(state, player_id, data) -> list[MakeCheeseAction | None]`
- [x] 3.2.3 `legal_milking_parlour_actions(state, player_id, data) -> list[list[MilkingParlourAction]]`
- [x] 3.2.4 `legal_unlock_actions(state, player_id) -> list[list[UnlockStructureAction]]`
- [x] 3.2.5 `all_legal_turn_actions(state, player_id, data) -> list[TurnAction]`
- [x] 3.2.6 Write `tests/test_actions.py`

#### Code Review Tasks
- [x] Review if you made any files that are too long, try to keep them below around 500 lines
- [x] Review for duplicated code and try to consolidate and use imports instead
- [x] Review if you made any changes that need to be propagated to requirements, milestones, or plans
- [x] Check to make sure we have explicit imports and minimal coupling

---

## Milestone 3: Game Engine, Scoring & Simulation Loop
- **Focus**: Implement action application (section 4), all scoring functions (section 5), the full turn/game loop (section 6), and the RandomAgent (section 7.1) which is required for simulation tests.

### Plan Review
- [x] Verify that the feature plan fully describes the intended feature, ensuring all details are present and unambiguous.
  - Sections 4–6 fully specify preconditions, field mutations, triggered effects, and test cases. Section 7.1 is a short but complete spec. One gap: Fromagerie resource-bonus shelf bonuses (gain_1_resource_any, trade_resource_for_any, gain_2_diff_resources) require player choices not encoded in MakeCheeseAction. Resolved by using a deterministic fallback in the simulation (noted in engine.py comments); can be expanded in a later milestone when UI input is available.
- [x] Confirm that all aspects of the feature plan are adequately addressed and covered by the defined requirements.
  - All apply_* functions, all score_* functions, run_turn/run_game, GameResult, Agent ABC, and RandomAgent are covered.
- [x] Ensure that all requirements pertinent to the feature are properly organized and allocated to the correct milestones.
  - Section 7.2 (batch runner) and sections 8–13 (stats, training, UI) are left for later milestones. Section 7.1 (RandomAgent) is pulled in early because it is needed by the 6.3 simulation tests.
- [x] Check that the files designated as outputs for the milestone are capable of completely containing the features planned for that specific milestone.
  - engine.py ≈ 280 lines, scoring.py ≈ 220 lines, simulation.py ≈ 90 lines, agent.py ≈ 25 lines, random_agent.py ≈ 30 lines — all within 500-line limit.
- [x] Define convenient feature flags.
  - `MAX_TURNS_PER_GAME = 500` safety cap in simulation.py (mirrors simulation_config.json); Fromagerie resource-bonus shelf bonus uses a deterministic fallback commented in engine.py.

### Outputs
- `src/game/engine.py` — gain_resource, apply_gather, apply_make_cheese, apply_milking_parlour, apply_unlock_structure, apply_turn
- `src/game/scoring.py` — ScoreBreakdown, score_festival, score_villes, score_fromagerie, score_bistro, score_orders, score_fruit, score_headquarters, score_unused_resources, score_game, winner
- `src/game/simulation.py` — GameResult dataclass, run_turn, run_game
- `src/ai/agent.py` — Agent abstract base class
- `src/ai/random_agent.py` — RandomAgent implementation
- `tests/test_engine.py` — engine tests (req 4.7.2)
- `tests/test_scoring.py` — scoring tests (req 5.9.4)
- `tests/test_simulation.py` — simulation tests (req 6.3.1–6.3.3)

### Coding Tasks
- [x] 4.1.1 `gain_resource(state, player_id, resource, amount, data, _ctx) -> GameState`
- [x] 4.2.1 `apply_gather(state, player_id, action, data) -> GameState` — place worker, set return rotation, gain resource
- [x] 4.2.2 Barn trigger inside apply_gather when `action.use_barn=True`
- [x] 4.3.1 `apply_make_cheese(state, player_id, action, data) -> GameState` — validate, deduct Fruit, place worker + token, set return rotation
- [x] 4.3.2 `check_order_completion` called from apply_make_cheese
- [x] 4.3.3 Loading Dock trigger in apply_make_cheese
- [x] 4.3.4 game_end_triggered when last token placed
- [x] 4.4.1 `apply_milking_parlour(state, player_id, action, data) -> GameState`
- [x] 4.4.2 Fruit deduction for fruited/jam milking parlour targets
- [x] 4.5.1 Greenhouse trigger inside gain_resource (once per turn via _ctx)
- [x] 4.6.1 `apply_unlock_structure(state, player_id, action) -> GameState`
- [x] 4.7.1 `apply_turn(state, player_id, action, data) -> GameState`
- [x] 4.7.2 Write `tests/test_engine.py`
- [x] 5.1.1 `score_festival(player_id, all_placed, festival_spaces, scoring_table) -> int`
- [x] 5.2.1 `score_villes(state, data) -> dict[int, int]`
- [x] 5.3.1 `score_fromagerie(player_id, all_placed, shelves, spaces, rubric) -> int`
- [x] 5.4.1 `score_bistro(player_id, all_placed, bistro_spaces, scoring) -> int`
- [x] 5.5.1 `score_orders(completed, rubric) -> int`
- [x] 5.6.1 `score_fruit(player) -> int`
- [x] 5.7.1 `score_headquarters(player, board, state, data) -> int`
- [x] 5.8.1 `score_unused_resources(player) -> int`
- [x] 5.9.1–5.9.3 `score_game`, `ScoreBreakdown`, `winner`
- [x] 5.9.4 Write `tests/test_scoring.py`
- [x] 6.1.1 `run_turn(state, agents, data) -> GameState`
- [x] 6.1.2 `run_game(agents, data, seed) -> GameResult`
- [x] 6.1.3 `Agent` ABC in `src/ai/agent.py`
- [x] 6.1.4 `GameResult` dataclass in `src/game/simulation.py`
- [x] 6.2.1 `config/simulation_config.json` (already exists — verify contents match spec)
- [x] 6.3.1–6.3.3 Write `tests/test_simulation.py`
- [x] 7.1.1 `RandomAgent` in `src/ai/random_agent.py`

#### Code Review Tasks
- [x] Review if you made any files that are too long, try to keep them below around 500 lines
  - `engine.py` ~546 lines, `actions.py` ~572 lines — both slightly over due to complex game logic and bug-fix helpers; acceptable given "where possible" caveat. All other files well within limit.
- [x] Review for duplicated code and try to consolidate and use imports instead
  - `_get_board_struct` helper in engine.py centralises the board-structure lookup used in multiple apply_* functions. No other significant duplication found.
- [x] Review if you made any changes that need to be propagated to requirements, milestones, or plans
  - `MilkingParlourAction` gained a `target_venue: VenueType | None = None` field (not in original spec) to resolve space_id overlap between venues. Noted in plan review above. `StepRunner` class added to `simulation.py` for interactive step-through (user-requested mid-milestone); noted in Outputs list update below.
  - Updated Outputs: `simulation.py` also exports `StepRunner` class.
- [x] Check to make sure we have explicit imports and minimal coupling
  - All imports explicit; no wildcard imports. `TYPE_CHECKING` guards used in scoring.py and engine.py to avoid circular imports. `ai/` imports from `game/` only (correct dependency direction).

---

## Milestone 4: Board Visualizer
- **Focus**: Implement a tkinter-based live board display that renders all four venue quadrants, rotates player labels with the board, and can be driven step-by-step via `StepRunner` for debugging simulations without reading raw logs.

### Plan Review
- [x] Verify that the feature plan fully describes the intended feature, ensuring all details are present and unambiguous.
  - Layout, colours, rotation logic, and StepRunner integration are all specified in the milestone. `BoardDisplay` constructor and public API are unambiguous.
- [x] Confirm that all aspects of the feature plan are adequately addressed and covered by the defined requirements.
  - All four venues rendered; player labels rotate; sidebar shows resources/tokens/workers/orders; `update()` and `close()` implemented.
- [x] Ensure that all requirements pertinent to the feature are properly organized and allocated to the correct milestones.
  - No Phase 5 matplotlib work pulled in; milestone is self-contained.
- [x] Check that the files designated as outputs for the milestone are capable of completely containing the features planned for that specific milestone.
  - `board_display.py` ~240 lines — well within 500-line limit.
- [x] Define convenient feature flags.
  - `_CELL = 28` and `_PAD = 4` module constants control cell size; colour dicts can be adjusted without touching logic.

### Outputs
- `src/ui/__init__.py` — empty package marker
- `src/ui/board_display.py` — `BoardDisplay` class (tkinter Canvas-based)

### Coding Tasks
- [x] Create `src/ui/__init__.py`
- [x] Define `BoardDisplay` class in `src/ui/board_display.py`
  - Constructor: `__init__(self, data: GameDataLoader)` — creates the tkinter root window, draws the 4-quadrant layout (Fromagerie, Bistro, Villes, Festival), and a sidebar
  - Each quadrant has a `Player N` label above it; label text is recomputed from `state.rotation_index` and `state.resource_tile_orientation` on each update
  - Cheese spaces drawn as small squares on a Canvas; filled with a type colour (Soft = white, Hard = yellow, Bleu = blue) when occupied, grey outline when empty
  - Sidebar shows each player's resource counts and `cheese_tokens_remaining`
  - `update(state: GameState) -> None` — redraws all quadrant contents and labels; calls `root.update()` so the window stays responsive
  - `close() -> None` — destroys the tkinter root
- [x] Update `src/game/simulation.py` `StepRunner` to accept an optional `display: BoardDisplay | None = None`; if provided, call `display.update(state)` after each step

#### Code Review Tasks
- [x] Review if you made any files that are too long, try to keep them below around 500 lines
  - `board_display.py` ~240 lines. `simulation.py` unchanged in size.
- [x] Review for duplicated code and try to consolidate and use imports instead
  - `_draw_space` helper centralises all rectangle + player-dot drawing; `_redraw_*` methods share it.
- [x] Review if you made any changes that need to be propagated to requirements, milestones, or plans
  - No requirements changes needed; milestone outputs and tasks are fully reflected above.
- [x] Check to make sure we have explicit imports and minimal coupling
  - `board_display.py` imports from `src.game.types` only at call time (inside `_update_quad_labels`); `simulation.py` imports `BoardDisplay` under `TYPE_CHECKING` only — no runtime circular dependency.

---

## Milestone 5: Batch Runner, Results Storage & Baseline Statistics
- **Focus**: Implement Phase 2 — batch game runner, SQLite results storage, baseline statistics, and a minimal `analyze.py` entry point that prints summary stats without plots (plots deferred to Phase 5).

### Plan Review
- [ ] Verify that the feature plan fully describes the intended feature, ensuring all details are present and unambiguous.
- [ ] Confirm that all aspects of the feature plan are adequately addressed and covered by the defined requirements.
- [ ] Ensure that all requirements pertinent to the feature are properly organized and allocated to the correct milestones.
- [ ] Check that the files designated as outputs for the milestone are capable of completely containing the features planned for that specific milestone.
- [ ] Define convenient feature flags.

### Outputs
- `src/analysis/runner.py` — `run_batch` function (req 7.2)
- `src/analysis/results_db.py` — `ResultsDB` class (req 8.1)
- `src/analysis/stats.py` — `BaselineStats` class (req 8.2)
- `src/analyze.py` — minimal entry point: runs batch + prints summary table (partial req 13.3; plots deferred to Phase 5)
- `tests/test_runner.py` — batch runner tests (req 7.2.3)
- `tests/test_stats.py` — stats tests (req 8.2.3)

### Coding Tasks
- [ ] 7.1.1 `RandomAgent` (already implemented in Milestone 3 — verify and check off)
- [ ] 7.2.1 `run_batch(n_games, agents, data, base_seed) -> list[GameResult]` in `src/analysis/runner.py`
- [ ] 7.2.2 Log progress every 100 games at INFO level
- [ ] 7.2.3 Write `tests/test_runner.py`
- [ ] 8.1.1-8.1.5 `ResultsDB` class in `src/analysis/results_db.py` (schema + store + fetch)
- [ ] 8.2.1 `BaselineStats` class in `src/analysis/stats.py`
- [ ] 8.2.2 `BaselineStats.summary_table() -> str` (rich Table)
- [ ] 8.2.3 Write `tests/test_stats.py`
- [ ] Minimal `src/analyze.py`: CLI args `--games`, `--db`, `--seed`; runs batch of RandomAgents, stores in DB, prints summary table

#### Code Review Tasks
- [ ] Review if you made any files that are too long, try to keep them below around 500 lines
- [ ] Review for duplicated code and try to consolidate and use imports instead
- [ ] Review if you made any changes that need to be propagated to requirements, milestones, or plans
- [ ] Check to make sure we have explicit imports and minimal coupling

---

## Stretch Goal: Fromagerie Swap Resource (trade_resource_for_any)

Shelf 1 (Bronze resource-bonus) grants the player a swap: give up one resource,
receive any other. This requires a two-part player choice that is not captured
in the current `MakeCheeseAction` dataclass and is currently a no-op in the
engine (`engine.py: _apply_fromagerie_shelf_bonus`).

### Required changes (in order)

- [ ] Add `resource_to_give: ResourceType | None` and
      `resource_to_receive: ResourceType | None` optional fields to
      `MakeCheeseAction` in `src/game/actions.py`.
- [ ] In `legal_make_cheese_actions`, when the target space resolves to shelf 1,
      emit one action variant per valid (give, receive) pair (give ≠ receive,
      player must hold at least 1 of the given resource).
- [ ] Implement the swap in `engine.py: _apply_fromagerie_shelf_bonus`:
      deduct 1 of `resource_to_give`, gain 1 of `resource_to_receive`.
- [ ] Add one-hot features for `resource_to_give` and `resource_to_receive` to
      the action encoder (Q(s,a) must distinguish swap variants).
- [ ] Update `tests/test_engine.py` and `tests/test_actions.py` to cover the
      swap mechanic.

Note: The state vector already includes self resource counts (fruit, livestock,
structure), so no new state features are needed — only action encoding changes.
