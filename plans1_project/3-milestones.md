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
- `src/ui/_score_widgets.py` — `ScoreTable` and `VillesTable` widget classes (extracted during code review to keep board_display.py within 500-line limit)

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
  - Original `board_display.py` was 724 lines. Refactored: extracted `ScoreTable` and `VillesTable` into `src/ui/_score_widgets.py` (230 lines); `board_display.py` now 516 lines. `simulation.py` unchanged at 208 lines.
- [x] Review for duplicated code and try to consolidate and use imports instead
  - `_draw_space` helper centralises all rectangle + player-dot drawing; `_redraw_*` methods share it. `_PLAYER_COLOURS` constant intentionally kept in both `board_display.py` and `_score_widgets.py` to avoid a shared-constants module for a single 1-line value.
- [x] Review if you made any changes that need to be propagated to requirements, milestones, or plans
  - Added `src/ui/_score_widgets.py` to Outputs list above.
- [x] Check to make sure we have explicit imports and minimal coupling
  - `_score_widgets.py` imports only `tkinter` at runtime (no game layer). `board_display.py` imports `VENUE_ORDER` at call time inside `_update_quad_labels`; `simulation.py` imports `BoardDisplay` under `TYPE_CHECKING` only — no runtime circular dependency.

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
- [x] 7.1.1 `RandomAgent` (already implemented in Milestone 3 — verify and check off)
- [x] 7.2.1 `run_batch(n_games, agents, data, base_seed) -> list[GameResult]` in `src/analysis/runner.py`
- [x] 7.2.2 Log progress every 100 games at INFO level
- [x] 7.2.3 Write `tests/test_runner.py`
- [x] 8.1.1-8.1.5 `ResultsDB` class in `src/analysis/results_db.py` (schema + store + fetch)
- [x] 8.2.1 `BaselineStats` class in `src/analysis/stats.py`
- [x] 8.2.2 `BaselineStats.summary_table() -> str` (rich Table)
- [x] 8.2.3 Write `tests/test_stats.py`
- [x] Minimal `src/analyze.py`: CLI args `--games`, `--db`, `--seed`; runs batch of RandomAgents, stores in DB, prints summary table

#### Code Review Tasks
- [x] Review if you made any files that are too long, try to keep them below around 500 lines
- [x] Review for duplicated code and try to consolidate and use imports instead
- [x] Review if you made any changes that need to be propagated to requirements, milestones, or plans
- [x] Check to make sure we have explicit imports and minimal coupling

---

## Milestone 6: Game Analysis Charts
- **Focus**: Implement all 14 game-analysis matplotlib charts in `src/analysis/plots.py`, extend `ResultsDB` to store the extra player-state fields the charts need, update `src/analyze.py` to generate charts and write `output/strategy_summary.md`. No Q-learning dependency — all data comes from RandomAgent simulation runs. Learning-performance charts (L1–L4) and `hyperparameter_signals.csv` are deferred to a Phase 5 milestone after Q-training is implemented.

### Plan Review
- [x] Verify that the feature plan fully describes the intended feature, ensuring all details are present and unambiguous.
  - Charts 1–14 are fully specified with chart type, axes, data sources, and rationale. `strategy_summary.md` finding schema is defined. DB extension fields are enumerated. No ambiguity.
- [x] Confirm that all aspects of the feature plan are adequately addressed and covered by the defined requirements.
  - All 14 charts have explicit DB data sources. DB schema extension (req 8.3.1–8.3.2) covers every extra field needed. Learning charts (L1–L4) and `hyperparameter_signals.csv` are explicitly excluded and deferred to Phase 5 (req 13).
- [x] Ensure that all requirements pertinent to the feature are properly organized and allocated to the correct milestones.
  - Game-analysis charts (no Q-learning dependency) are in this milestone, completing Phase 2. Learning charts are in Phase 5.
- [x] Check that the files designated as outputs for the milestone are capable of completely containing the features planned for that specific milestone.
  - `plots.py` ~400 lines (14 chart functions + helpers), `exports.py` ~60 lines, `analyze.py` extension ~60 lines — all within 500-line limit. `test_plots.py` ~150 lines.
