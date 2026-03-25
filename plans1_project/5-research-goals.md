# Research Goals: Fromage-ML

> **Purpose**: This document captures everything we need to know before writing complete requirements and beginning implementation. Questions marked ✅ are answered from the physical rulebook (Fromage_Rulebook_20231208.pdf). Questions marked ❓ still require inspection of physical components or board art that was not legible in the PDF.

---

## How to Use This Document

1. Read through each section. Questions marked ❓ are unanswered.
2. Consult the physical rulebook, a playthrough video, or Board Game Arena to find the answer.
3. Fill in the answer below the question and mark it ✅.
4. Once a full section is answered, draft the corresponding module requirements in `2-requirements.md`.
5. Do not begin coding a module until all ❓ in its section are resolved.

---

## Section 1: Components & Setup

### 1.1 Player Count
✅ **Always 4 players** — this is the fixed assumption for all of Fromage-ML. Simulation scope decision: no variable player count logic needed anywhere in the codebase.
✅ At 4 players, **no cheese spaces are blocked** (⊘ spaces only appear in 1–3 player games). All cheese spaces on all quadrants are always available.

### 1.2 Worker Types & Counts
✅ **3 worker types: Soft, Hard, and Bleu.** These match the 3 cheese types. Each player gets exactly 1 Worker of each type (3 Workers total). Workers attach to colored Worker Bases.
✅ **No way to gain additional Workers.** The Barn Structure ability lets a Worker placed there not count as the Gather Resources action, effectively freeing up Worker capacity — but the total Worker count stays at 3.
✅ **Worker type matters for Making Cheese** (must match Cheese Type of the space), but **does NOT matter for Gathering Resources** (any Worker can be placed on any resource space).

### 1.3 Resources
✅ **4 resource types: Structures, Livestock, Fruit, and Orders.** These are the 4 quadrants of the central Resource Tile, each corresponding to one resource type.
  - **Structures** 🏠 — go in the space to the left of your Structure abilities on the Player Board. Used to unlock Structures.
  - **Livestock** 🐄🐑🐐 — go in the pasture on the Player Board. Used for Milking Parlours (bonus cheese).
  - **Fruit** 🍓🍇🫐 — go in the basket on the Player Board. Used to make Fruited Cheese and Jam spaces; scored at end.
  - **Orders** 🃏 — drawn as Order Cards, placed face-up to the left of the Player Board.
✅ **Resources are unlimited in supply.** Shared Resource Trays; if one runs out, take from the other tray or use the x3/x5 multiplier tokens.
❓ **Whether there is a physical cap per player.** The Player Board has specific areas for each resource (pasture, basket, structure space), but the rulebook does not state a hard numeric maximum. Need to inspect physical Player Board to see if space is the practical limit.

### 1.4 Cheese Types & Costs
✅ **3 cheese types: Soft (△), Hard (🧀 wedge), Bleu (🔵 round).** These correspond exactly to the 3 Worker types.
✅ **No resource cost to make regular cheese.** You only need the matching Worker type and an empty cheese space in your current quadrant. The "cost" is tying up your Worker for 1–3 turns.
✅ **Fruited Cheese (🍓) and Jam (🫙) spaces require spending a Fruit Token.** Move Fruit from basket to the corresponding spent area. These are otherwise made normally with a Worker.
✅ **15 Cheese Tokens per player.** When you place your last one, you trigger game-end.
✅ **No recipe cards.** Cheese spaces on the board quadrants determine what types and ages are available at each venue each turn.
✅ **Cheese space counts per venue now fully specified in CSV files.** All spaces filled in by user from physical board (Side I, 4-player only). See `data/` directory for complete layouts.

### 1.5 Board Rotation
✅ **Fixed 90° clockwise rotation after every turn.** Not influenced by players.
✅ **Full rotation = 4 turns** (each quadrant faces each player once per cycle).
✅ **Workers rotate with the board.** This is how aging is tracked — a Worker placed on a Bronze space faces the player again after 1 rotation (1 turn), Silver after 2, Gold after 3. There is no separate aging counter; the rotation *is* the aging mechanism.
✅ **Direction convention for cheese spaces**: The cheese icon printed on each space points in a direction that encodes its age tier. Direction is described **player-relative** — from the perspective of the player currently facing that quadrant. Using absolute cardinal directions (N/S/E/W) is avoided because each of the 4 board quadrants is oriented differently and would require remapping.
  - **right** → Bronze (1 turn): after 1 CW rotation the icon points toward the player, worker is retrieved
  - **away** (far side) → Silver (2 turns): takes 2 CW rotations to point toward the player
  - **left** → Gold (3 turns): takes 3 CW rotations to point toward the player
  - `age` is fully derived from `direction` — no separate tracking needed. **In practice, the user filled in the CSV `direction` columns using Bronze/Silver/Gold labels directly (not right/away/left), so the `direction` column is effectively the `age` column.** In code, treat `direction` as `age` (rename on load).

