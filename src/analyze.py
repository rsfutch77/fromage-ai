"""Entry point: run a batch of RandomAgent games, store results, print stats.

Usage:
    python -m src.analyze --games 100 --db data/results.db --seed 42

Plots are deferred to Milestone 6 (Phase 5).

See requirements section 13.3.
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
        "--games", type=int, default=100, help="Number of games to simulate (default: 100)"
    )
    parser.add_argument(
        "--db", type=str, default="data/results.db", help="Path to SQLite results DB"
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="Base random seed (optional)"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    args = _parse_args(argv)
    data = GameDataLoader()
    agents = [RandomAgent(data, seed=(args.seed + i) if args.seed is not None else None)
              for i in range(4)]

    logger.info("Running %d games with %s (seed=%s)", args.games, _AGENT_CONFIG, args.seed)
    results = run_batch(args.games, agents, data, base_seed=args.seed)

    db = ResultsDB(Path(args.db))
    for result in results:
        db.store_result(result, _AGENT_CONFIG)
    logger.info("Stored %d results in %s", len(results), args.db)

    stats = BaselineStats(results)
    print(stats.summary_table())


if __name__ == "__main__":
    main()