- [x] Define convenient feature flags.
  - `MIN_GAMES_FOR_CHART = 10` guard in each chart function (skip + log warning if DB has fewer rows); `OUTPUT_DIR = Path("output/plots")` default constant in `analyze.py`.

### Outputs
- `src/analysis/plots.py` — 14 game-analysis chart functions (Charts 1–14)
- `src/analysis/exports.py` — `write_strategy_summary(db: ResultsDB, out_path: Path)`
- `src/analysis/results_db.py` — extended schema and updated `store_result`
- `src/analyze.py` — updated entry point with `--charts` and `--out` flags
- `tests/test_plots.py` — chart generation tests (req 8.3.7)

### Coding Tasks
- [x] Extend `ResultsDB` schema: add `structures_unlocked TEXT`, `fruit_spent_on_fruited INTEGER`, `fruit_spent_on_jam INTEGER`, `milking_parlours_used INTEGER` to `scores`; add `placed_cheese` table (`game_id`, `player_id`, `age TEXT`, `count INTEGER`); add `villes_control` table (`game_id`, `player_id`, `region INTEGER`, `controlling_player INTEGER`); use try/except around ALTER TABLE for safe migration (SQLite lacks ADD COLUMN IF NOT EXISTS pre-3.37)
- [x] Update `ResultsDB.store_result` to populate new columns and tables from `GameResult`; also fixed longstanding bug where `board_id` was incorrectly stored as `player_id`
- [x] Create `src/analysis/plots.py`; add `MIN_GAMES_FOR_CHART = 10` constant
- [x] Chart 1: `plot_structure_frequency(db, out_dir)`
- [x] Chart 2: `plot_points_per_venue(db, out_dir)`
- [x] Chart 3: `plot_win_rate_by_board(db, out_dir)`
- [x] Chart 4: `plot_fruit_usage(db, out_dir)`
- [x] Chart 5: `plot_orders_share(db, out_dir)`
- [x] Chart 6: `plot_unused_resources_share(db, out_dir)`
- [x] Chart 7: `plot_winner_vs_loser_radar(db, out_dir)`
- [x] Chart 8: `plot_board_venue_heatmap(db, out_dir)`
- [x] Chart 9: `plot_cheese_age_distribution(db, out_dir)`
- [x] Chart 10: `plot_structure_unlock_by_outcome(db, out_dir)`
- [x] Chart 11: `plot_headquarters_by_board(db, out_dir)`
- [x] Chart 12: `plot_parlour_usage_vs_win_rate(db, out_dir)`
- [x] Chart 13: `plot_villes_region_control(db, out_dir)`
- [x] Chart 14: `plot_fruit_balance_scatter(db, out_dir)`
- [x] Create `src/analysis/exports.py`; implement `write_strategy_summary(db: ResultsDB, out_path: Path)`
- [x] Update `src/analyze.py`: add `--charts` flag (default `True`) and `--out` arg (default `output/`); when `--charts`, call all 14 plot functions and call `write_strategy_summary`
- [x] Write `tests/test_plots.py`: populate a temp DB with 50 synthetic results; run each chart function; assert PNG created and `os.path.getsize > 0`

#### Code Review Tasks
- [x] Review if you made any files that are too long, try to keep them below around 500 lines
  - `plots.py` 465 lines, `exports.py` 319 lines, `results_db.py` 279 lines, `analyze.py` 110 lines — all within limit.
- [x] Review for duplicated code and try to consolidate and use imports instead
  - `_check_min` and `_save` helpers centralise the skip-guard and file-write logic shared by all 14 chart functions. `_VENUES`, `_SCORE_CATS`, `_AGES` constants avoid repetition across plots and exports.
- [x] Review if you made any changes that need to be propagated to requirements, milestones, or plans
  - Milestone coding tasks updated above. `store_result` board_id bug fix is internal — no spec change needed. Charts 1 and 10 drop the `data` parameter (not needed — board IDs come from the DB).
