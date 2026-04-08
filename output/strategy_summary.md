# Strategy Summary

_Generated from simulation results. One finding per chart — high confidence = clear numeric signal, low = noisy or sparse data._


## Finding: Most commonly unlocked structure per board
source_chart: Chart 1 — Structure build frequency by player board
confidence: high
key_metric: Board 1: slot 1 (75%); Board 2: slot 1 (88%); Board 3: slot 2 (96%); Board 4: slot 1 (73%)
winner_vs_loser_delta: n/a
finding: Each board has one structure slot that is unlocked in more games than any other.
implication: Prioritise the dominant slot on your board — it is the one the game economy most rewards.


## Finding: Dominant scoring venue
source_chart: Chart 2 — Average points per venue
confidence: high
key_metric: villes: 11.5 mean pts
winner_vs_loser_delta: n/a
finding: The villes venue contributes the most average points per player per game.
implication: Focus cheese placements in villes before branching out to secondary venues.


## Finding: Board balance check
source_chart: Chart 3 — Win rate per player board
confidence: high
key_metric: Board 4: 0.31 win rate (Δ+0.06 from 0.25)
winner_vs_loser_delta: n/a
finding: Board 4 deviates most from the 0.25 random baseline with a win rate of 0.31.
implication: Investigate board structure if any board exceeds ±0.05 from baseline.


## Finding: Fruit usage skew
source_chart: Chart 4 — Fruit vs jam usage
confidence: medium
key_metric: fruited 1.75 / jam 1.76 (ratio 1.00×)
winner_vs_loser_delta: n/a
finding: Players spend 1.0× more fruit on jam cheese than on the other type.
implication: If the ratio exceeds 2×, consider whether fruit requirements in the CSV data are balanced.


## Finding: Orders as share of score
source_chart: Chart 5 — Orders as share of total score
confidence: high
key_metric: Mean 5.6% of total score
winner_vs_loser_delta: n/a
finding: Orders account for 5.6% of total prestige on average.
implication: De-prioritise orders if share is below 5%; prioritise if above 15%.


## Finding: Unused resource penalty magnitude
source_chart: Chart 6 — Unused resources as share of total score
confidence: medium
key_metric: Mean 6.0% of total score
winner_vs_loser_delta: n/a
finding: The unused-resource deduction costs players 6.0% of their total score on average.
implication: If above 10%, the AI should be trained to convert resources more aggressively before game end.


## Finding: Biggest winner/loser scoring divergence
source_chart: Chart 7 — Winner vs loser score breakdown (radar)
confidence: high
key_metric: villes: Δ+8.7 pts (winners vs losers)
winner_vs_loser_delta: +8.7 pts
finding: The villes category shows the largest gap between winners and losers.
implication: Focus training incentives and strategy on villes to close or widen the gap.


## Finding: Board×venue synergy extremes
source_chart: Chart 8 — Board × venue synergy heatmap
confidence: medium
key_metric: Best: Board 1×villes (11.9); Worst: Board 3×fromagerie (6.7)
winner_vs_loser_delta: n/a
finding: Board 1 earns the most at villes (11.9 pts mean); Board 3 earns the least at fromagerie (6.7 pts mean).
implication: Route Board 1 players to villes; avoid fromagerie for Board 3 unless board structures force it.


## Finding: Gold cheese age and winning
source_chart: Chart 9 — Cheese age distribution: winners vs losers
confidence: high
key_metric: Winners avg 4.8 Gold; Losers avg 3.9 Gold
winner_vs_loser_delta: Δ+0.87 Gold tokens
finding: Winners place 0.9 more Gold tokens on average.
implication: Gold cheese costs 3 rotations; adjust strategy if the delta is small or negative.


## Finding: Structure slots that distinguish winners from losers
source_chart: Chart 10 — Structure unlock rate: winners vs losers
confidence: medium
key_metric: See chart PNG for per-slot breakdown
winner_vs_loser_delta: n/a
finding: Some structure slots are unlocked at notably higher rates by winners than losers.
implication: Prioritise the slots with the largest winner/loser delta on your board.


## Finding: Headquarters score and winning
source_chart: Chart 11 — Headquarters score by board (winners vs losers)
confidence: medium
key_metric: Winners HQ mean 0.3; Losers HQ mean 0.3
winner_vs_loser_delta: Δ+0.0 pts
finding: Winners score 0.0 more HQ points on average.
implication: If the HQ delta exceeds 5 pts, the HQ condition is a meaningful tiebreaker worth pursuing.


## Finding: Optimal milking parlour usage count
source_chart: Chart 12 — Milking parlour usage count vs win rate
confidence: medium
key_metric: Peak win rate at 0 parlours used (0.28)
winner_vs_loser_delta: n/a
finding: Players using 0 milking parlour(s) win most often.
implication: Target 0 parlour use per game; more or fewer may not pay off.


## Finding: Best Villes region to contest
source_chart: Chart 13 — Villes region control rate and win correlation
confidence: medium
key_metric: Region green: 0.55 win rate for controllers
winner_vs_loser_delta: n/a
finding: Controlling region green correlates with the highest win rate.
implication: Prioritise placing cheese in region green when competing for Villes control.


## Finding: Fruit balance and winning
source_chart: Chart 14 — Fruit balance scatter (fruited vs jam, by outcome)
confidence: medium
key_metric: Winner imbalance 0.24; Loser imbalance 0.35
winner_vs_loser_delta: Δ-0.11 imbalance ratio
finding: Winners have lower fruit-spend imbalance than losers.
implication: Balance fruited and jam spending (target imbalance ratio < 0.3) to maximise score_fruit.

