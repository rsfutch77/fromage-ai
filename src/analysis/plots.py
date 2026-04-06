"""Game-analysis matplotlib charts (Charts 1–14).

All functions read from a ResultsDB instance and write PNGs to out_dir.
Each function skips silently (with a warning log) when fewer than
MIN_GAMES_FOR_CHART rows are available.

See requirements section 8.3 and Milestone 6.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib
matplotlib.use("Agg")  # non-interactive backend; safe for tests / headless servers
import matplotlib.pyplot as plt
import numpy as np

if TYPE_CHECKING:
    from src.analysis.results_db import ResultsDB

logger = logging.getLogger(__name__)

MIN_GAMES_FOR_CHART: int = 10

_VENUES = ["fromagerie", "bistro", "villes", "festival"]
_SCORE_CATS = ["festival", "villes", "fromagerie", "bistro", "orders",
               "fruit", "headquarters", "unused_resources"]
_AGES = ["BRONZE", "SILVER", "GOLD"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_min(rows: list, chart: str) -> bool:
    if len(rows) < MIN_GAMES_FOR_CHART:
        logger.warning("Chart %s skipped: only %d rows (need %d)", chart, len(rows), MIN_GAMES_FOR_CHART)
        return False
    return True


def _save(fig: "plt.Figure", out_dir: Path, name: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    fig.savefig(path, bbox_inches="tight", dpi=100)
    plt.close(fig)
    logger.info("Saved %s", path)


# ---------------------------------------------------------------------------
# Chart 1 — Structure build frequency by player board
# ---------------------------------------------------------------------------

def plot_structure_frequency(db: "ResultsDB", out_dir: Path) -> None:
    rows = db.fetch_scores()
    if not _check_min(rows, "1 structure_frequency"):
        return

    board_unlocks: dict[int, list[list[int]]] = defaultdict(lambda: [[] for _ in range(4)])
    for r in rows:
        if r["structures_unlocked"] is None:
            continue
        bools = json.loads(r["structures_unlocked"])
        for slot, unlocked in enumerate(bools):
            board_unlocks[r["board_id"]][slot].append(int(unlocked))

    boards = sorted(board_unlocks)
    x = np.arange(4)
    width = 0.2
    fig, ax = plt.subplots(figsize=(10, 5))
    for i, board in enumerate(boards):
        rates = [np.mean(board_unlocks[board][s]) if board_unlocks[board][s] else 0 for s in range(4)]
        ax.bar(x + i * width, rates, width, label=f"Board {board}")
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels([f"Slot {s+1}" for s in range(4)])
    ax.set_ylabel("Unlock rate")
    ax.set_title("Structure unlock frequency by board")
    ax.legend()
    _save(fig, out_dir, "chart_01_structure_frequency.png")


# ---------------------------------------------------------------------------
# Chart 2 — Average points per venue
# ---------------------------------------------------------------------------

def plot_points_per_venue(db: "ResultsDB", out_dir: Path) -> None:
    rows = db.fetch_scores()
    if not _check_min(rows, "2 points_per_venue"):
        return

    means = {v: np.mean([r[v] for r in rows]) for v in _VENUES}
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(list(means.keys()), list(means.values()),
           color=["#4CAF50", "#2196F3", "#FF9800", "#9C27B0"])
    ax.set_ylabel("Mean score")
    ax.set_title("Average points per venue")
    _save(fig, out_dir, "chart_02_points_per_venue.png")


# ---------------------------------------------------------------------------
# Chart 3 — Win rate per player board
# ---------------------------------------------------------------------------

def plot_win_rate_by_board(db: "ResultsDB", out_dir: Path) -> None:
    rows = db.fetch_scores()
    if not _check_min(rows, "3 win_rate_by_board"):
        return

    board_wins: dict[int, list[int]] = defaultdict(list)
    for r in rows:
        board_wins[r["board_id"]].append(r["is_winner"])

    boards = sorted(board_wins)
    rates = [np.mean(board_wins[b]) for b in boards]
    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar([f"Board {b}" for b in boards], rates)
    ax.axhline(0.25, color="red", linestyle="--", label="Random baseline (0.25)")
    ax.set_ylabel("Win rate")
    ax.set_title("Win rate per player board")
    ax.legend()
    for bar, rate in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f"{rate:.2f}", ha="center", fontsize=9)
    _save(fig, out_dir, "chart_03_win_rate_by_board.png")


# ---------------------------------------------------------------------------
# Chart 4 — Fruit vs jam usage
# ---------------------------------------------------------------------------

def plot_fruit_usage(db: "ResultsDB", out_dir: Path) -> None:
    rows = db.fetch_scores()
    if not _check_min(rows, "4 fruit_usage"):
        return

    fruited = np.mean([r["fruit_spent_on_fruited"] or 0 for r in rows])
    jam = np.mean([r["fruit_spent_on_jam"] or 0 for r in rows])
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar(["Fruited cheese", "Jam cheese"], [fruited, jam], color=["#FF6B6B", "#FFD93D"])
    ax.set_ylabel("Mean fruit spent per player per game")
    ax.set_title("Fruit usage: fruited vs jam")
    _save(fig, out_dir, "chart_04_fruit_usage.png")


# ---------------------------------------------------------------------------
# Chart 5 — Orders as share of total score
# ---------------------------------------------------------------------------

def plot_orders_share(db: "ResultsDB", out_dir: Path) -> None:
    rows = db.fetch_scores()
    if not _check_min(rows, "5 orders_share"):
        return

    shares = [r["orders"] / r["total"] * 100 for r in rows if r["total"] > 0]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(shares, bins=20, color="#42A5F5", edgecolor="white")
    ax.axvline(np.mean(shares), color="red", linestyle="--",
               label=f"Mean {np.mean(shares):.1f}%")
    ax.set_xlabel("Orders / total score (%)")
    ax.set_ylabel("Count")
    ax.set_title("Orders as share of total score")
    ax.legend()
    _save(fig, out_dir, "chart_05_orders_share.png")


# ---------------------------------------------------------------------------
# Chart 6 — Unused resources as share of total score
# ---------------------------------------------------------------------------

def plot_unused_resources_share(db: "ResultsDB", out_dir: Path) -> None:
    rows = db.fetch_scores()
    if not _check_min(rows, "6 unused_resources_share"):
        return

    shares = [r["unused_resources"] / r["total"] * 100 for r in rows if r["total"] > 0]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(shares, bins=20, color="#EF5350", edgecolor="white")
    ax.axvline(np.mean(shares), color="navy", linestyle="--",
               label=f"Mean {np.mean(shares):.1f}%")
    ax.set_xlabel("Unused resources / total score (%)")
    ax.set_ylabel("Count")
    ax.set_title("Unused resources as share of total score")
    ax.legend()
    _save(fig, out_dir, "chart_06_unused_resources_share.png")


# ---------------------------------------------------------------------------
# Chart 7 — Winner vs loser score breakdown (radar)
# ---------------------------------------------------------------------------

def plot_winner_vs_loser_radar(db: "ResultsDB", out_dir: Path) -> None:
    rows = db.fetch_scores()
    if not _check_min(rows, "7 winner_vs_loser_radar"):
        return

    winners = [r for r in rows if r["is_winner"]]
    losers = [r for r in rows if not r["is_winner"]]
    if not winners or not losers:
        logger.warning("Chart 7 skipped: no winner/loser split available")
        return

    cats = _SCORE_CATS
    n = len(cats)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]

    w_means = [np.mean([r[c] for r in winners]) for c in cats]
    l_means = [np.mean([r[c] for r in losers]) for c in cats]
    maxvals = [max(wm, lm) or 1 for wm, lm in zip(w_means, l_means)]
    w_norm = [v / m for v, m in zip(w_means, maxvals)] + [w_means[0] / maxvals[0]]
    l_norm = [v / m for v, m in zip(l_means, maxvals)] + [l_means[0] / maxvals[0]]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"polar": True})
    ax.plot(angles, w_norm, "o-", color="#4CAF50", label="Winners")
    ax.fill(angles, w_norm, alpha=0.25, color="#4CAF50")
    ax.plot(angles, l_norm, "o-", color="#F44336", label="Losers")
    ax.fill(angles, l_norm, alpha=0.25, color="#F44336")
    ax.set_thetagrids(np.degrees(angles[:-1]), cats)
    ax.set_title("Winner vs loser score breakdown", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
    _save(fig, out_dir, "chart_07_winner_vs_loser_radar.png")


# ---------------------------------------------------------------------------
# Chart 8 — Board × venue synergy heatmap
# ---------------------------------------------------------------------------

def plot_board_venue_heatmap(db: "ResultsDB", out_dir: Path) -> None:
    rows = db.fetch_scores()
    if not _check_min(rows, "8 board_venue_heatmap"):
        return

    boards = sorted({r["board_id"] for r in rows})
    data = np.zeros((len(boards), len(_VENUES)))
    for bi, board in enumerate(boards):
        subset = [r for r in rows if r["board_id"] == board]
        for vi, venue in enumerate(_VENUES):
            data[bi, vi] = np.mean([r[venue] for r in subset]) if subset else 0

    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(data, aspect="auto", cmap="YlOrRd")
    ax.set_xticks(range(len(_VENUES)))
    ax.set_xticklabels(_VENUES)
    ax.set_yticks(range(len(boards)))
    ax.set_yticklabels([f"Board {b}" for b in boards])
    for bi in range(len(boards)):
        for vi in range(len(_VENUES)):
            ax.text(vi, bi, f"{data[bi, vi]:.1f}", ha="center", va="center", fontsize=9)
    plt.colorbar(im, ax=ax, label="Mean score")
    ax.set_title("Board × venue synergy heatmap")
    _save(fig, out_dir, "chart_08_board_venue_heatmap.png")


# ---------------------------------------------------------------------------
# Chart 9 — Cheese age distribution: winners vs losers
# ---------------------------------------------------------------------------

def plot_cheese_age_distribution(db: "ResultsDB", out_dir: Path) -> None:
    rows = db.fetch_placed_cheese()
    if not _check_min(rows, "9 cheese_age_distribution"):
        return

    w_counts: dict[str, list] = {a: [] for a in _AGES}
    l_counts: dict[str, list] = {a: [] for a in _AGES}
    player_ages: dict[tuple, dict[str, int]] = defaultdict(lambda: {a: 0 for a in _AGES})
    player_winner: dict[tuple, int] = {}
    for r in rows:
        key = (r["game_id"], r["player_id"])
        if r["age"] in player_ages[key]:
            player_ages[key][r["age"]] = r["count"]
        player_winner[key] = r["is_winner"]

    for key, ages in player_ages.items():
        target = w_counts if player_winner.get(key) else l_counts
        for age in _AGES:
            target[age].append(ages[age])

    x = np.arange(len(_AGES))
    width = 0.35
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(x - width / 2, [np.mean(w_counts[a]) if w_counts[a] else 0 for a in _AGES],
           width, label="Winners", color="#4CAF50")
    ax.bar(x + width / 2, [np.mean(l_counts[a]) if l_counts[a] else 0 for a in _AGES],
           width, label="Losers", color="#F44336")
    ax.set_xticks(x)
    ax.set_xticklabels(_AGES)
    ax.set_ylabel("Mean cheese tokens placed")
    ax.set_title("Cheese age distribution: winners vs losers")
    ax.legend()
    _save(fig, out_dir, "chart_09_cheese_age_distribution.png")


# ---------------------------------------------------------------------------
# Chart 10 — Structure unlock rate: winners vs losers
# ---------------------------------------------------------------------------

def plot_structure_unlock_by_outcome(db: "ResultsDB", out_dir: Path) -> None:
    rows = db.fetch_scores()
    if not _check_min(rows, "10 structure_unlock_by_outcome"):
        return

    boards = sorted({r["board_id"] for r in rows})
    labels, w_rates, l_rates = [], [], []
    for board in boards:
        for slot in range(4):
            subset = [r for r in rows if r["board_id"] == board
                      and r["structures_unlocked"] is not None]
            winners = [r for r in subset if r["is_winner"]]
            losers = [r for r in subset if not r["is_winner"]]
            labels.append(f"B{board}S{slot+1}")
            w_rates.append(
                np.mean([json.loads(r["structures_unlocked"])[slot] for r in winners])
                if winners else 0
            )
            l_rates.append(
                np.mean([json.loads(r["structures_unlocked"])[slot] for r in losers])
                if losers else 0
            )

    x = np.arange(len(labels))
    width = 0.4
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.bar(x - width / 2, w_rates, width, label="Winners", color="#4CAF50")
    ax.bar(x + width / 2, l_rates, width, label="Losers", color="#F44336")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel("Unlock rate")
    ax.set_title("Structure unlock rate: winners vs losers")
    ax.legend()
    fig.tight_layout()
    _save(fig, out_dir, "chart_10_structure_unlock_by_outcome.png")


# ---------------------------------------------------------------------------
# Chart 11 — Headquarters score by board (winners vs losers)
# ---------------------------------------------------------------------------

def plot_headquarters_by_board(db: "ResultsDB", out_dir: Path) -> None:
    rows = db.fetch_scores()
    if not _check_min(rows, "11 headquarters_by_board"):
        return

    boards = sorted({r["board_id"] for r in rows})
    x = np.arange(len(boards))
    width = 0.35
    fig, ax = plt.subplots(figsize=(7, 4))
    w_hq = [
        np.mean([r["headquarters"] for r in rows if r["board_id"] == b and r["is_winner"]])
        if any(r["board_id"] == b and r["is_winner"] for r in rows) else 0
        for b in boards
    ]
    l_hq = [
        np.mean([r["headquarters"] for r in rows if r["board_id"] == b and not r["is_winner"]])
        if any(r["board_id"] == b and not r["is_winner"] for r in rows) else 0
        for b in boards
    ]
    ax.bar(x - width / 2, w_hq, width, label="Winners", color="#4CAF50")
    ax.bar(x + width / 2, l_hq, width, label="Losers", color="#F44336")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Board {b}" for b in boards])
    ax.set_ylabel("Mean HQ score")
    ax.set_title("Headquarters score by board: winners vs losers")
    ax.legend()
    _save(fig, out_dir, "chart_11_headquarters_by_board.png")


# ---------------------------------------------------------------------------
# Chart 12 — Milking parlour usage count vs win rate
# ---------------------------------------------------------------------------

def plot_parlour_usage_vs_win_rate(db: "ResultsDB", out_dir: Path) -> None:
    rows = db.fetch_scores()
    if not _check_min(rows, "12 parlour_usage_vs_win_rate"):
        return

    usage_wins: dict[int, list[int]] = defaultdict(list)
    for r in rows:
        if r["milking_parlours_used"] is not None:
            usage_wins[r["milking_parlours_used"]].append(r["is_winner"])

    counts = sorted(usage_wins)
    rates = [np.mean(usage_wins[c]) for c in counts]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar([str(c) for c in counts], rates, color="#7E57C2")
    ax.axhline(0.25, color="red", linestyle="--", label="Random baseline")
    ax.set_xlabel("Parlours used")
    ax.set_ylabel("Win rate")
    ax.set_title("Milking parlour usage vs win rate")
    ax.legend()
    _save(fig, out_dir, "chart_12_parlour_usage_vs_win_rate.png")


# ---------------------------------------------------------------------------
# Chart 13 — Villes region control rate and win correlation
# ---------------------------------------------------------------------------

def plot_villes_region_control(db: "ResultsDB", out_dir: Path) -> None:
    rows = db.fetch_villes_control()
    if not _check_min(rows, "13 villes_region_control"):
        return

    regions = sorted({r["region"] for r in rows})
    control_rates, win_rates = [], []
    for region in regions:
        subset = [r for r in rows if r["region"] == region]
        controlled = [r for r in subset if r["controlling_player"] != -1]
        control_rates.append(len(controlled) / len(subset) if subset else 0)
        win_rates.append(
            np.mean([r["controller_is_winner"] for r in controlled]) if controlled else 0
        )

    x = np.arange(len(regions))
    width = 0.35
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(x - width / 2, control_rates, width, label="Control rate", color="#42A5F5")
    ax.bar(x + width / 2, win_rates, width, label="Win rate (controllers)", color="#FF7043")
    ax.set_xticks(x)
    ax.set_xticklabels(regions, rotation=30, ha="right")
    ax.set_ylabel("Rate")
    ax.set_title("Villes region control rate and win correlation")
    ax.legend()
    fig.tight_layout()
    _save(fig, out_dir, "chart_13_villes_region_control.png")


# ---------------------------------------------------------------------------
# Chart 14 — Fruit balance scatter (fruited vs jam, coloured by outcome)
# ---------------------------------------------------------------------------

def plot_fruit_balance_scatter(db: "ResultsDB", out_dir: Path) -> None:
    rows = db.fetch_scores()
    if not _check_min(rows, "14 fruit_balance_scatter"):
        return

    winners = [r for r in rows if r["is_winner"] and r["fruit_spent_on_fruited"] is not None]
    losers = [r for r in rows if not r["is_winner"] and r["fruit_spent_on_fruited"] is not None]
    fig, ax = plt.subplots(figsize=(7, 6))
    if losers:
        ax.scatter(
            [r["fruit_spent_on_fruited"] for r in losers],
            [r["fruit_spent_on_jam"] for r in losers],
            alpha=0.4, color="#F44336", label="Losers", s=20,
        )
    if winners:
        ax.scatter(
            [r["fruit_spent_on_fruited"] for r in winners],
            [r["fruit_spent_on_jam"] for r in winners],
            alpha=0.6, color="#4CAF50", label="Winners", s=20,
        )
    all_vals = (
        [r["fruit_spent_on_fruited"] for r in rows if r["fruit_spent_on_fruited"]]
        + [r["fruit_spent_on_jam"] for r in rows if r["fruit_spent_on_jam"]]
    )
    max_val = max(all_vals) if all_vals else 1
    ax.plot([0, max_val], [0, max_val], "k--", alpha=0.5, label="y = x (perfect balance)")
    ax.set_xlabel("Fruit spent on fruited cheese")
    ax.set_ylabel("Fruit spent on jam cheese")
    ax.set_title("Fruit balance: fruited vs jam (by outcome)")
    ax.legend()
    _save(fig, out_dir, "chart_14_fruit_balance_scatter.png")