- [x] Check to make sure we have explicit imports and minimal coupling
  - All imports explicit. `plots.py` and `exports.py` use `TYPE_CHECKING` for `ResultsDB` to avoid circular imports. `matplotlib.use("Agg")` set at module level to prevent display issues in headless environments.

---

## Milestone 7: State Encoding & Q-Learning Agent
- **Focus**: Implement the fixed-length state encoder (section 9) and the linear Q-function approximator with ε-greedy policy and weight-update rule (section 10). No training loop yet — this milestone delivers the buildable pieces so Milestone 8 can wire them together.

### Plan Review
- [x] Verify that the feature plan fully describes the intended feature, ensuring all details are present and unambiguous.
  - Sections 9.1 and 10.1 fully specify feature-vector layout, Q-function representation choices, ε-greedy policy, update rule, save/load format, and config keys. The alternative feedforward-network path (10.1.2) is configurable but numpy-only; no ambiguity on implementation constraints.
- [x] Confirm that all aspects of the feature plan are adequately addressed and covered by the defined requirements.
  - All encoder sub-vectors (own-player, board, venue occupancy, opponent summary) are enumerated with sizes totalling `STATE_VECTOR_SIZE`. All `QAgent` public methods are specified. `agent_config.json` keys are listed.
- [x] Ensure that all requirements pertinent to the feature are properly organized and allocated to the correct milestones.
  - Training loop (section 11), entry point (`src/train.py`), and `evaluate` function are deferred to Milestone 8 to keep this milestone focused on the data/model layer.
- [x] Check that the files designated as outputs for the milestone are capable of completely containing the features planned for that specific milestone.
  - `state_encoder.py` ≈ 120 lines, `q_agent.py` ≈ 160 lines, `agent_config.json` < 20 lines, `test_state_encoder.py` ≈ 60 lines, `test_q_agent.py` ≈ 80 lines — all within 500-line limit.
- [x] Define convenient feature flags.
  - `STATE_VECTOR_SIZE` module constant in `state_encoder.py` (asserted at runtime). `USE_NETWORK_APPROX` boolean key in `agent_config.json` switches between linear and feedforward Q-function.

### Outputs
- `src/ai/state_encoder.py` — `encode_state` function + `STATE_VECTOR_SIZE` constant
- `src/ai/q_agent.py` — `QAgent` class (linear or feedforward Q-function, ε-greedy, save/load)
- `config/agent_config.json` — hyperparameters and model-path config
- `tests/test_state_encoder.py` — encoder tests (req 9.1.7)
- `tests/test_q_agent.py` — Q-agent unit tests (req 10.1 methods)

### Coding Tasks
- [x] 9.1.1 `encode_state(state, player_id, data) -> np.ndarray` in `src/ai/state_encoder.py`
- [x] 9.1.2 Own-player sub-vector: resources (4), workers in hand (3 binary), cheese_tokens_remaining (1, normalised), structures_unlocked fraction (1), orders_completed count (1), orders_held count (1), fruit_spent_on_fruited (1), fruit_spent_on_jam (1), milking_parlours_used count (1), board_id one-hot (4)
- [x] 9.1.3 Board state sub-vector: rotation_index one-hot (4), resource_facing one-hot (4), venue_facing one-hot (4)
- [x] 9.1.4 Venue occupancy sub-vector: for each venue (Fromagerie 18, Bistro 18, Villes 18, Festival 25 = 79 spaces), binary own-token and any-token flags = 158 features
- [x] 9.1.5 Opponent summary sub-vector: per opponent (3): cheese_tokens_remaining (normalised), orders_completed, total cheese placed = 9 features
- [x] 9.1.6 `STATE_VECTOR_SIZE` constant; assert output length in `encode_state`
- [x] 9.1.7 Write `tests/test_state_encoder.py`: verify length == `STATE_VECTOR_SIZE`; verify all values in [0, 1]; verify determinism
- [x] 10.1.1 `QAgent` class in `src/ai/q_agent.py`: linear approximator `Q(s,a) = w · φ(s,a)`; weight vector shape `(STATE_VECTOR_SIZE + MAX_ACTIONS_PER_TURN,)`
- [x] 10.1.2 Feedforward alternative (2 hidden layers, 64 units, ReLU, numpy only) behind `USE_NETWORK_APPROX` config flag
- [x] 10.1.3 `QAgent.choose_action(state, player_id) -> TurnAction`: compute Q-values for all legal actions; ε-greedy selection
- [x] 10.1.4 `QAgent.update(state, player_id, action, reward, next_state)`: Q-learning update `w ← w + α(r + γ max_a' Q(s',a') − Q(s,a)) ∇Q(s,a)`
- [x] 10.1.5 `QAgent.save(path: Path)` and `QAgent.load(path: Path)`: serialise weights + hyperparameters as `.npz`
- [x] 10.1.6 Create `config/agent_config.json` with keys: `epsilon_start`, `epsilon_end`, `epsilon_decay_games`, `alpha`, `gamma`, `reward_win`, `reward_loss`, `reward_per_pp`, `model_save_dir`, `use_network_approx`
- [x] Write `tests/test_q_agent.py`: verify `choose_action` returns a valid `TurnAction`; verify `update` changes the weight vector; verify save/load round-trip preserves weights; verify ε=1.0 produces random choices