### 1.6 Starting Resources
✅ **Starting resources determined by Resource Tile orientation.** Each player: take **2 Resources** matching the quadrant of the Resource Tile **to your left**, and **1 Resource** matching the quadrant **opposite you**. Setup is randomized (random board orientation, random Player Board assignment) so starting resources vary each game.
✅ **Random Player Board** assigned to each player. Player Boards are parallel in function but each has different specific Structure abilities and Milking Parlour layouts.

---

## Section 2: Turn Structure

### 2.1 Simultaneous Action Resolution
✅ **Actions are simultaneous in the real game, but each player operates exclusively within their own quadrant — no shared spaces exist between players.** No spot contention can occur mid-turn. **Simulation impact: model turns sequentially (player 1 then player 2, or randomized order per round). Outcomes are identical either way. No special simultaneous-resolution logic needed.**
✅ **Spot contention does not exist** — each player's quadrant is private to them.
✅ **Rare deadlock rule:** In the highly unlikely case that 2+ players refuse to act until they see each other's action first, those players take turns clockwise from the player facing the Structure quadrant of the Resource Tile. The developer note states this was never needed in hundreds of playtests. **Simulation impact: ignore this rule entirely.**
❓ **Can a player pass entirely?** The rulebook says players "may" perform each action, implying both are optional. What happens if a player has no legal actions at all (e.g., no Workers available AND no cheese spaces accessible)? Assumed they simply skip their turn — confirm.

### 2.2 The Two Actions
✅ **Both actions are optional.** The rulebook uses "may" — players may perform ONE Gather Resources AND ONE Make Cheese, in either order. A player can skip either or both.
✅ **No rule for a third or bonus action** (as a standard game action). The Barn Structure ability lets a Worker placed there not count as Gather Resources — so you *can* effectively use all 3 Workers in 1 turn (1 on Barn for resources, 1 to Gather Resources, 1 to Make Cheese), but this is still mechanically 2 declared actions.

### 2.3 Gather Resources Action
✅ **One spot per turn on the Resource Tile.** The Resource Tile quadrant facing you has 3 numbered spaces (1, 2, 3). You place your Worker on one space and immediately take that many resources of the corresponding type.
✅ **One resource type per Gather action** (whichever type the facing Resource Tile quadrant provides). You pick the quantity (1, 2, or 3) but not the type.
✅ **Self-blocking only.** If your own Worker is still on a space (not yet returned), you cannot use that space. Opponent Workers are never in your quadrant. The "spaces 1, 2, 3" are per-player — they are on the Resource Tile quadrant *facing* you, not shared.
✅ **You may use acquired resources on the same turn you gained them.**

### 2.4 Make Cheese Action
✅ **Sequence: (1) place Cheese Token on empty cheese space in your current quadrant, (2) place your matching Worker Type on top.** No resource payment beyond Fruit for fruited/jam spaces.
✅ **Cheese Token stays on board permanently.** It is NOT retrieved at end of aging — it scores at game-end. Only the Worker is retrieved.
✅ **"Aging" = how long the Worker is tied up.** Bronze space = Worker returns after 1 rotation. Silver = 2. Gold = 3. The Cheese Token is considered "aged" at all times for scoring purposes (the rulebook clarifies: "All Cheese Tokens on the Board count, regardless of if they have fully aged or not").
✅ **No separate aging counter needed.** The Worker's board position (which quadrant it points toward) tracks when it will return. This is elegantly handled by the rotation mechanic.

