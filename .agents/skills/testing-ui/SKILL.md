# Testing the Board Visualiser UI

## Overview

The board visualiser (`ui.py`) is a tkinter desktop application that steps through game replays. It displays four venue quadrants (Festival, Fromagerie, Villes, Bistro), a player sidebar, a score breakdown table, navigation controls, and a debug structure toggle panel.

## Environment Setup

### tkinter Availability

The pyenv-installed Python may not include the `_tkinter` C extension. If `import tkinter` fails with `ModuleNotFoundError: No module named '_tkinter'`:

1. Install tk development libraries: `sudo apt-get install -y python3-tk tk-dev`
2. Use system Python (`/usr/bin/python3`) which includes tkinter after installing `python3-tk`
3. Install project dependencies for system Python: `/usr/bin/python3 -m pip install numpy matplotlib rich`

Alternatively, rebuild the pyenv Python version with tk support after installing `tk-dev`.

### Display

The app requires an X11 display. Verify with `echo $DISPLAY` (should be `:0` or similar). If not set, export it: `export DISPLAY=:0`.

## Launch Command

```bash
cd /path/to/fromage-ai && DISPLAY=:0 /usr/bin/python3 ui.py
```

The app opens a window titled "Fromage" showing Turn 1 at pre-placement state.

## Key UI Flows to Test

### 1. Initial Render
- Window opens with dark theme background
- Four venue quadrants display with labelled headers and player arrows
- Player sidebar shows 4 player cards (P0–P3) with coloured borders
- Score Breakdown table shows category rows with dashes
- Control bar at bottom with Back, Fwd, primary action, and Run to End buttons
- Status text shows "Turn 1 · Pre-placement (1/1)"

### 2. Step Through Turns
- Click the primary action button (e.g. "Place Workers ▶") to advance
- Board updates with cheese tokens (coloured fills) and worker markers
- Status text updates to reflect current phase
- Button label changes between phases ("Place Workers" → "Rotate Board")
- Player token counts decrement

### 3. Run to End
- Click "Run to End" to fast-forward to game completion
- Status shows "Game over — Turn N — Winner(s): P#"
- Score table populates with numbers
- Winner's TOTAL cell should be highlighted with that player's accent colour

### 4. Debug Structure Toggle
- Bottom panel shows structure buttons (Barn, Dock, Grnhs, HQ) per player
- Click a button to toggle: locked (dark) → unlocked (green) → locked (dark)
- Player labels (P0–P3) should show distinct accent colours

### 5. History Navigation
- After stepping forward, click "◀ Back" or "Fwd ▶" to navigate history
- Board state should update to reflect the historical step

## Style Constants

All visual constants are centralised in `src/ui/styles.py`. When verifying theme consistency, check that UI elements reference these constants rather than hardcoded values.

Key constants to verify visually:
- Background: dark charcoal (#1E1E2E)
- Surface cards: slightly lighter (#2A2A3C)
- Primary action button: purple accent (#6C63FF)
- Player colours: P0=red (#FF6B6B), P1=blue (#4FC3F7), P2=green (#81C784), P3=orange (#FFB74D)
- Cells: 36px with 6px corner radius

## Unit Tests

Run from project root:
```bash
pytest
```

Currently 194 tests covering game logic. UI tests are visual-only (no automated UI test framework).

## Devin Secrets Needed

None — this is a local desktop application with no external service dependencies.