#### Code Review Tasks
- [x] Review if you made any files that are too long, try to keep them below around 500 lines
- [x] Review for duplicated code and try to consolidate and use imports instead
- [x] Review if you made any changes that need to be propagated to requirements, milestones, or plans
- [x] Check to make sure we have explicit imports and minimal coupling

---

## Milestone 8: Training Loop & Train Entry Point
- **Focus**: Implement self-play Q-learning training (section 11) — the `train` and `evaluate` functions in `src/ai/training.py`, checkpoint saving, training-log JSONL output, and the `src/train.py` CLI entry point.

### Plan Review
- [x] Verify that the feature plan fully describes the intended feature, ensuring all details are present and unambiguous.
  - Section 11 specifies shared-weight self-play, Monte Carlo-style reverse-order updates, evaluation cadence (every 500 games), checkpoint cadence (every 1000 games), log schema, and all `train.py` CLI flags. `evaluate` return dict keys are listed. No ambiguity.
- [x] Confirm that all aspects of the feature plan are adequately addressed and covered by the defined requirements.
  - All items in 11.1.1–11.1.5 and 11.2.1–11.2.2 are covered. Learning-performance charts (section 13) remain deferred to Milestone 9.
- [x] Ensure that all requirements pertinent to the feature are properly organized and allocated to the correct milestones.
  - `QAgent` and `encode_state` are prerequisites (Milestone 7). Charts L1–L4 and `hyperparameter_signals.csv` depend on training output and are deferred to Milestone 9 so this milestone ships a working trainer first.
- [x] Check that the files designated as outputs for the milestone are capable of completely containing the features planned for that specific milestone.
  - `training.py` ≈ 200 lines, `train.py` ≈ 80 lines, `test_training.py` ≈ 60 lines — all within 500-line limit.
- [x] Define convenient feature flags.
  - `EVAL_INTERVAL = 500` and `CHECKPOINT_INTERVAL = 1000` module constants in `training.py` (mirrored in `agent_config.json` as `eval_interval` and `checkpoint_interval`); `--learning-plots` CLI flag on `train.py` gated to False until Milestone 9.

### Outputs
- `src/ai/training.py` — `train` and `evaluate` functions
- `src/train.py` — CLI entry point (`--games`, `--config`, `--seed`)
- `models/` — directory created on first run; `trained_agent.npz` + periodic checkpoints written here
- `output/training_log.jsonl` — per-eval-window log written during training
- `tests/test_training.py` — training loop tests (req 11.2.2)

