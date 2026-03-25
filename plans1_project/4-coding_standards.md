# Fromage-ML — Coding Standards

> **Reference document.** These standards apply to all code in the `fromage` project. Every implementation, review, and milestone must conform to these rules. When in doubt, consult this document first.

---

## Table of Contents

1. [Language & Runtime](#1-language--runtime)
2. [Project Directory Structure](#2-project-directory-structure)
3. [Naming Conventions](#3-naming-conventions)
4. [File Size Policy](#4-file-size-policy)
5. [Import Style](#5-import-style)
6. [Dependency Direction](#6-dependency-direction)
7. [Error Handling](#7-error-handling)
8. [Logging](#8-logging)
9. [Configuration Management](#9-configuration-management)
10. [SQLite Conventions](#10-sqlite-conventions)
11. [Reproducibility & Random Seeds](#11-reproducibility--random-seeds)
12. [Testing Standards](#12-testing-standards)
13. [Rich CLI Style System](#13-rich-cli-style-system)
14. [Code Review Checklist](#14-code-review-checklist)

---

## 1. Language & Runtime

- **Python 3.11+ only.** No JavaScript, TypeScript, or any other runtime.
- No web frameworks (Flask, FastAPI, Django).
- No cloud SDKs or remote APIs — this is a fully local tool.

### Approved Libraries

| Library | Purpose |
|---|---|
| `numpy` | Array math for AI state representations and statistical analysis |
| `sqlite3` (stdlib) | All persistent storage — simulation results, trained model weights, game logs |
| `json` (stdlib) | Game state serialization/deserialization |
| `logging` (stdlib) | All internal logging |
| `rich` | Terminal output: panels, tables, progress bars, colors |
| `matplotlib` | Training charts and statistical analysis plots |
| `pytest` | Unit testing |
| `customtkinter` | Optional desktop GUI for Phase 4 move recommender (do not add until Phase 4) |
| `torch` or `scikit-learn` | Advanced AI models only if Q-learning proves insufficient (do not add prematurely) |

Do not introduce new external libraries without updating `requirements.txt` and adding a rationale comment in the relevant feature plan.

---

## 2. Project Directory Structure

```
fromage/
├── src/
│   ├── game/                   # Game simulation engine — pure logic, no UI, no AI
│   │   ├── state.py            # GameState dataclass
│   │   ├── board.py            # Quadrant definitions and board rotation
│   │   ├── actions.py          # Action enumeration and validation
│   │   ├── resources.py        # Resource types and counts
│   │   ├── cheese.py           # Cheese types, costs, aging rules
│   │   ├── workers.py          # Worker types, placement, recovery timing
│   │   ├── scoring.py          # Venue scoring algorithms
│   │   └── engine.py           # Turn loop, simultaneous action resolution, game-end
│   ├── ai/                     # AI agents and training — depends on game/, not ui/
│   │   ├── random_agent.py     # Baseline: random legal move selection
│   │   ├── agent.py            # Trained agent (Q-learning or MCTS)
│   │   └── trainer.py          # Self-play training loop
│   ├── analysis/               # Statistical analysis — depends on game/, not ai/ or ui/
│   │   ├── simulator.py        # Batch game runner
│   │   ├── stats.py            # Aggregation and summary statistics
│   │   └── plotting.py         # matplotlib charts
│   └── ui/                     # User interface — depends on all others
│       ├── cli.py              # Rich terminal interface
│       └── app.py              # Optional: customtkinter desktop GUI
├── data/                       # SQLite DBs, saved models, exported CSVs
├── tests/
│   └── test_<module>.py        # One test file per source module
├── plans1_project/             # Project planning documents
└── requirements.txt
```

New modules go in the most semantically appropriate directory. Never create ad-hoc top-level source files.

---

## 3. Naming Conventions

| Entity | Style | Examples |
|---|---|---|
| Classes | `PascalCase` | `GameState`, `RandomAgent`, `CheeseType`, `VenueScorer` |
| Methods & functions | `snake_case` | `get_legal_actions()`, `apply_action()`, `score_venue()` |
| Variables | `snake_case` | `worker_count`, `cheese_tokens`, `rotation_index` |
| Constants / feature flags | `UPPER_SNAKE_CASE` with `ENABLE_` prefix for flags | `MAX_WORKERS`, `ENABLE_VERBOSE_LOGGING`, `BASE_CHEESE_TYPES` |
| Source files | `snake_case.py` | `random_agent.py`, `scoring.py`, `game_engine.py` |
| Config files | `snake_case.json` or `snake_case.py` | `game_config.json`, `training_config.json` |
| Test files | `test_<module_name>.py` | `test_scoring.py`, `test_engine.py` |
| Enums | `PascalCase` class, `UPPER_SNAKE_CASE` members | `class ResourceType(Enum): MILK = "milk"` |

### Examples

```python
# ✅ Correct
class GameState:
    def get_legal_actions(self) -> list["Action"]:
        ...

class ResourceType(Enum):
    MILK = "milk"
    CULTURE = "culture"
    RENNET = "rennet"

MAX_WORKERS = 4
ENABLE_VERBOSE_LOGGING = False

# ❌ Wrong
class gamestate: ...            # not PascalCase
def GetActions(): ...           # not snake_case
maxWorkers = 4                  # not UPPER_SNAKE_CASE for constant
```

---

## 4. File Size Policy

**Keep all source files under ~500 lines.**

If a file grows beyond this limit, split it into focused sub-modules. Each module must have a single clear responsibility.

```
# Example: engine.py grows too large
# Split into:
#   engine.py        ← core turn loop only
#   resolver.py      ← simultaneous action resolution logic
#   validators.py    ← action legality checking
```

This rule applies at every milestone review.

---

## 5. Import Style

- **Never use wildcard imports.** `from module import *` is prohibited.
- Import only what a module actually uses.
- Use explicit full import paths — never rely on implicit package resolution.
- Extract shared logic into `utils/` (if created) and import from there.

```python
# ✅ Correct
import sqlite3
import logging
from enum import Enum
from dataclasses import dataclass, field
from src.game.state import GameState
from src.game.actions import Action, ActionType

# ❌ Wrong
from src.game import *          # wildcard — prohibited
from game.state import *        # wildcard — prohibited
```

---

## 6. Dependency Direction

This is the most important architectural rule in the project:

```
game/  ←  ai/  ←  ui/
game/  ←  analysis/  ←  ui/
```

- `game/` has **no imports** from `ai/`, `analysis/`, or `ui/`
- `ai/` may import from `game/` only
- `analysis/` may import from `game/` only
- `ui/` may import from all of the above

Violating this rule means game logic has leaked into the wrong layer. Refactor before proceeding.

---

## 7. Error Handling

- **All I/O operations** (file, database, JSON parsing) must be wrapped in `try/except`.
- **Invalid game states** must raise exceptions immediately — never silently produce wrong output.
- Log all errors with `logging.error()`. Never silently swallow exceptions.
- The game engine must be strict: if an action is illegal, raise `IllegalActionError`. Do not "correct" it silently.

```python
# ✅ Correct — illegal state raises immediately
def apply_action(self, state: GameState, action: Action) -> GameState:
    if action not in self.get_legal_actions(state):
        raise IllegalActionError(f"Action {action} is not legal in state {state}")
    ...

# ✅ Correct — I/O wrapped
def load_model(path: str) -> dict:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Failed to load model from {path}: {e}")
        return {}

# ❌ Wrong — silently returns wrong result
def apply_action(self, state, action):
    if action not in self.get_legal_actions(state):
        return state   # hides the bug
```

---

## 8. Logging

- Use Python's `logging` module exclusively. **No bare `print()` calls in non-UI code.**
- `ui/cli.py` and `ui/app.py` use `rich` console output for display; everything else uses `logging`.
- Log level must be configurable via config — not hardcoded.
- Log all: training episode results, scoring calculations (at DEBUG), illegal action attempts, and file I/O events.

```python
import logging
logger = logging.getLogger(__name__)

def run_episode(self) -> dict:
    logger.info(f"Starting episode {self.episode_count}")
    ...
    logger.debug(f"Player scores this episode: {scores}")
    logger.info(f"Episode complete. Winner: {winner}")
```

### Log Level Guidelines

| Level | When to use |
|---|---|
| `DEBUG` | Per-action state, per-turn details, individual scoring steps |
| `INFO` | Episode start/end, training milestones, model save/load |
| `WARNING` | Unexpected but recoverable: missing config key (using default), model file not found |
| `ERROR` | I/O failure, JSON parse error, database write failure |
| `CRITICAL` | Corrupted game state, unrecoverable simulation error |

---

## 9. Configuration Management

- **No hardcoded values** for player counts, episode counts, resource limits, or file paths.
- All tunable parameters live in config files under `src/config/` or a top-level `config/` directory.
- Feature flags use `UPPER_SNAKE_CASE` with `ENABLE_` prefix.

### Config File Locations

| File | Contents |
|---|---|
| `config/game_config.json` | Player count range, resource maximums, cheese token counts, worker counts |
| `config/training_config.json` | Episode count, learning rate, discount factor, random seed, model save path |
| `config/app_config.json` | Log level, output paths, UI mode (cli vs gui) |

### Example: `training_config.json`

```json
{
  "episodes": 1000,
  "random_seed": 42,
  "learning_rate": 0.1,
  "discount_factor": 0.95,
  "model_save_path": "data/model.pkl",
  "ENABLE_VERBOSE_LOGGING": false
}
```

### Startup Validation

All config values must be validated before any simulation or training begins. Missing required keys raise `ValueError`.

---

## 10. SQLite Conventions

- **SQLite only** for all persistent storage.
- Column names in `snake_case`.
- All timestamps stored as UTC ISO 8601 strings.
- Use parameterized queries exclusively — never string interpolation in SQL.
- Include `schema_version` in tables subject to future changes.

### Key Tables

```sql
-- simulation_results: one row per completed game
CREATE TABLE IF NOT EXISTS simulation_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at          TEXT    NOT NULL,   -- UTC ISO 8601
    player_count    INTEGER NOT NULL,
    winner_index    INTEGER NOT NULL,
    scores          TEXT    NOT NULL,   -- JSON array of per-player scores
    move_log        TEXT,               -- JSON array of all moves (optional)
    schema_version  INTEGER NOT NULL DEFAULT 1
);

-- training_runs: one row per training session
CREATE TABLE IF NOT EXISTS training_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TEXT    NOT NULL,
    episodes        INTEGER NOT NULL,
    final_win_rate  REAL,
    model_path      TEXT,
    schema_version  INTEGER NOT NULL DEFAULT 1
);
```

---

## 11. Reproducibility & Random Seeds

- Every random operation (card draw, shuffle, random agent) must accept a seed.
- The top-level runner passes a configurable seed from `training_config.json` down to all components.
- Any simulation run must be exactly reproducible given the same seed.

```python
import random
import numpy as np

def set_global_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
```

---

## 12. Testing Standards

- **Framework:** `pytest`
- **Location:** `tests/test_<module_name>.py` — one file per source module
- All game-state transitions must be unit tested
- Test both legal and illegal action paths
- Mock all file I/O and database operations in unit tests
- Follow the **AAA pattern**: Arrange → Act → Assert
- Tests must be fully independent — no shared mutable state

### Priority Test Coverage (Phase 1)

Every scoring rule for every venue must have at least one passing test before Phase 2 begins. This is the highest-priority test surface in the project.

```python
# tests/test_scoring.py
def test_festival_score_empty_city():
    # Arrange
    state = GameState.empty(player_count=2)
    scorer = VenueScorer()
    # Act
    score = scorer.score_festival(state, player_index=0)
    # Assert
    assert score == 0

def test_bistro_score_matching_pair():
    # Arrange
    state = make_state_with_cheese(player=0, cheeses=["brie", "champagne"])
    scorer = VenueScorer()
    # Act
    score = scorer.score_bistro(state, player_index=0)
    # Assert
    assert score == EXPECTED_BISTRO_PAIR_SCORE
```

---

## 13. Rich CLI Style System

All terminal output in `ui/cli.py` uses `rich`. Never call `print()` directly in UI code.

### Color Palette

| Color | Markup Tag | Usage |
|---|---|---|
| Cyan | `[cyan]` / `[bold cyan]` | Panel titles, section headers |
| Green | `[green]` / `[bold green]` | Success, winning player, recommended move |
| Yellow | `[yellow]` / `[italic yellow]` | Warnings, in-progress states |
| Magenta | `[magenta]` | AI reasoning, debug info |
| Red | `[bold red]` | Errors, illegal action warnings |
| White | `[white]` | Default table content |

### Usage Examples

```python
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Recommended move panel
console.print(Panel(
    "[bold green]Best Move:[/bold green] Gather 2 Milk (Silver spot)\n"
    "[cyan]Expected point delta:[/cyan] +3.2\n"
    "[cyan]Worker returns in:[/cyan] 2 turns",
    title="[bold cyan]Fromage-ML Recommendation[/bold cyan]",
    border_style="cyan"
))

# Training progress
console.print(f"[yellow]Episode {ep}/{total} — Win rate: {win_rate:.1%}[/yellow]")

# Error
console.print("[bold red]✗ Invalid game state: worker count exceeds maximum.[/bold red]")
```

---

## 14. Code Review Checklist

Every implementation — new feature, bug fix, or refactor — must pass all four checks before moving to the next milestone:

| # | Check | Pass Criteria |
|---|---|---|
| 1 | **File size** | No file exceeds ~500 lines. Split if needed. |
| 2 | **Import hygiene** | All imports explicit and minimal. No wildcards. No unused imports. |
| 3 | **No duplicated logic** | Repeated logic extracted and imported. No copy-paste code blocks. |
| 4 | **Dependency direction** | `game/` has zero imports from `ai/`, `analysis/`, or `ui/`. |
| 5 | **Test coverage** | All new scoring rules and action validators have at least one unit test. |
| 6 | **Propagation check** | Interface changes reflected in requirements, milestones, and config docs. |

---

*Last updated: 2026-03-23 — Fromage-ML project coding standards, Python/SQLite/Rich stack.*
