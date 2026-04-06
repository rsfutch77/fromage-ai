"""Entry point: train the Q-learning agent via self-play.

Usage::

    python -m src.train --games 10000 --config config/agent_config.json
    python -m src.train --games 500 --seed 42

See requirements section 11.2.
"""

from __future__ import annotations

import argparse
import logging
import random
from pathlib import Path

from rich.console import Console
from rich.table import Table

from src.ai.training import evaluate, train
from src.game.data_loader import GameDataLoader

console = Console()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train QAgent via self-play Q-learning.")
    parser.add_argument(
        "--games",
        type=int,
        default=10000,
        help="Number of self-play training games (default: 10000)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/agent_config.json"),
        help="Path to agent config JSON (default: config/agent_config.json)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional global random seed for reproducibility",
    )
    parser.add_argument(
        "--learning-plots",
        action="store_true",
        default=False,
        help="[Milestone 9] Generate learning-performance charts after training.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    data = GameDataLoader()
    console.print(f"[bold]Training QAgent[/bold] — {args.games} games, config: {args.config}")

    agent = train(n_games=args.games, data=data, config_path=args.config)

    console.print("\n[bold green]Training complete.[/bold green] Running final evaluation (100 games)…")
    result = evaluate(agent, 100, data)

    table = Table(title="Final Evaluation vs. RandomAgent (100 games)")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="magenta")
    table.add_row("Win Rate", f"{result['win_rate']:.3f}")
    table.add_row("Mean PP (QAgent)", f"{result['mean_pp']:.1f}")
    table.add_row("PP Delta vs Random", f"{result['mean_pp_delta_vs_random']:+.1f}")
    console.print(table)

    if args.learning_plots:
        console.print(
            "[yellow]--learning-plots is not yet implemented (Milestone 9).[/yellow]"
        )


if __name__ == "__main__":
    main()