### 2.5 Worker Recovery
✅ **Workers return at the START of the turn when their quadrant is facing the player.** When the board rotates to bring a Worker's quadrant face-to-face with its owner, that Worker is retrieved and becomes available for that same turn.
✅ **Bronze/Silver/Gold are fixed properties of each cheese space**, not player choice. The space determines how long the Worker is away. For resource spaces (on the Resource Tile), the player chooses the 1/2/3 spot, which determines Worker return time (1/2/3 turns respectively).
✅ **Workers stuck on the board at game-end are simply removed.** They do not score or penalize. All Cheese Tokens count regardless.

### 2.6 Game-End Trigger
✅ **Triggered when a player places their final (15th) Cheese Token and declares it.** All players finish the current turn, then the game ends.
✅ **Multiple players can trigger on the same turn** — all finish the turn, then game ends.
✅ **No turn limit** mentioned as a backup. In practice the game always ends via Cheese Token exhaustion.

---

## Section 3: The Four Quadrants

> **Important clarification from rulebook**: The board has two separate rotating components. (1) The **4 Board Quadrants** (Festival, Fromagerie, Bistro, Villes) — each player faces one venue and makes cheese there. (2) The central **Resource Tile** — each player faces one quadrant of it and gathers that type of resource. Both rotate together 90° clockwise each turn. A player's venue and their resource type both change each turn.

### 3.1 The Festival
✅ **Resources gathered**: Determined by whichever Resource Tile quadrant faces the player when Festival is facing them (varies by setup orientation). Resource type is not venue-specific.
✅ **Scoring rule**: Score points for **orthogonally adjacent Cheese Tokens**. Diagonal adjacency does not count. Free Sample spaces (printed on board) count as containing ALL players' Cheese Tokens — they provide adjacency to everyone. At game-end, count each group of adjacent tokens and consult the scoring rubric on the board.
  - Bronze cheese spaces are adjacent to 0 tokens on the board itself (they only score if next to your own tokens or Free Sample spaces)
  - Silver spaces are adjacent to 1 printed cheese token
  - Gold spaces are adjacent to 2 printed cheese tokens
  - You can score multiple separate groups.
✅ **Full Festival scoring rubric** (confirmed from physical board):
  | Group size | 1 | 2 | 3 | 4 | 5 | 6  | 7  | 8+ |
  |---|---|---|---|---|---|----|----|-----|
  | Points     | 0 | 2 | 4 | 6 | 9 | 12 | 15 | +5 per additional token |
✅ **Festival cheese space layout fully specified** in `data/festival_spaces.csv`. 18 cheese spaces + 6 free_sample spaces in a 5×5 grid. Corners (1,1), (1,5), (3,1), (3,3), (3,5), (5,1), (5,5) are free_sample.

### 3.2 The Villes
✅ **Scoring rule**: The Villes map is divided into **6 regions**. Each cheese space you place tokens in "influences" regions it physically touches: Bronze spaces influence 1 region, Silver spaces influence 2 regions, Gold spaces influence 3 regions. At game-end, the player with the **most influence in each region** takes that region's Customer Token. Customer Token values vary by player count (printed on board/tokens).
✅ **Tie rule**: If tied for most influence, flip the token to its tied (=) side. Tied players score the indicated tie value. **In 1–2 player games, ties are worth 0 points.**
✅ **6 Customer Tokens** in the game (one per region presumably, or distributed at setup).
✅ **Customer Token values fully confirmed** in `data/customer_tokens.csv`. 6 regions with win/tie values at 4 players:
  | Region  | Win | Tie |
  |---------|-----|-----|
  | Purple  |  7  |  3  |
  | Blue    |  7  |  3  |
  | Green   |  8  |  3  |
  | White   |  9  |  3  |
  | Yellow  |  9  |  3  |
  | Pink    |  8  |  3  |
  **Note**: Customer Tokens are normally randomly distributed at game start. For this project, **token placement is fixed to the arrangement in the CSV** — no random setup of tokens needed in simulation.
✅ **Villes fully specified** in `data/villes_spaces.csv`. 18 spaces across 6 regions (purple, blue, green, white, yellow, pink). All 18 cities confirmed: Toulouse, Caylus, Montpellier, Nantes, Rennes, Tours, Orleans, Limoges, Chavignol, Laguiole, Paris, Troyes, Lille, Dijon, Lyon, Grenoble, Point-L'Eveque, Strasbourg.

