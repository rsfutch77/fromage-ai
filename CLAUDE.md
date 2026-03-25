# Fromage-ML — Claude Instructions

## Bash Tool Rules
- Do NOT write Python code inside Bash tool calls (no `python -c`, no inline scripts)
- To run Python: create a dedicated `.py` file, then call it with `python path/to/file.py`

## Code Style
- Keep files under ~500 lines where possible
- Dependency direction is strict: `game/` ← `ai/` ← `analysis/` ← `ui/`; never import upward
- No wildcard imports (`from module import *`)
- Raise `IllegalActionError` for illegal game states — never silently ignore them
- Use Python `logging`, not bare `print`, for all diagnostic output

## Workflow
- Milestone workflow: write milestone → plan review → implement → check off → code review → user test
- All game data lives in `data/` as CSVs; load via `GameDataLoader`, never hardcode game constants
- Config lives in `config/` as JSON files (`simulation_config.json`, `agent_config.json`)
- State is never mutated in place — all game functions return new `GameState` instances
- Entry points: `src/train.py`, `src/recommend.py`, `src/analyze.py`
- Run tests with `pytest` from the project root (config in `pytest.ini`)

## Key Design Decisions
- Always 4 players — no variable player count logic anywhere
- Board rotation IS the aging mechanic — no separate age counter needed
- `direction` column in CSVs = age tier (Bronze/Silver/Gold); rename to `age` on load
- Customer token arrangement is fixed (not randomized) per `data/customer_tokens.csv`
- Order cards are generated programmatically (4 per type×age = 36 total), not loaded from CSV
- Q-learning only — numpy, no PyTorch/TensorFlow
