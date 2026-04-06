"""Entry point: run a batch of RandomAgent games, store results, print stats,
and optionally generate analysis charts.

Usage:
    python -m src.analyze --games 100 --db data/results.db --seed 42
    python -m src.analyze --games 100 --charts --out output/

See requirements sections 8.2.2, 8.3.4–8.3.6, and Milestone 6.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.ai.random_agent import RandomAgent
from src.analysis.runner import run_batch
from src.analysis.results_db import ResultsDB
from src.analysis.stats import BaselineStats
from src.game.data_loader import GameDataLoader

logger = logging.getLogger(__name__)

_AGENT_CONFIG = "RandomAgent x4"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run baseline RandomAgent games and print summary statistics."
    )
    parser.add_argument(
        "--games", type=int, default=100,
        help="Number of games to simulate (default: 100)"
    )
    parser.add_argument(
        "--db", type=str, default="data/results.db",
        help="Path to SQLite results DB"
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Base random seed (optional)"
    )
    parser.add_argument(
        "--charts", action=argparse.BooleanOptionalAction, default=True,
        help="Generate analysis charts (default: on). Use --no-charts to skip."
    )
    parser.add_argument(
        "--out", type=str, default="output/",
        help="Output directory for charts and strategy_summary.md (default: output/)"
    )
    return parser.parse_args(argv)


def _generate_charts(db: ResultsDB, out_dir: Path) -> None:
    from src.analysis import plots
    from src.analysis.exports import write_strategy_summary

    plot_fns = [
        plots.plot_structure_frequency,
        plots.plot_points_per_venue,
        plots.plot_win_rate_by_board,
        plots.plot_fruit_usage,
        plots.plot_orders_share,
        plots.plot_unused_resources_share,
        plots.plot_winner_vs_loser_radar,
        plots.plot_board_venue_heatmap,
        plots.plot_cheese_age_distribution,
        plots.plot_structure_unlock_by_outcome,
        plots.plot_headquarters_by_board,
        plots.plot_parlour_usage_vs_win_rate,
        plots.plot_villes_region_control,
        plots.plot_fruit_balance_scatter,
    ]
    plots_dir = out_dir / "plots"
    for fn in plot_fns:
        fn(db, plots_dir)

    write_strategy_summary(db, out_dir / "strategy_summary.md")


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    args = _parse_args(argv)
    data = GameDataLoader()
    agents = [
        RandomAgent(data, seed=(args.seed + i) if args.seed is not None else None)
        for i in range(4)
    ]

    logger.info("Running %d games with %s (seed=%s)", args.games, _AGENT_CONFIG, args.seed)
    results = run_batch(args.games, agents, data, base_seed=args.seed)

    db = ResultsDB(Path(args.db))
    for result in results:
        db.store_result(result, _AGENT_CONFIG)
    logger.info("Stored %d results in %s", len(results), args.db)

    stats = BaselineStats(results)
    print(stats.summary_table())

    if args.charts:
        out_dir = Path(args.out)
        logger.info("Generating charts to %s", out_dir)
        _generate_charts(db, out_dir)


if __name__ == "__main__":
    main()
