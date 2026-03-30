# Fromage-ML: Fixed Simulation Assumptions

Things held constant in the simulation rather than randomised or made configurable.

---

## Player Count

Always 4 players — no variable player count; all simulation logic assumes exactly 4.

---

## Board Configuration

- **4-player insert only (Side I)** — no other board configurations or insert sides are in scope.
- **Structure Tiles (advanced mode) are entirely out of scope** — not implemented.

---

## Fixed Orientations

- **`resource_tile_orientation` is always 0** — not randomised at setup. This fixes which resource faces which player at game start.

**Clockwise resource order** (position 0 → 1 → 2 → 3):

| Position | Resource  |
|----------|-----------|
| 0        | Livestock |
| 1        | Orders    |
| 2        | Structure |
| 3        | Fruit     |

Defined as `RESOURCE_ORDER` in `src/game/types.py`.

**Starting resources** derived from fixed orientation 0:

| Player | Faces     | Left (×2) | Opposite (×1) |
|--------|-----------|-----------|---------------|
| 0      | Livestock | Orders    | Structure     |
| 1      | Orders    | Structure | Fruit         |
| 2      | Structure | Fruit     | Livestock     |
| 3      | Fruit     | Livestock | Orders        |

Note: "Orders" as a starting resource is stored directly in `player.resources[ResourceType.ORDER]` (not converted to order cards at setup).

---

## Turn Order

**Sequential turn order** — players act in order 0→1→2→3 each rotation. Turns are simultaneous in the real game but sequential here (valid because each player only operates in their own quadrant).

---

## Fromagerie Resource-Bonus Shelf Effects

Resource-bonus shelf bonuses require a player choice not encoded in `MakeCheeseAction`. The simulation uses a deterministic fallback:

| Bonus string              | Effect                        |
|---------------------------|-------------------------------|
| `gain_1_resource_any`     | Gain 1 STRUCTURE              |
| `gain_2_diff_resources`   | Gain 1 STRUCTURE + 1 LIVESTOCK |
| `trade_resource_for_any`  | No-op (skip)                  |

---

## Customer Tokens

**Regional assignments are fixed** — loaded from `data/customer_tokens.csv` in fixed order; not randomly distributed at game start.

---

## Milking Parlour

**Bonus cheese is restricted to the currently-facing venue** — same restriction as make-cheese actions. All 4 venue boards (Fromagerie, Bistro, Villes, Festival) are quadrants of the outer board; a player can only place in the one facing them.

---

## Structure Unlock Costs

**Slot N costs N STRUCTURE tokens** — slot 1 costs 1, slot 2 costs 2, slot 3 costs 3, slot 4 costs 4. Slots do not need to be unlocked sequentially.

---

## Safety Caps

- **`MAX_ACTIONS_PER_TURN = 200`** — legal action generation is capped to prevent combinatorial explosion in complex states.
- **`MAX_TURNS_PER_GAME = 500`** — safety cap to prevent infinite loops in simulation.

---

## Things That Are Randomised (not assumptions)

- Board ID assignment to players (random shuffle of 1–4 at setup)
- Order card deck shuffle at setup (reproducible with optional seed)