### Coding Tasks
- [x] 11.1.1 `train(n_games, data, config_path) -> QAgent` in `src/ai/training.py`: create 4 `QAgent` instances sharing one weight vector; run `n_games` self-play; after each game compute rewards (win/loss + optional PP delta) and call `update` for each player's transitions; decay ε linearly
- [x] 11.1.2 Store per-game transitions as `(state_vector, action_index, reward, next_state_vector)`; apply updates in reverse chronological order within the game
- [x] 11.1.3 Log training metrics every `EVAL_INTERVAL` games: mean total score, win rate vs. random (100 eval games), current ε; write one JSON line to `output/training_log.jsonl` per log event
- [x] 11.1.4 Save checkpoint every `CHECKPOINT_INTERVAL` games to `models/checkpoint_{game_num}.npz`; save final model to `models/trained_agent.npz`
- [x] 11.1.5 `evaluate(agent, n_games, data) -> dict`: run `n_games` with 1 `QAgent` vs. 3 `RandomAgents`; return `{win_rate, mean_pp, mean_pp_delta_vs_random}`
- [x] 11.2.1 `src/train.py`: CLI args `--games` (default 10000), `--config` (default `config/agent_config.json`), `--seed` (optional); call `train()`; print final evaluation summary via `rich`
- [x] 11.2.2 Write `tests/test_training.py`: run minimal training loop of 20 games; verify Q-weights differ from initial values; verify `evaluate` returns expected keys with values in valid ranges

#### Code Review Tasks
- [x] Review if you made any files that are too long, try to keep them below around 500 lines
- [x] Review for duplicated code and try to consolidate and use imports instead
- [x] Review if you made any changes that need to be propagated to requirements, milestones, or plans
- [x] Check to make sure we have explicit imports and minimal coupling

---

## Milestone 9: Learning Performance Charts
- **Focus**: Implement Charts L1–L4 (epsilon decay, win-rate vs training, mean score, Q-weight norms) and the `hyperparameter_signals.csv` export in `src/analysis/plots.py` and `src/train.py`. Requires completed Q-training output (`output/training_log.jsonl`, `models/checkpoint_*.npz`). Deferred to Phase 5.

### Plan Review
- [ ] Verify that the feature plan fully describes the intended feature, ensuring all details are present and unambiguous.
- [ ] Confirm that all aspects of the feature plan are adequately addressed and covered by the defined requirements.
- [ ] Ensure that all requirements pertinent to the feature are properly organized and allocated to the correct milestones.
- [ ] Check that the files designated as outputs for the milestone are capable of completely containing the features planned for that specific milestone.
- [ ] Define convenient feature flags.

### Learning Performance Charts

These four charts read from the training log produced by `src/ai/training.py`. The training log is a newline-delimited JSON file at `output/training_log.jsonl`, where each line is a dict with the keys below (written once per evaluation window, default every 500 games):

```
{"game": 500, "epsilon": 0.92, "win_rate": 0.28, "mean_score": 31.4, "std_score": 6.1, "pp_delta": 2.1}
```

The charts also optionally read checkpoint files at `models/checkpoint_{game}.npz` to compute Q-weight norms.

#### Chart L1 — Epsilon decay curve

- **What**: Line chart of ε (y-axis, 0–1) vs. game number (x-axis). Draws a dashed horizontal line at `epsilon_end` from `agent_config.json`. Annotates the point where ε first reaches `epsilon_end` (if it has), or marks the current ε if training is still in progress.
- **Data source**: `output/training_log.jsonl` — `game` + `epsilon` fields.
- **Why useful**: The primary readout for "how close are we to stabilising learning." Once ε reaches its floor the agent is in near-pure exploitation; further games return diminishing exploration benefit. The gap between the current point and the floor is the direct answer to "do we need more samples?"

#### Chart L2 — Win rate vs training progress

- **What**: Line chart of win rate against `RandomAgent` (y-axis, 0–1) vs. game number (x-axis). Draws a dashed horizontal line at 0.25 (random-agent baseline for a 4-player game). Annotates the final win rate.
- **Data source**: `output/training_log.jsonl` — `game` + `win_rate` fields.
- **Why useful**: Direct measure of whether the agent is improving. A plateau well above 0.25 indicates convergence; a plateau at or near 0.25 indicates the agent has not learned meaningful strategy and training should be extended or hyperparameters revised.

#### Chart L3 — Mean score over training (with variance band)

