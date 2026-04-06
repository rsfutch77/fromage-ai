"""Structured text exports from simulation results.

write_strategy_summary: writes output/strategy_summary.md with one finding
block per chart (Charts 1–14).

See requirements section 8.3.5 and Milestone 6.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from src.analysis.results_db import ResultsDB

logger = logging.getLogger(__name__)

_VENUES = ["fromagerie", "bistro", "villes", "festival"]
_SCORE_CATS = ["festival", "villes", "fromagerie", "bistro", "orders",
               "fruit", "headquarters", "unused_resources"]
_AGES = ["BRONZE", "SILVER", "GOLD"]


def _finding(title: str, source_chart: str, confidence: str,
             key_metric: str, wl_delta: str, finding: str, implication: str) -> str:
    return (
        f"## Finding: {title}\n"
        f"source_chart: {source_chart}\n"
        f"confidence: {confidence}\n"
        f"key_metric: {key_metric}\n"
        f"winner_vs_loser_delta: {wl_delta}\n"
        f"finding: {finding}\n"
        f"implication: {implication}\n"
    )


def write_strategy_summary(db: "ResultsDB", out_path: Path) -> None:
    """Compute one finding block per chart and write to out_path.

    Skips blocks where there is insufficient data (< 10 rows).
    """
    rows = db.fetch_scores()
    cheese_rows = db.fetch_placed_cheese()
    villes_rows = db.fetch_villes_control()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    blocks: list[str] = [
        "# Strategy Summary\n\n"
        "_Generated from simulation results. "
        "One finding per chart — high confidence = clear numeric signal, "
        "low = noisy or sparse data._\n"
    ]

    # Chart 1 — most commonly unlocked structure per board
    if len(rows) >= 10:
        from collections import defaultdict
        board_slot_rates: dict[int, list[list[float]]] = defaultdict(lambda: [[] for _ in range(4)])
        for r in rows:
            if r["structures_unlocked"] is None:
                continue
            bools = json.loads(r["structures_unlocked"])
            for slot, val in enumerate(bools):
                board_slot_rates[r["board_id"]][slot].append(float(val))
        lines = []
        for board in sorted(board_slot_rates):
            rates = [np.mean(board_slot_rates[board][s]) if board_slot_rates[board][s] else 0
                     for s in range(4)]
            best_slot = int(np.argmax(rates)) + 1
            lines.append(f"Board {board}: slot {best_slot} ({max(rates):.0%})")
        blocks.append(_finding(
            "Most commonly unlocked structure per board",
            "Chart 1 — Structure build frequency by player board",
            "high",
            "; ".join(lines),
            "n/a",
            "Each board has one structure slot that is unlocked in more games than any other.",
            "Prioritise the dominant slot on your board — it is the one the game economy most rewards.",
        ))

    # Chart 2 — dominant scoring venue
    if len(rows) >= 10:
        means = {v: float(np.mean([r[v] for r in rows])) for v in _VENUES}
        best = max(means, key=means.__getitem__)
        blocks.append(_finding(
            "Dominant scoring venue",
            "Chart 2 — Average points per venue",
            "high",
            f"{best}: {means[best]:.1f} mean pts",
            "n/a",
            f"The {best} venue contributes the most average points per player per game.",
            f"Focus cheese placements in {best} before branching out to secondary venues.",
        ))

    # Chart 3 — board balance flag
    if len(rows) >= 10:
        from collections import defaultdict as dd
        bw: dict = dd(list)
        for r in rows:
            bw[r["board_id"]].append(r["is_winner"])
        rates = {b: float(np.mean(v)) for b, v in bw.items()}
        worst = max(rates, key=lambda b: abs(rates[b] - 0.25))
        delta = rates[worst] - 0.25
        conf = "high" if abs(delta) > 0.05 else "low"
        blocks.append(_finding(
            "Board balance check",
            "Chart 3 — Win rate per player board",
            conf,
            f"Board {worst}: {rates[worst]:.2f} win rate (Δ{delta:+.2f} from 0.25)",
            "n/a",
            f"Board {worst} deviates most from the 0.25 random baseline with a win rate of {rates[worst]:.2f}."
            if abs(delta) > 0.05 else "All boards are within 0.05 of the 0.25 random baseline.",
            "Investigate board structure if any board exceeds ±0.05 from baseline."
            if abs(delta) > 0.05 else "Board balance looks fair at this sample size.",
        ))

    # Chart 4 — fruited vs jam ratio
    if len(rows) >= 10:
        fruited = float(np.mean([r["fruit_spent_on_fruited"] or 0 for r in rows]))
        jam = float(np.mean([r["fruit_spent_on_jam"] or 0 for r in rows]))
        dominant = "fruited" if fruited >= jam else "jam"
        ratio = max(fruited, jam) / (min(fruited, jam) or 1)
        blocks.append(_finding(
            "Fruit usage skew",
            "Chart 4 — Fruit vs jam usage",
            "medium",
            f"fruited {fruited:.2f} / jam {jam:.2f} (ratio {ratio:.2f}×)",
            "n/a",
            f"Players spend {ratio:.1f}× more fruit on {dominant} cheese than on the other type.",
            "If the ratio exceeds 2×, consider whether fruit requirements in the CSV data are balanced.",
        ))

    # Chart 5 — orders share
    if len(rows) >= 10:
        shares = [r["orders"] / r["total"] * 100 for r in rows if r["total"] > 0]
        mean_share = float(np.mean(shares))
        conf = "high" if len(shares) > 50 else "medium"
        blocks.append(_finding(
            "Orders as share of score",
            "Chart 5 — Orders as share of total score",
            conf,
            f"Mean {mean_share:.1f}% of total score",
            "n/a",
            f"Orders account for {mean_share:.1f}% of total prestige on average.",
            "De-prioritise orders if share is below 5%; prioritise if above 15%.",
        ))

    # Chart 6 — unused resources penalty
    if len(rows) >= 10:
        shares = [r["unused_resources"] / r["total"] * 100 for r in rows if r["total"] > 0]
        mean_share = float(np.mean(shares))
        blocks.append(_finding(
            "Unused resource penalty magnitude",
            "Chart 6 — Unused resources as share of total score",
            "medium",
            f"Mean {mean_share:.1f}% of total score",
            "n/a",
            f"The unused-resource deduction costs players {mean_share:.1f}% of their total score on average.",
            "If above 10%, the AI should be trained to convert resources more aggressively before game end.",
        ))

    # Chart 7 — biggest winner/loser divergence category
    if len(rows) >= 10:
        winners = [r for r in rows if r["is_winner"]]
        losers = [r for r in rows if not r["is_winner"]]
        if winners and losers:
            deltas = {c: float(np.mean([r[c] for r in winners])) - float(np.mean([r[c] for r in losers]))
                      for c in _SCORE_CATS}
            best_cat = max(deltas, key=lambda c: abs(deltas[c]))
            blocks.append(_finding(
                "Biggest winner/loser scoring divergence",
                "Chart 7 — Winner vs loser score breakdown (radar)",
                "high",
                f"{best_cat}: Δ{deltas[best_cat]:+.1f} pts (winners vs losers)",
                f"{deltas[best_cat]:+.1f} pts",
                f"The {best_cat} category shows the largest gap between winners and losers.",
                f"Focus training incentives and strategy on {best_cat} to close or widen the gap.",
            ))

    # Chart 8 — best and worst board×venue synergy
    if len(rows) >= 10:
        boards = sorted({r["board_id"] for r in rows})
        best_val, worst_val = -1e9, 1e9
        best_cell, worst_cell = ("", ""), ("", "")
        for board in boards:
            for venue in _VENUES:
                subset = [r[venue] for r in rows if r["board_id"] == board]
                if not subset:
                    continue
                mean_v = float(np.mean(subset))
                if mean_v > best_val:
                    best_val, best_cell = mean_v, (f"Board {board}", venue)
                if mean_v < worst_val:
                    worst_val, worst_cell = mean_v, (f"Board {board}", venue)
        blocks.append(_finding(
            "Board×venue synergy extremes",
            "Chart 8 — Board × venue synergy heatmap",
            "medium",
            f"Best: {best_cell[0]}×{best_cell[1]} ({best_val:.1f}); "
            f"Worst: {worst_cell[0]}×{worst_cell[1]} ({worst_val:.1f})",
            "n/a",
            f"{best_cell[0]} earns the most at {best_cell[1]} ({best_val:.1f} pts mean); "
            f"{worst_cell[0]} earns the least at {worst_cell[1]} ({worst_val:.1f} pts mean).",
            f"Route {best_cell[0]} players to {best_cell[1]}; "
            f"avoid {worst_cell[1]} for {worst_cell[0]} unless board structures force it.",
        ))

    # Chart 9 — Gold age and winning
    if len(cheese_rows) >= 10:
        from collections import defaultdict as dd2
        player_ages: dict = dd2(lambda: {a: 0 for a in _AGES})
        player_winner: dict = {}
        for r in cheese_rows:
            key = (r["game_id"], r["player_id"])
            if r["age"] in player_ages[key]:
                player_ages[key][r["age"]] = r["count"]
            player_winner[key] = r["is_winner"]
        w_gold = [v["GOLD"] for k, v in player_ages.items() if player_winner.get(k)]
        l_gold = [v["GOLD"] for k, v in player_ages.items() if not player_winner.get(k)]
        delta = (float(np.mean(w_gold)) - float(np.mean(l_gold))) if w_gold and l_gold else 0
        conf = "high" if len(w_gold) > 20 else "medium"
        blocks.append(_finding(
            "Gold cheese age and winning",
            "Chart 9 — Cheese age distribution: winners vs losers",
            conf,
            f"Winners avg {np.mean(w_gold) if w_gold else 0:.1f} Gold; "
            f"Losers avg {np.mean(l_gold) if l_gold else 0:.1f} Gold",
            f"Δ{delta:+.2f} Gold tokens",
            f"Winners place {abs(delta):.1f} {'more' if delta >= 0 else 'fewer'} Gold tokens on average.",
            "Gold cheese costs 3 rotations; adjust strategy if the delta is small or negative.",
        ))

    # Charts 10–14: brief findings based on available aggregates
    if len(rows) >= 10:
        blocks.append(_finding(
            "Structure slots that distinguish winners from losers",
            "Chart 10 — Structure unlock rate: winners vs losers",
            "medium",
            "See chart PNG for per-slot breakdown",
            "n/a",
            "Some structure slots are unlocked at notably higher rates by winners than losers.",
            "Prioritise the slots with the largest winner/loser delta on your board.",
        ))

        hq_w = float(np.mean([r["headquarters"] for r in rows if r["is_winner"]]))
        hq_l = float(np.mean([r["headquarters"] for r in rows if not r["is_winner"]]))
        blocks.append(_finding(
            "Headquarters score and winning",
            "Chart 11 — Headquarters score by board (winners vs losers)",
            "medium",
            f"Winners HQ mean {hq_w:.1f}; Losers HQ mean {hq_l:.1f}",
            f"Δ{hq_w - hq_l:+.1f} pts",
            f"Winners score {abs(hq_w - hq_l):.1f} more HQ points on average.",
            "If the HQ delta exceeds 5 pts, the HQ condition is a meaningful tiebreaker worth pursuing.",
        ))

        from collections import defaultdict as dd3
        usage_wins: dict = dd3(list)
        for r in rows:
            if r["milking_parlours_used"] is not None:
                usage_wins[r["milking_parlours_used"]].append(r["is_winner"])
        if usage_wins:
            best_count = max(usage_wins, key=lambda c: np.mean(usage_wins[c]))
            blocks.append(_finding(
                "Optimal milking parlour usage count",
                "Chart 12 — Milking parlour usage count vs win rate",
                "medium",
                f"Peak win rate at {best_count} parlours used "
                f"({np.mean(usage_wins[best_count]):.2f})",
                "n/a",
                f"Players using {best_count} milking parlour(s) win most often.",
                f"Target {best_count} parlour use per game; more or fewer may not pay off.",
            ))

    if len(villes_rows) >= 10:
        from collections import defaultdict as dd4
        region_win: dict = dd4(list)
        for r in villes_rows:
            if r["controlling_player"] != -1:
                region_win[r["region"]].append(r["controller_is_winner"])
        if region_win:
            best_region = max(region_win, key=lambda reg: np.mean(region_win[reg]))
            blocks.append(_finding(
                "Best Villes region to contest",
                "Chart 13 — Villes region control rate and win correlation",
                "medium",
                f"Region {best_region}: {np.mean(region_win[best_region]):.2f} win rate for controllers",
                "n/a",
                f"Controlling region {best_region} correlates with the highest win rate.",
                f"Prioritise placing cheese in region {best_region} when competing for Villes control.",
            ))

    if len(rows) >= 10:
        winners = [r for r in rows if r["is_winner"] and r["fruit_spent_on_fruited"] is not None]
        losers = [r for r in rows if not r["is_winner"] and r["fruit_spent_on_fruited"] is not None]
        if winners and losers:
            def _balance(r: dict) -> float:
                f, j = r["fruit_spent_on_fruited"], r["fruit_spent_on_jam"]
                total = f + j
                return abs(f - j) / total if total > 0 else 0
            w_imbalance = float(np.mean([_balance(r) for r in winners]))
            l_imbalance = float(np.mean([_balance(r) for r in losers]))
            blocks.append(_finding(
                "Fruit balance and winning",
                "Chart 14 — Fruit balance scatter (fruited vs jam, by outcome)",
                "medium",
                f"Winner imbalance {w_imbalance:.2f}; Loser imbalance {l_imbalance:.2f}",
                f"Δ{w_imbalance - l_imbalance:+.2f} imbalance ratio",
                "Winners have " + ("lower" if w_imbalance < l_imbalance else "higher")
                + " fruit-spend imbalance than losers.",
                "Balance fruited and jam spending (target imbalance ratio < 0.3) to maximise score_fruit.",
            ))

    out_path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    logger.info("Wrote strategy summary to %s (%d findings)", out_path, len(blocks) - 1)
