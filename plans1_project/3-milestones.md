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