- **What**: Line chart of mean total prestige score (y-axis) vs. game number (x-axis), with a shaded ±1 std dev band. Annotates the peak mean score and the game at which it was reached.
- **Data source**: `output/training_log.jsonl` — `game`, `mean_score`, `std_score` fields.
- **Why useful**: Tracks absolute score improvement independent of win rate. A narrowing band as training progresses shows the policy is converging; a persistently wide band after ε stabilises suggests the policy has not settled.

#### Chart L4 — Q-weight magnitude over checkpoints

- **What**: Line chart of the L2 norm of the Q-weight vector (y-axis) vs. checkpoint game number (x-axis). Reads all `models/checkpoint_*.npz` files and computes `np.linalg.norm(weights["w"])` for each.
- **Data source**: `models/checkpoint_{game}.npz` — `w` key (weight vector).
- **Why useful**: If the norm is still growing or shifting significantly between checkpoints, the Q-function has not converged. A flat line indicates the weights have stabilised, meaning additional training is unlikely to change the learned strategy — the clearest signal for an early-stopping decision.

### Outputs
- `src/analysis/plots.py` — 4 learning-performance chart functions (L1–L4)
- `src/analysis/exports.py` — `write_hyperparameter_signals(log_path, models_dir, config_path, out_path)`
- `src/train.py` — add `--learning-plots` flag; generate charts and write `output/hyperparameter_signals.csv`
- `tests/test_learning_plots.py` — learning chart tests (req 13.3.1)

### Coding Tasks
- [x] L1: `plot_epsilon_decay(log_path: Path, config: dict, out_path: Path)` — line chart of ε vs game number; dashed line at `epsilon_end`; annotate convergence point
- [x] L2: `plot_win_rate_vs_training(log_path: Path, out_path: Path)` — line chart of win rate vs game number; dashed baseline at 0.25; annotate final win rate
- [x] L3: `plot_mean_score_training(log_path: Path, out_path: Path)` — line chart of mean score ± std dev band vs game number; annotate peak
- [x] L4: `plot_q_weight_norms(models_dir: Path, out_path: Path)` — line chart of L2 norm per checkpoint; reads all `models/checkpoint_*.npz`; computes `np.linalg.norm(weights["w"])`
- [x] `write_hyperparameter_signals(log_path, models_dir, config_path, out_path)` in `src/analysis/exports.py`: compute 11 signals (req 13.2.1); set `status`/`recommendation` per thresholds; write CSV
- [x] Add `--learning-plots` flag to `src/train.py`; when set, call L1–L4 and `write_hyperparameter_signals`
- [x] Write `tests/test_learning_plots.py`: write a synthetic training log JSONL + dummy checkpoint files; run all 4 chart functions; assert PNGs created and non-empty

#### Code Review Tasks
- [x] Review if you made any files that are too long, try to keep them below around 500 lines
- [x] Review for duplicated code and try to consolidate and use imports instead
- [x] Review if you made any changes that need to be propagated to requirements, milestones, or plans
- [x] Check to make sure we have explicit imports and minimal coupling

---

## Milestone 10: Enhanced State Encoder
- **Focus**: Replace the current 197-feature raw-occupancy encoder with a richer encoder that includes venue/resource lookahead, worker turns-until-available, and pre-computed scoring-derived features (Festival BFS groups, Fromagerie shelf counts, Bistro pairings, Villes influence per region). See the `[ASPIRATIONAL]` design notes at the top of `src/ai/state_encoder.py` for the full spec. Trigger: run 10 000 games with Milestone 8 training; if win rate plateaus below 0.35 or fails to improve consistently, the linear approximator likely cannot extract the scoring structure from raw occupancy flags and this milestone should be prioritised.

### Plan Review
- [x] Verify that the feature plan fully describes the intended feature, ensuring all details are present and unambiguous.
- [x] Confirm that all aspects of the feature plan are adequately addressed and covered by the defined requirements.
- [x] Ensure that all requirements pertinent to the feature are properly organized and allocated to the correct milestones.
- [x] Check that the files designated as outputs for the milestone are capable of completely containing the features planned for that specific milestone.
- [x] Define convenient feature flags — `enhanced` param on `encode_state` (default True); `use_enhanced_encoder` config key.