### 3.3 The Fromagerie
✅ **Scoring rule**: The Fromagerie has multiple **shelves**, each with a Display Sign showing a bonus. Shelves for higher-aged cheeses (Silver, Gold) offer more valuable bonuses.
  - **Immediate bonuses** (triggered when placing Cheese Token on certain shelves):
    - **≠** icon: Gain 2 **different** Resources immediately
    - **□** icon: Gain 1 Resource of any type immediately
    - **≠×** icon: Discard an unused Resource → gain 1 Resource of any type
  - **End-game scoring**: Count the number of **different shelves** that have your Cheese Tokens and consult the rubric on the board. Additionally, for each token on a shelf that has a **point bonus** (separate from resource bonuses), add those points.
✅ **Full Fromagerie scoring rubric** (confirmed from physical board):
  | Shelves occupied | 1 | 2 | 3 | 4 | 5  | 6  |
  |---|---|---|---|---|----|----|
  | Base points      | 0 | 2 | 5 | 9 | 14 | 20 |
✅ **6 shelves total confirmed.** 2 columns (resource bonus column left, point bonus column right) × 3 rows (Bronze/Silver/Gold). **All 6 shelves contain Soft, Hard, and Bleu spaces.**
✅ **Shelf immediate bonuses confirmed** (resource bonus column):
  - Bronze shelf: trade any resource for 1 of another type (≠× icon)
  - Silver shelf: gain 1 Resource of any type (□ icon)
  - Gold shelf: gain 2 **different** Resources (≠ icon)
✅ **Shelf point bonuses confirmed** (point bonus column): +1 PP/token (Bronze), +2 PP/token (Silver), +3 PP/token (Gold)
✅ **Fromagerie space layout fully specified** in `data/fromagerie_spaces.csv`. 18 spaces across 6 shelves (3 cheese types per shelf). Fruit and Jam flags confirmed for each space.

### 3.4 The Bistro
✅ **Scoring rule**: The Bistro has **tables**, each with multiple plates (Bronze, Silver, Gold). Score points for each plate that has your Cheese Token. **Make pairings** by having 2 of your Cheese Tokens on the same table. At game-end, the total number of pairings you made determines how many points each plate is worth (consult the rubric on the board).
  - **Confirmed row** (1 pairing): Bronze plate = 1 pt, Silver = 3 pts, Gold = 5 pts. Example: 1B + 2S + 1G with 1 pairing = 1+3+3+5 = 12 pts.
  - More pairings = higher points per plate (scaling rubric). The scoring table is visible on the board and has **4 rows** (1, 2, 3, 4 pairings), each with values for Bronze, Silver, and Gold plates.
✅ **9 tables × 2 plates = 18 total spaces.** (Earlier estimate of 6×3 was incorrect — physical board confirmed 9 tables each with 2 plates, not 3.)
✅ **Bistro scoring rule clarified**: (1) Count how many tables you control (tables where you filled both plates = pairings). (2) Look up pairings count in the rubric to get per-plate point values. (3) Count all plates of each age across ALL your tables (not just controlled ones). (4) Multiply and sum.
✅ **Full Bistro scoring rubric confirmed** in `data/scoring_bistro.csv`:
  | Pairings | Bronze | Silver | Gold |
  |----------|--------|--------|------|
  | 0        |   0    |   2    |   4  |
  | 1        |   1    |   3    |   5  |
  | 2        |   2    |   4    |   6  |
  | 3+       |   3    |   6    |   9  |
✅ **Bistro space layout fully specified** in `data/bistro_spaces.csv`. Each table has exactly 2 plates; no table has all 3 age tiers. Cheese types and fruit/jam flags confirmed.

### 3.5 Quadrant Rotation Interaction
✅ **Workers placed on cheese spaces rotate with the board.** They do not stay in absolute position — they move with the quadrant they are on. This is how the aging/return mechanic works.
✅ **Players can ONLY interact with the quadrant currently facing them.** You cannot reach another player's quadrant or a non-facing venue.

---

## Section 4: Scoring

### 4.1 When Does Scoring Happen?
✅ **Most scoring is at game-end only.** Venues (Festival, Villes, Fromagerie end-game rubric, Bistro), Fruit, Orders, and unused Resources are all calculated at game-end.
✅ **Two types of immediate scoring/benefits during play:**
  - **Fromagerie Display Sign resource bonuses**: immediately gain the resource shown when placing a Cheese Token on that shelf.
  - **Order completion**: immediately "complete" the Order Card (move to right of Player Board) when you place a matching Cheese Token — this happens during the turn, but the actual point value is counted at game-end.
  - **Loading Dock Structure ability**: immediately gain a resource when placing in Villes.
  - **Greenhouse Structure ability**: immediately gain bonus resource when gaining the shown type.

