"""Entry point: train the Q-learning agent via self-play.

Usage::

    python -m src.train --games 10000 --config config/agent_config.json
    python -m src.train --games 500 --seed 42
    python -m src.train --games 500 --charts --eval-games 200 --db data/results.db --out output/

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
logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")

_AGENT_CONFIG_LABEL = "QAgent vs RandomAgent x3"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train QAgent via self-play Q-learning.")
    parser.add_argument(
        "--games",
        type=int,
        default=8000,
        help="Number of self-play training games (default: 8000)",
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
        "--charts",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Generate analysis charts after training (default: off). Use --charts to enable.",
    )
    parser.add_argument(
        "--eval-games",
        type=int,
        default=100,
        help="Games to run for final evaluation (and chart generation if --charts). Default: 100.",
    )
    parser.add_argument(
        "--db",
        type=str,
        default="data/results.db",
        help="Path to SQLite results DB (used when --charts is set, default: data/results.db)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="output/",
        help="Output directory for charts (used when --charts is set, default: output/)",
    )
    parser.add_argument(
        "--learning-plots",
        action="store_true",
        default=False,
        help="[Milestone 9] Generate learning-performance charts after training.",
    )
    return parser.parse_args()


def _generate_charts(db_path: Path, out_dir: Path) -> None:
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
    from src.analysis.results_db import ResultsDB
    db = ResultsDB(db_path)
    plots_dir = out_dir / "plots"
    for fn in plot_fns:
        fn(db, plots_dir)
    write_strategy_summary(db, out_dir / "strategy_summary.md")


def _generate_learning_plots(config_path: Path, out_dir: Path) -> None:
    """Generate L1–L4 learning charts and hyperparameter signals CSV."""
    import json as _json

    from src.analysis.exports import write_hyperparameter_signals
    from src.analysis.plots import (
        plot_epsilon_decay,
        plot_mean_score_training,
        plot_q_weight_norms,
        plot_win_rate_vs_training,
    )

    log_path = out_dir / "training_log.jsonl"
    models_dir = Path("models")
    plots_dir = out_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    if not log_path.exists():
        console.print(f"[yellow]Training log not found at {log_path}; skipping learning plots.[/yellow]")
        return

    with open(config_path, encoding="utf-8") as fh:
        config = _json.load(fh)

    console.print(f"Generating learning charts to [cyan]{plots_dir}[/cyan]…")
    plot_epsilon_decay(log_path, config, plots_dir / "chart_L1_epsilon_decay.png")
    plot_win_rate_vs_training(log_path, plots_dir / "chart_L2_win_rate_vs_training.png")
    plot_mean_score_training(log_path, plots_dir / "chart_L3_mean_score_training.png")
    plot_q_weight_norms(models_dir, plots_dir / "chart_L4_q_weight_norms.png")

    signals_path = out_dir / "hyperparameter_signals.csv"
    write_hyperparameter_signals(log_path, models_dir, config_path, signals_path)
    console.print(f"Wrote hyperparameter signals to [cyan]{signals_path}[/cyan]")


def main() -> None:
    args = _parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    data = GameDataLoader()
    console.print(f"[bold]Training QAgent[/bold] — {args.games} games, config: {args.config}")

    agent = train(n_games=args.games, data=data, config_path=args.config)

    console.print(
        f"\n[bold green]Training complete.[/bold green] "
        f"Running final evaluation ({args.eval_games} games)…"
    )

    if args.charts:
        from src.ai.random_agent import RandomAgent
        from src.analysis.results_db import ResultsDB
        from src.analysis.runner import run_batch

        agent._epsilon = 0.0  # greedy for evaluation
        agents = [
            agent,
            RandomAgent(data, seed=1),
            RandomAgent(data, seed=2),
            RandomAgent(data, seed=3),
        ]
        results = run_batch(args.eval_games, agents, data, base_seed=args.seed)

        db_path = Path(args.db)
        db = ResultsDB(db_path)
        for r in results:
            db.store_result(r, _AGENT_CONFIG_LABEL)
        console.print(f"Stored {len(results)} results in [cyan]{args.db}[/cyan]")

        q_scores = [s.total for r in results for s in r.scores if s.player_id == 0]
        random_scores = [s.total for r in results for s in r.scores if s.player_id != 0]
        wins = sum(1 for r in results if 0 in r.winner_ids)
        result = {
            "win_rate": wins / len(results),
            "mean_pp": sum(q_scores) / len(q_scores),
            "mean_pp_delta_vs_random": (
                sum(q_scores) / len(q_scores) - sum(random_scores) / len(random_scores)
            ),
        }

        out_dir = Path(args.out)
        console.print(f"Generating charts to [cyan]{out_dir}[/cyan]…")
        _generate_charts(db_path, out_dir)
    else:
        result = evaluate(agent, args.eval_games, data)

    table = Table(title=f"Final Evaluation vs. RandomAgent ({args.eval_games} games)")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="magenta")
    table.add_row("Win Rate", f"{result['win_rate']:.3f}")
    table.add_row("Mean PP (QAgent)", f"{result['mean_pp']:.1f}")
    table.add_row("PP Delta vs Random", f"{result['mean_pp_delta_vs_random']:+.1f}")
    console.print(table)

    if args.learning_plots:
        _generate_learning_plots(args.config, Path(args.out))


if __name__ == "__main__":
    main()