### Outputs
- `src/ai/state_encoder.py` — rewritten `encode_state` and updated `STATE_VECTOR_SIZE`
- `tests/test_state_encoder.py` — updated tests for new vector length and new feature ranges

### Coding Tasks
- [x] 10E.1 Venue/resource lookahead sub-vector: one-hot(4) venue at rotation+0..+3; one-hot(4) resource at rotation+0..+2 (28 features)
- [x] 10E.2 Worker turns-until-available sub-vector: for each of 3 cheese types, one-hot(4) where index = turns until worker is in hand (12 features)
- [x] 10E.3 Festival derived sub-vector: `score_festival` result (normalised), top-3 connected group sizes (normalised by 7), count of empty adjacent spaces (normalised)
- [x] 10E.4 Fromagerie derived sub-vector: own distinct shelves occupied (normalised by 6), shelves still available (normalised by 6), each opponent's shelf count (3 × normalised by 6), count of unoccupied point-bonus spaces available (normalised)
- [x] 10E.5 Bistro derived sub-vector: own pairings (normalised by 9), own half-tables (normalised by 9), own Bronze/Silver/Gold token counts (normalised by 9 each), each opponent's pairings (3 × normalised by 9)
- [x] 10E.6 Villes derived sub-vector: per region (6 regions) — self influence (normalised), max-opponent influence (normalised), delta (self − max_opp, normalised), winner status one-hot(3) = 6 × 6 = 36 features
- [x] 10E.7 Update `STATE_VECTOR_SIZE` constant; update assertion in `encode_state`; update `_FEATURE_SIZE` in `q_agent.py` (depends on STATE_VECTOR_SIZE); re-initialise weights (saved models from earlier training are incompatible with the new vector size — document this clearly)
- [x] 10E.8 Update `tests/test_state_encoder.py`: verify new vector length; verify scoring-derived features are non-zero for a state with known placements; verify lookahead features match expected rotation offsets

#### Code Review Tasks
- [x] Review if you made any files that are too long, try to keep them below around 500 lines — `state_encoder.py` is 514 lines (BFS logic cannot be reduced without losing clarity)
- [x] Review for duplicated code and try to consolidate and use imports instead — Festival BFS duplicated from scoring.py but justified: encoder needs intermediate group sizes that `score_festival` doesn't expose, and extracting a shared helper would violate `game/` ← `ai/` dependency direction
- [x] Review if you made any changes that need to be propagated to requirements, milestones, or plans — requirements 9.2.1–9.2.8 checked off below
- [x] Check to make sure we have explicit imports and minimal coupling — all imports explicit, correct dependency direction

---

## Stretch Goal: Customer Token Randomisation

In the real game, the 6 customer tokens (purple 7, blue 7, green 8, pink 8, white 9, yellow 9) are placed randomly on the Villes board at game start. The simulation currently fixes them in CSV order (see `assumptions.md`). This means Chart 13 may conflate positional advantage (which Villes spaces are easiest to reach) with token-value advantage, making its advice unreliable for real games.

**Trigger**: Run Chart 13 after Milestone 6. If the win-correlation results are clearly dominated by token point value (white/yellow always best regardless of position), fixed assignment is likely fine. If the ranking looks spatially biased or the caveat creates genuine doubt about the chart's advice, implement this stretch goal before drawing conclusions.

### Required changes (in order)

- [ ] Remove the "Regional assignments are fixed" entry from `assumptions.md` and add "Customer token placement is randomised at game start" to the "Things That Are Randomised" section.
- [ ] In `setup_game` (`src/game/board.py`), shuffle the list returned by `data.customer_tokens` before assigning region positions; use the existing `seed` parameter so games remain reproducible.
- [ ] Update `GameState.villes_customer_token_holders` initialisation in `setup_game` to reflect the shuffled assignment rather than the CSV order.
- [ ] Update `tests/test_board.py` to verify that two games with different seeds produce different token arrangements (statistical check: run 10 seeds, assert not all identical).
- [ ] Re-run Chart 13 after this change and compare results against the fixed-assignment run to confirm whether the spatial vs value distinction matters.

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