### 4.2 Venue Score Breakdown
✅ **All 4 venues are scored at game-end for every player** (you score whatever cheese you placed at each venue, regardless of how much you engaged).
✅ **Additional end-game scores:**
  - **Fruit**: (# Fruit tokens spent on Fruited Cheese spaces) × (# Fruit tokens spent on Jam spaces)
  - **Orders**: consult the rubric (scaling — example: 4 Orders = 5 pts)
  - **Structures (Headquarters ability)**: 1 PP per shown Resource type used
  - **Unused Resources**: 1 PP per 2 unused Resources of any type (rounded down)

### 4.3 Tiebreaker
✅ **Tiebreaker 1**: Player who made more cheese (placed more Cheese Tokens) wins.
✅ **Tiebreaker 2**: If still tied, victory is shared.

### 4.4 Point Tracking
✅ **Points are totaled only at game-end.** No score track is used during play. Players tally all sources after the final turn.

---

## Section 5: Special Rules & Edge Cases

### 5.1 Cheese Uniqueness
✅ **No "unique" mechanic.** Multiple Cheese Tokens of the same type can be placed at the same venue. The only constraint is that a cheese space must be empty before you can place a token there.

### 5.2 Resource Limits
✅ **Resources are effectively unlimited in supply** (shared trays; use x3/x5 tokens if exhausted).
✅ **No per-player resource holding limit.** No cap is mentioned in the rulebook and no physical limit exists on the Player Board. Resources are unbounded per player. Simulation note: represent all resource counts as plain integers with no upper bound.

### 5.3 Blocking
✅ **Blocking is not a mechanic.** Each player operates only in their own quadrant. The only blocking constraint is your own unrecovered Workers occupying spaces in your own quadrant.

### 5.4 Player Interaction
✅ **The only meaningful inter-player interaction is competing for Customer Tokens in Villes** (most influence per region). Everything else is completely independent.
✅ **No trading, stealing, card targeting, or any other direct interaction.**

### 5.5 Cheese Token Exhaustion (Non-End-Trigger)
✅ **Placing your last Cheese Token triggers game-end.** You cannot run out without triggering it — there is no "out of tokens but game continues" scenario (you declare game-end at the moment you place the final token).

### 5.6 Livestock / Milking Parlours (Bonus Cheese)
✅ **Milking Parlour** mechanic: At any time during your turn, move the required number of Livestock from your pasture to a Milking Parlour on your Player Board. This lets you immediately place a Bonus Cheese Token on a space matching the Parlour's Bonus Cheese Type and Age — **without using a Worker**.
✅ **Can be used in the same turn as the Make Cheese action** — you can place one Worker cheese AND one (or more) Milking Parlour cheeses in the same turn.
✅ **Can use multiple Milking Parlours per turn** (each Parlour can be used once per game, not once per turn — need to confirm this).
✅ **If the Milking Parlour targets a Fruited Cheese or Jam space, Fruit must still be used.**
✅ **Bonus Cheese from Milking Parlours CAN complete Orders.**
✅ **Each Player Board has exactly 4 Milking Parlours.** Livestock costs: 2, 3, 4, 5. The 4th Parlour (cost 5) on every board is **wild** — any cheese type and any age.
✅ **Milking Parlour bonus cheese fully specified** in `data/milking_parlours.csv`.

### 5.7 Structure Abilities
✅ **Each Player Board has 4 Structure abilities.** Each slot has the same *function category* across all boards, but the specific resource type (slot 1 and 3) and specific venue/condition (slots 2 and 4) differ per board. Fully specified in `data/player_board_structures.csv`.

✅ **The 4 structure slot functions:**
  1. **Barn** (slot 1): Place a Worker here to gain the shown Resource. Retrieve Worker at start of next turn. Does NOT count as a Gather Resources action.
  2. **Loading Dock** (slot 2): When placing a Cheese Token at a specific venue (different per board), immediately gain 1 of the shown Resource. Includes Bonus Cheese from Milking Parlours.
  3. **Greenhouse** (slot 3): When gaining the shown Resource type, gain 1 additional of that type. Max 1 trigger per turn.
  4. **Headquarters** (slot 4): End-game bonus — 1 PP per unit of a specific condition (different per board).

✅ **Per-board structure details** (confirmed from `data/player_board_structures.csv`):
  | Board | Slot 1 Barn resource | Slot 2 Loading Dock trigger | Slot 3 Greenhouse resource | Slot 4 HQ condition |
  |-------|---------------------|-----------------------------|----------------------------|---------------------|
  | 1     | Livestock (Animal)  | Fromagerie → gain Order     | Fruit                      | +1 PP per deployed Structure |
  | 2     | Structure           | Festival → gain Livestock   | Order                      | +1 PP per Fruit/Jam spent |
  | 3     | Fruit               | Villes → gain Structure     | Livestock (Animal)         | +1 PP per completed Order |
  | 4     | Order               | Bistro → gain Fruit         | Structure                  | +1 PP per Livestock in Parlour |

  **Design note**: Each board specialises in a different venue trigger (Fromagerie/Festival/Villes/Bistro), creating natural strategic differentiation between boards. Slot 2 reward type rotates so every resource type appears once across the 4 boards.

### 5.8 Structure Tiles (Advanced Mode)
✅ **OUT OF SCOPE FOR THIS PROJECT.** Structure Tiles are an advanced variant mode and will not be implemented at any phase of Fromage-ML. The base game's 4 printed Structure abilities per Player Board are the only abilities in scope. Simulation note: all Player Boards use their printed abilities only.

### 5.9 Orders
✅ **Orders are Order Cards** with 2 requirements: Cheese Type (Soft/Hard/Bleu) and Age (Bronze/Silver/Gold).
✅ **When you place a Cheese Token matching the requirements, you may immediately complete the Order** (place it to right of Player Board). Only 1 Order can be completed per Cheese Token.
✅ **Cannot retroactively complete** — must draw the card before making the matching cheese.
✅ **36 Order Cards** in the game.
✅ **Full Order scoring rubric confirmed** in `data/order_scoring.csv`:
  | Orders completed | 1 | 2 | 3 | 4 | 5  | 6  | 7+ |
  |---|---|---|---|---|----|----|-----|
  | Points           | 1 | 3 | 5 | 8 | 11 | 14 | +4 per additional |
✅ **Order Card distribution confirmed**: 4 cards per combination of (Cheese Type × Age) = 3 types × 3 ages × 4 = **36 cards total.** Distribution is perfectly uniform — no CSV needed. Simulation note: shuffle all 36 at start; draw from deck as players acquire Orders.

---

## Section 6: AI & Simulation Design Questions

### 6.1 State Representation
✅ **Draft GameState schema** (to be refined once ❓ items in Sections 1–5 are resolved):

```
GameState:
  rotation_index: int          # 0-3, which quadrant faces which player
  turn_number: int
  game_end_triggered: bool

  players: list[PlayerState]   # one per player (2-4)

PlayerState:
  resources:
    structures: int
    livestock: int
    fruit: int
    orders_held: int           # raw Order tokens held (before drawing cards)

  order_cards: list[OrderCard] # active (incomplete) orders
  completed_orders: list[OrderCard]

  cheese_tokens_remaining: int # starts at 15
  cheese_tokens_on_board: list[CheeseToken]
    # each: venue, space_id, type (Soft/Hard/Bleu), age (Bronze/Silver/Gold)

  workers: list[Worker]        # 3 workers
    # each: type (Soft/Hard/Bleu), location (in_hand | on_board),
    #       board_position (venue, space_id) if on_board

  structures_unlocked: list[StructureAbility]
  milking_parlours_used: list[bool]  # one per parlour, reset each game

  fruit_used_for_fruited: int  # tracking for end-game Fruit scoring
  fruit_used_for_jam: int

  # Opponent-visible summary (for AI state encoding):
  # cheese_tokens_placed: int (derived), workers_on_board: int (derived)

GlobalState:
  villes_customer_tokens: list[CustomerToken]  # which player holds each
  resource_tile_orientation: int               # which quadrant provides which resource
  order_card_deck: list[OrderCard]             # remaining deck
```

### 6.2 Action Space
✅ **Estimated maximum legal actions per turn** (before Structures/Milking Parlours):
  - Gather Resources: 3 choices (1, 2, or 3 resources) + skip = **4 options**
  - Make Cheese: up to ~6–8 available cheese spaces per venue (varies) + skip = **~7–9 options**
  - Combined (both are independent): ~28–36 combinations
  - Plus Milking Parlour uses (if Livestock held): small additional set
  - **Total estimated action space per turn: ~30–50 discrete actions.** This is small and well-suited to Q-learning without approximation.

### 6.3 Player Count for Training
✅ **Always train at 4 players** — fixed by project scope decision. All simulation runs use exactly 4 agents.

### 6.4 AI Approach
✅ **Q-learning is the right choice.** Each player operates in their own quadrant — the action space is fully independent per player per turn. No simultaneous-decision problem exists. Q-learning converges well on action spaces of ~30–50 options and will be interpretable (we can inspect the Q-table to understand which moves it values).
- **State encoding**: flatten `PlayerState` + key opponent-visible fields into a fixed-length vector for the Q-table/function approximator.
- **Opponent modeling note**: Include opponent's `cheese_tokens_remaining` and `cheese_tokens_on_board` count in the state vector. The most important opponent signal is "how close is the game to ending?"
- **Revisit trigger**: If post-training analysis shows the AI ignores Villes competition (e.g., never contests Customer Tokens), add more opponent Villes-state features before escalating to MCTS.

### 6.5 Evaluation Metric
✅ **Primary metric: win rate** over N simulated games after training. Simple to compute and directly corresponds to the goal.
✅ **Secondary metric: average Prestige Point delta** vs. random agent. Useful for measuring improvement during training even when win rate is noisy.
- Regret minimization is theoretically cleanest but adds implementation overhead — skip for Phase 1 AI.

---

## Research Completion Checklist

Before writing `2-requirements.md`, all items below must be checked off:

- [x] **Section 1 mostly answered** — ❓ remaining: exact ⊘ space counts per player count; Player Board resource cap; cheese space counts per quadrant
- [x] **Section 2 mostly answered** — ❓ remaining: pass/no-legal-actions edge case
- [ ] **Section 3 — open** — Exact scoring rubrics and cheese space layouts needed for ALL 4 venues (Festival, Villes, Fromagerie, Bistro)
- [x] **Section 4 fully answered** — Scoring mechanics complete
- [x] **Section 5 mostly answered** — ❓ remaining: Milking Parlour details per board; Structure ability resource types per board; Order Card distribution; Order scoring rubric; per-player resource cap
- [x] **Section 6 design decisions documented** — AI & Simulation approach settled

---

## Remaining Open Questions Summary

These are the items that require inspecting the **physical board or components**. All other questions are resolved. Structure Tiles are out of scope and removed from this list.

All items now closed. ✅

| # | Item | Status |
|---|---|---|
| ~~1~~ | ~~⊘-blocked space locations~~ | **CLOSED** — always 4 players |
| ~~2~~ | ~~Per-player resource holding cap~~ | **CLOSED** — no limit |
| ~~3~~ | ~~Cheese space layouts (all venues)~~ | **CLOSED** ✅ — all 4 venue CSVs complete |
| ~~4~~ | ~~Festival scoring rubric~~ | **CLOSED** ✅ — `scoring_festival.csv` |
| ~~5~~ | ~~Customer Token values~~ | **CLOSED** ✅ — `customer_tokens.csv`; arrangement fixed (not random) |
| ~~6~~ | ~~Fromagerie scoring rubric + shelf bonuses~~ | **CLOSED** ✅ — `scoring_fromagerie.csv`, `fromagerie_shelves.csv` |
| ~~7~~ | ~~Bistro scoring rubric~~ | **CLOSED** ✅ — `scoring_bistro.csv`; table count corrected to 9×2 |
| ~~8~~ | ~~Milking Parlour bonus cheese per board~~ | **CLOSED** ✅ — `milking_parlours.csv`; parlour 4 is wild (any type/age) |
| ~~9~~ | ~~Structure ability details per board~~ | **CLOSED** ✅ — `player_board_structures.csv`; each board targets different venue |
| ~~10~~ | ~~Order scoring rubric~~ | **CLOSED** ✅ — `order_scoring.csv` |
| ~~11~~ | ~~Order Card distribution~~ | **CLOSED** ✅ — 4 per (type × age), 36 total; no CSV needed |

---

## Notes & Answers (Session Log)

**2026-03-23**: Initial research goals created. All questions open.

**2026-03-23**: Clarified simultaneous-turn architecture — each player has their own quadrant, no spot contention. Q-learning confirmed, MCTS unnecessary.

**2026-03-23**: Full rulebook (Fromage_Rulebook_20231208.pdf) reviewed. Major findings:
- Resources are Structures / Livestock / Fruit / Orders (not milk/rennet/etc. — more abstract than expected)
- Workers ARE the cheese-type designators (Soft/Hard/Bleu worker = Soft/Hard/Bleu cheese)
- "Aging" is just worker recovery time — no separate aging counter, the board rotation handles it elegantly
- Making cheese has NO resource cost except Fruit for fruited/jam spaces
- Cheese Tokens are permanent on board — only Workers return
- Livestock creates Bonus Cheese placements (Milking Parlours) without using a Worker — this is a significant parallel action system
- Structures give meaningful abilities that modify rules (Barn skips Gather action cost, Greenhouse gives bonus resources, etc.)
- Fruit scoring is multiplicative: (fruited cheese count) × (jam count) — creates interesting combo potential
- All 4 venues score at game-end; only Fromagerie shelf bonuses and Order completion are mid-game
- ~11 items still need physical component inspection (see table above)

---

**2026-03-23** (second pass): Venue board image and Player Board image reviewed. Updates:
- Structure Tiles confirmed **out of scope for the entire project** (user decision)
- Milking Parlour count confirmed: **4 per board**; Livestock costs confirmed: **2, 3, 4, 5**
- Fromagerie partial rubric: 3 shelves = 5 pts; bottom-right shelf = +1 pt/token confirmed
- Festival partial rubric: group of 2 = 2 pts, group of 4 = 6 pts confirmed
- Bistro: 1-pairing row confirmed (B=1, S=3, G=5); **4-row table** structure confirmed
- Villes: 4 of 6 Customer Token values partially visible (3, 4, 4, 5 at one player count)
- Order rubric: non-linear track confirmed; 4-order=5pt data point confirmed
- Reduced from 11 to **11 items** (same count, but 4 items now have partial data closing half the uncertainty)

**2026-03-24** (third pass): Physical board photos reviewed. Major confirmations:
- Festival full scoring rubric confirmed: 0/2/4/6/9/12/15/+5 ✅ → `scoring_festival.csv` complete
- Fromagerie full scoring rubric confirmed: 0/2/5/9/14/20 ✅ → `scoring_fromagerie.csv` complete
- Fromagerie shelf structure confirmed: all 6 shelves have Soft/Hard/Bleu; resource column bonuses (Bronze=trade, Silver=1any, Gold=2diff); point column (+1/+2/+3 PP per token) ✅ → `fromagerie_shelves.csv` complete
- Bistro 6 tables confirmed (18 spaces total) ✅
- Villes 18 spaces confirmed; 16 of 18 city names identified ✅
- Festival 18 spaces in 5×5 grid + Free Sample spaces confirmed ✅
- Side 1 of 4-player insert only ✅
- 13 CSV data files created in `data/` directory. Remaining open items now tracked in CSVs for user to fill in directly.

**2026-03-24** (fourth pass): All CSVs filled in by user from physical components. All research items now closed.
- Bistro table count corrected: **9 tables × 2 plates** (not 6 × 3 as previously estimated)
- Bistro scoring rubric complete: 0/1/2/3+ pairings → B(0/1/2/3), S(2/3/4/6), G(4/5/6/9)
- Customer tokens fixed arrangement confirmed; all 6 values known (7/7/8/9/9/8 win, all tie=3)
- Order scoring complete: 1/2/3/4/5/6/7+ → 1/3/5/8/11/14/+4
- Order cards: uniform distribution confirmed (4 per type×age combination)
- Structure abilities corrected: slot 2 (Loading Dock) triggers at different venue per board; slot 4 (HQ) has unique end-game condition per board
- Milking Parlour 4 on every board is wild (any type, any age)
- Direction column in CSVs uses age labels (Bronze/Silver/Gold) directly

*Last updated: 2026-03-24 — All research items closed. Ready to write `2-requirements.md` and `3-milestones.md`.*
