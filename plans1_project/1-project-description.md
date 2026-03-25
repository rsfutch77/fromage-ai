# Project Description: Fromage-ML

## 🎬 Inspiration

This project is inspired by the desire to deeply understand and master [Fromage](https://www.allplay.com/board-games/fromage), a 2024 simultaneous worker-placement board game by Matthew O'Malley and Ben Rosset, themed around competitive cheesemaking in early 20th-century France.

Fromage is a game with elegant but deep decision-making: each turn you choose which resources to gather and which cheeses to make, but workers committed to higher-yield spots take multiple turns to return—creating meaningful tension between short-term gain and long-term tempo. The rotating board adds another layer: the venue facing you changes each round, so what you can *do* and what you can *score* evolves constantly. Understanding the statistical best moves requires modeling all these overlapping constraints.

The prior [Everdell AI project](../../../everdell_workspace/) established a proof of concept for this class of problems: simulate the game in Python, train an AI via self-play, and use it to recommend moves during live play. Fromage-ML takes the same idea further with a cleaner architecture, better tooling, and lessons learned from that first attempt.

**Development Approach**: Build a complete game simulation engine first, validate it against the real rules, then layer statistical analysis and AI training on top. The final product is a local tool that—given the current game state—recommends the statistically best move(s) for a human player to execute at the real table.

---

## 🌟 Vision Statement

To create a local desktop tool that simulates the Fromage board game, trains an AI through self-play, and provides human players with statistically grounded move recommendations—helping any player at any skill level understand the best strategy for their current board state.

---

## 🎯 Core Philosophy

### Accuracy First

The simulation must be a faithful, rules-complete implementation of the base game. A move recommender is only as good as the game engine underneath it. Every mechanic—worker timing, board rotation, cheese aging, each venue's scoring rule—must be correctly modeled before any AI training begins.

### Interpretable Results

Unlike a black-box neural network, the tool should be able to explain *why* a move is good. Where possible, preference is given to approaches that produce statistics (e.g., win rates, average point deltas, resource efficiency curves) over approaches that only produce a ranking.

### Personal Use, Not Production

This is a personal tool. No web server, no accounts, no deployment. All computation runs locally. The UI can be simple—a terminal interface or a minimal desktop window is fine, as long as it's clear and easy to use at the game table.

### Lessons from Everdell

The Everdell project used a single large `ai_game.py` file (~730 lines) and mixed game logic, AI logic, and UI together. Fromage-ML will keep these cleanly separated from the start: `game/` for simulation, `ai/` for training, `ui/` for interaction. File size stays under ~500 lines per module.

---

## 📋 Feature Roadmap

### Phase 0: Game Research & Rules Formalization
- [ ] Document all game components (resources, worker types, cheese types, quadrant rules)
- [ ] Formalize each venue's scoring algorithm in pseudocode
- [ ] Identify all edge cases and ambiguous rules from the physical manual
- [ ] Define the complete state representation for the simulation

### Phase 1: Game Simulation Engine
- [ ] Implement board state: resources, workers, cheese tokens, board rotation
- [ ] Implement all four quadrant rules (Festival, Villes, Fromagerie, Bistro)
- [ ] Implement worker placement and recovery timing (bronze/silver/gold spots)
- [ ] Implement cheese-making rules (worker type matching, aging)
- [ ] Implement turn structure, simultaneous action resolution, and game-end trigger
- [ ] Implement full scoring calculation for all venues
- [ ] Unit tests for all game rules

### Phase 2: Random Baseline & Statistical Analysis
- [ ] Implement a random-play agent (baseline)
- [ ] Run N-game simulations between random agents; collect and store results
- [ ] Analyze: most common winning strategies, resource distributions, cheese mix efficiency
- [ ] Produce statistical tables: which moves/cheeses/venues score highest on average

### Phase 3: AI Training via Self-Play
- [ ] Implement a Q-learning or MCTS-based agent (informed by Phase 2 findings)
- [ ] Self-play training loop with configurable episode count
- [ ] Save/load trained model
- [ ] Track and display training progress (win rates over time, score distributions)

### Phase 4: Move Recommender (Test Mode)
- [ ] UI to input current game state (your hand, resources, workers, board position)
- [ ] Query trained AI for best move(s) with confidence scores
- [ ] Display top 3 recommended moves with explanation of reasoning
- [ ] Allow user to confirm actual move played and update state

### Phase 5: Analysis & Visualization (Stretch Goal)
- [ ] Charts: card/cheese play frequency, venue scoring distributions
- [ ] Heatmap: expected points by board position and turn number
- [ ] Export session summary to CSV or PDF

---

## 🛠️ Technical Architecture Overview

### Core Stack

- **Language**: Python 3.x (primary)
- **AI/ML**: Standard library + `numpy`; Q-learning or MCTS for Phase 3 (no heavy ML frameworks required for initial training; `scikit-learn` or `pytorch` added only if needed)
- **UI**: `rich` for terminal output (Phase 1-3); optional `customtkinter` desktop window for Phase 4 (decision pending)
- **Storage**: `sqlite3` for simulation results and trained model state; `json` for game state serialization
- **Testing**: `pytest`
- **Plotting**: `matplotlib` for training charts and analysis (matches Everdell project precedent)

### Project Structure

```
fromage/
├── src/
│   ├── game/                   # Game simulation engine (pure logic, no UI)
│   │   ├── state.py            # GameState dataclass: board, players, workers, rotation
│   │   ├── board.py            # Quadrant definitions and board rotation
│   │   ├── actions.py          # Action enumeration and validation
│   │   ├── resources.py        # Resource types and counts
│   │   ├── cheese.py           # Cheese types, requirements, aging rules
│   │   ├── workers.py          # Worker types, placement, recovery timing
│   │   ├── scoring.py          # Venue scoring algorithms
│   │   └── engine.py           # Turn loop, action resolution, game-end detection
│   ├── ai/                     # AI agents and training
│   │   ├── random_agent.py     # Baseline: fully random legal moves
│   │   ├── agent.py            # Trained agent (Q-learning or MCTS)
│   │   └── trainer.py          # Self-play training loop
│   ├── analysis/               # Statistical analysis and reporting
│   │   ├── simulator.py        # Batch game runner
│   │   ├── stats.py            # Aggregation and summary statistics
│   │   └── plotting.py         # matplotlib charts
│   └── ui/                     # User interface
│       ├── cli.py              # Rich terminal interface for test mode
│       └── app.py              # Optional: desktop GUI wrapper
├── data/                       # SQLite databases, saved models, cached results
├── tests/
│   └── test_<module>.py
├── plans1_project/             # This folder
└── requirements.txt
```

### Why Python (not something else)?

The Everdell project demonstrated that Python is fast enough for this class of board game simulation—100 training episodes completed in under a minute on modest hardware. Fromage has comparable complexity. A compiled language (Rust, C++) would be faster but adds friction for a personal tool; a JavaScript/TypeScript solution would enable browser-based use but adds no value for a local app. Python + numpy covers every need.

### State Representation

A `GameState` object captures everything needed to deterministically recreate any moment in the game:
- Board rotation index (which quadrant faces which player)
- For each player: resources held, workers on board (with return-turn counters), cheese tokens placed, cheese in progress (aging counter), score by venue
- Meadow / available actions for current turn
- Turn number and game-end flag

This state must be serializable to JSON for saving/loading test scenarios.

---

## 📝 Development Principles

### For This Project

1. **Rules before AI**: The simulation engine must pass all unit tests before any AI agent is written.
2. **Separate concerns**: `game/` knows nothing about `ai/`; `ai/` knows nothing about `ui/`. Dependencies flow one direction only.
3. **Reproducibility**: All random seeds configurable; any simulation run can be replayed exactly.
4. **Log everything**: Training runs produce logs with per-episode scores for later analysis.
5. **Fail loudly**: Invalid game states raise exceptions—never silently produce wrong results.
6. **Keep files small**: ~500 line limit per module. Split when approaching this.

### Non-Requirements

- No multiplayer networking
- No web deployment
- No integration with Board Game Arena or any online platform
- No real-time data fetching
- No mobile support
- No support for Fromage expansions (base game only)

---

## 🔭 Future Stretch Goals

- Support for expansions if they are released
- Opponent modeling: adapt recommendations based on observed opponent tendencies
- Opening-book style: pre-computed best first 2-3 turns by player count and starting resources
- Export trained AI as a standalone script to share with friends

---

*Last updated: 2026-03-23 — Initial project description, Fromage-ML.*
