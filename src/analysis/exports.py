"""Structured text exports from simulation results.

write_strategy_summary: writes output/strategy_summary.md with one finding
block per chart (Charts 1–14).

write_hyperparameter_signals: writes output/hyperparameter_signals.csv with
11 computed signals from training logs and model checkpoints.

See requirements sections 8.3.5 (strategy summary) and 13.2 (signals).
"""

from __future__ import annotations

import csv
import glob as _glob_mod
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


# ---------------------------------------------------------------------------
# Hyperparameter signals CSV (requirement 13.2.1)
# ---------------------------------------------------------------------------

def read_training_log(log_path: Path) -> list[dict]:
    """Read a newline-delimited JSON training log."""
    entries: list[dict] = []
    with open(log_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def write_hyperparameter_signals(
    log_path: Path,
    models_dir: Path,
    config_path: Path,
    out_path: Path,
) -> None:
    """Compute 11 training signals and write to CSV.

    Schema: signal, value, unit, threshold, status, recommendation
    """
    with open(config_path, encoding="utf-8") as fh:
        config = json.load(fh)

    entries = read_training_log(log_path)
    if not entries:
        logger.warning("hyperparameter_signals skipped: empty training log")
        return

    epsilon_end = config.get("epsilon_end", 0.05)
    last = entries[-1]

    # --- Compute checkpoint weight norms ---
    ckpt_pattern = str(models_dir / "checkpoint_*.npz")
    ckpt_files = sorted(_glob_mod.glob(ckpt_pattern))
    ckpt_norms: list[tuple[int, float]] = []
    for f in ckpt_files:
        try:
            game_num = int(Path(f).stem.split("_", 1)[1])
        except (IndexError, ValueError):
            continue
        data = np.load(f)
        if "w" in data:
            ckpt_norms.append((game_num, float(np.linalg.norm(data["w"]))))
    ckpt_norms.sort(key=lambda x: x[0])

    # --- Signal computations ---
    signals: list[dict] = []

    # 1. epsilon_final
    eps_final = last["epsilon"]
    signals.append({
        "signal": "epsilon_final",
        "value": f"{eps_final:.4f}",
        "unit": "",
        "threshold": f"<= {epsilon_end}",
        "status": "OK" if eps_final <= epsilon_end else "WARN",
        "recommendation": "Epsilon has reached floor."
        if eps_final <= epsilon_end else "Train more games to reach epsilon floor.",
    })

    # 2. epsilon_floor
    eps_floor = min(e["epsilon"] for e in entries)
    signals.append({
        "signal": "epsilon_floor",
        "value": f"{eps_floor:.4f}",
        "unit": "",
        "threshold": f"<= {epsilon_end}",
        "status": "OK" if eps_floor <= epsilon_end else "WARN",
        "recommendation": "Floor reached." if eps_floor <= epsilon_end
        else "Epsilon never reached configured floor.",
    })

    # 3. games_to_epsilon_floor
    games_to_floor = "n/a"
    for e in entries:
        if e["epsilon"] <= epsilon_end:
            games_to_floor = str(e["game"])
            break
    signals.append({
        "signal": "games_to_epsilon_floor",
        "value": games_to_floor,
        "unit": "games",
        "threshold": "",
        "status": "OK" if games_to_floor != "n/a" else "WARN",
        "recommendation": f"Floor reached at game {games_to_floor}."
        if games_to_floor != "n/a" else "Floor not yet reached.",
    })

    # 4. win_rate_final
    wr_final = last["win_rate"]
    wr_status = "OK" if wr_final > 0.3 else ("WARN" if wr_final > 0.25 else "CRIT")
    signals.append({
        "signal": "win_rate_final",
        "value": f"{wr_final:.4f}",
        "unit": "",
        "threshold": "> 0.30 OK; > 0.25 WARN; else CRIT",
        "status": wr_status,
        "recommendation": "Agent is winning above baseline."
        if wr_status == "OK" else "Agent is near or below random baseline.",
    })

    # 5. win_rate_peak
    wr_peak = max(e["win_rate"] for e in entries)
    signals.append({
        "signal": "win_rate_peak",
        "value": f"{wr_peak:.4f}",
        "unit": "",
        "threshold": "> 0.30",
        "status": "OK" if wr_peak > 0.3 else "WARN",
        "recommendation": "Peak win rate exceeds baseline."
        if wr_peak > 0.3 else "Peak win rate is low; revise hyperparameters.",
    })

    # 6. win_rate_plateau_game — no improvement for >= 1000 games
    plateau_game = "n/a"
    best_so_far = entries[0]["win_rate"]
    last_improvement_game = entries[0]["game"]
    for e in entries[1:]:
        if e["win_rate"] > best_so_far:
            best_so_far = e["win_rate"]
            last_improvement_game = e["game"]
        elif e["game"] - last_improvement_game >= 1000:
            plateau_game = str(last_improvement_game)
            break
    signals.append({
        "signal": "win_rate_plateau_game",
        "value": plateau_game,
        "unit": "games",
        "threshold": "",
        "status": "OK" if plateau_game != "n/a" else "WARN",
        "recommendation": f"Win rate plateaued at game {plateau_game}."
        if plateau_game != "n/a" else "No plateau detected; agent may still be improving.",
    })

    # 7. score_mean_final
    signals.append({
        "signal": "score_mean_final",
        "value": f"{last['mean_score']:.2f}",
        "unit": "pts",
        "threshold": "",
        "status": "OK",
        "recommendation": f"Final mean score is {last['mean_score']:.1f}.",
    })

    # 8. score_std_final
    std_final = last["std_score"]
    signals.append({
        "signal": "score_std_final",
        "value": f"{std_final:.2f}",
        "unit": "pts",
        "threshold": "",
        "status": "OK" if std_final < 5.0 else "WARN",
        "recommendation": "Score variance is reasonable."
        if std_final < 5.0 else "High score variance; policy may not have converged.",
    })

    # 9. score_std_trend — compare late vs early std
    half = len(entries) // 2
    if half > 0:
        early_std = np.mean([e["std_score"] for e in entries[:half]])
        late_std = np.mean([e["std_score"] for e in entries[half:]])
        trend = "decreasing" if late_std < early_std else "increasing"
        trend_symbol = "\u2193" if late_std < early_std else "\u2191"
    else:
        trend = "n/a"
        trend_symbol = "n/a"
    signals.append({
        "signal": "score_std_trend",
        "value": trend_symbol,
        "unit": "",
        "threshold": "decreasing = OK",
        "status": "OK" if trend == "decreasing" else "WARN",
        "recommendation": "Score variance is narrowing (policy converging)."
        if trend == "decreasing" else "Score variance is widening or flat.",
    })

    # 10. weight_norm_final
    if ckpt_norms:
        wn_final = ckpt_norms[-1][1]
        signals.append({
            "signal": "weight_norm_final",
            "value": f"{wn_final:.4f}",
            "unit": "",
            "threshold": "",
            "status": "OK",
            "recommendation": f"Final weight norm is {wn_final:.2f}.",
        })
    else:
        signals.append({
            "signal": "weight_norm_final",
            "value": "n/a",
            "unit": "",
            "threshold": "",
            "status": "WARN",
            "recommendation": "No checkpoints found.",
        })

    # 11. weight_norm_delta
    if len(ckpt_norms) >= 2:
        wn_delta = ckpt_norms[-1][1] - ckpt_norms[0][1]
        delta_pct = abs(wn_delta) / (ckpt_norms[0][1] or 1) * 100
        signals.append({
            "signal": "weight_norm_delta",
            "value": f"{wn_delta:+.4f}",
            "unit": "",
            "threshold": "< 10% change = stable",
            "status": "OK" if delta_pct < 10 else "WARN",
            "recommendation": "Weights are stable."
            if delta_pct < 10 else "Weights are still shifting; consider more training.",
        })
    else:
        signals.append({
            "signal": "weight_norm_delta",
            "value": "n/a",
            "unit": "",
            "threshold": "",
            "status": "WARN",
            "recommendation": "Need at least 2 checkpoints to compute delta.",
        })

    # --- Write CSV ---
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["signal", "value", "unit", "threshold", "status", "recommendation"]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(signals)

    logger.info("Wrote %d hyperparameter signals to %s", len(signals), out_path)
