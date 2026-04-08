"""Parallel hyperparameter sweep for Q-learning agent training.

Runs multiple short training runs in parallel across CPU cores, each with
a different hyperparameter config from a Cartesian product grid.  Produces
a ranked comparison CSV so the best config can be identified before
committing to a full-length training run.

Usage::

    python -m src.sweep --config config/sweep_config.json --seed 42
    python -m src.sweep --dry-run

See Milestone 11 in plans1_project/3-milestones.md.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import logging
import multiprocessing
import os
import threading
import time
from pathlib import Path

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.table import Table

from src.ai.training import evaluate, train_for_sweep
from src.game.data_loader import GameDataLoader

console = Console()
logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Sentinel value to signal the progress reader thread to stop.
_POISON = None


# ---------------------------------------------------------------------------
# Grid expansion
# ---------------------------------------------------------------------------

def expand_grid(grid: dict[str, list]) -> list[dict]:
    """Return the Cartesian product of *grid* values as a list of dicts.

    >>> expand_grid({"a": [1, 2], "b": [3, 4]})
    [{'a': 1, 'b': 3}, {'a': 1, 'b': 4}, {'a': 2, 'b': 3}, {'a': 2, 'b': 4}]
    """
    keys = list(grid.keys())
    combos = list(itertools.product(*[grid[k] for k in keys]))
    return [dict(zip(keys, combo)) for combo in combos]


# ---------------------------------------------------------------------------
# Single-run worker (must be a top-level function for pickling)
# ---------------------------------------------------------------------------

# Module-level ref set by each worker process via the Pool initializer.
_progress_queue: multiprocessing.Queue | None = None


def _pool_init(queue: multiprocessing.Queue) -> None:
    """Initializer called once per worker process to store the shared queue."""
    global _progress_queue  # noqa: PLW0603
    _progress_queue = queue


def _run_single_config(args: tuple) -> dict:
    """Train one config and return summary metrics.

    Accepts a single tuple for compatibility with ``Pool.map``:
    ``(run_id, config, n_games, eval_interval, eval_games, final_eval_games, seed)``.
    """
    run_id, config, n_games, eval_interval, eval_games, final_eval_games, seed = args

    if seed is not None:
        import random
        random.seed(seed + run_id)

    data = GameDataLoader()
    t0 = time.perf_counter()

    # Signal that this run is starting
    if _progress_queue is not None:
        _progress_queue.put(("start", run_id, 0, n_games))

    agent, eval_log = train_for_sweep(
        n_games=n_games,
        data=data,
        config=config,
        eval_interval=eval_interval,
        eval_games=eval_games,
        progress_queue=_progress_queue,
        run_id=run_id,
    )

    final_result = evaluate(agent, final_eval_games, data)
    elapsed = time.perf_counter() - t0

    # Extract swept params for the results row
    swept_params = {
        k: config[k]
        for k in ("alpha", "gamma", "epsilon_decay_games", "weight_decay")
        if k in config
    }

    return {
        "run_id": run_id,
        "win_rate": final_result["win_rate"],
        "mean_pp": final_result["mean_pp"],
        "pp_delta": final_result["mean_pp_delta_vs_random"],
        "final_epsilon": round(agent._epsilon, 4),
        "elapsed_seconds": round(elapsed, 1),
        "eval_log": eval_log,
        **swept_params,
    }


# ---------------------------------------------------------------------------
# Progress reader thread
# ---------------------------------------------------------------------------

def _progress_reader(
    queue: multiprocessing.Queue,
    progress: Progress,
    overall_task_id,
    n_games_per_run: int,
) -> None:
    """Background thread that reads worker progress messages and updates bars.

    Messages are tuples: ``(kind, run_id, game_num, n_games)`` where *kind*
    is ``"start"``, ``"progress"``, or ``"done"``.
    """
    run_tasks: dict[int, object] = {}  # run_id -> rich task id

    while True:
        msg = queue.get()
        if msg is _POISON:
            break

        kind, run_id, game_num, n_games = msg

        if kind == "start":
            task_id = progress.add_task(
                f"  run {run_id:>3d}",
                total=n_games,
                completed=0,
            )
            run_tasks[run_id] = task_id

        elif kind == "progress":
            task_id = run_tasks.get(run_id)
            if task_id is not None:
                progress.update(task_id, completed=game_num)

        elif kind == "done":
            task_id = run_tasks.pop(run_id, None)
            if task_id is not None:
                progress.update(task_id, completed=n_games, visible=False)
            progress.advance(overall_task_id)


# ---------------------------------------------------------------------------
# Sweep runner
# ---------------------------------------------------------------------------

def run_sweep(sweep_config_path: Path, seed: int | None = None) -> list[dict]:
    """Run a full hyperparameter sweep and write results CSV.

    Returns results sorted by win_rate descending (tiebreak by pp_delta).
    """
    sweep_cfg = json.loads(Path(sweep_config_path).read_text())
    base_config = json.loads(Path(sweep_cfg["base_config"]).read_text())

    n_games = int(sweep_cfg.get("screening_games", 2000))
    eval_interval = int(sweep_cfg.get("screening_eval_interval", 500))
    eval_games = int(sweep_cfg.get("screening_eval_games", 50))
    final_eval_games = int(sweep_cfg.get("final_eval_games", 100))
    max_workers = sweep_cfg.get("max_workers") or os.cpu_count() or 4

    grid_combos = expand_grid(sweep_cfg["grid"])
    total_runs = len(grid_combos)
    console.print(
        f"[bold]Sweep:[/bold] {total_runs} configs × {n_games} games, "
        f"{max_workers} workers"
    )

    # Build argument tuples for each run
    work_items: list[tuple] = []
    for run_id, combo in enumerate(grid_combos):
        config = {**base_config, **combo, "eval_interval": eval_interval}
        work_items.append(
            (run_id, config, n_games, eval_interval, eval_games, final_eval_games, seed)
        )

    # Shared queue for worker -> parent progress messages
    progress_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Set up rich progress display
    progress_bar = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TextColumn("eta"),
        TimeRemainingColumn(),
    )

    results: list[dict] = []

    with progress_bar:
        overall_task = progress_bar.add_task(
            "Sweep — completed runs", total=total_runs
        )

        # Start background thread to read progress messages
        reader = threading.Thread(
            target=_progress_reader,
            args=(progress_queue, progress_bar, overall_task, n_games),
            daemon=True,
        )
        reader.start()

        # Run all configs in parallel; workers send progress via the queue
        with multiprocessing.Pool(
            processes=max_workers,
            initializer=_pool_init,
            initargs=(progress_queue,),
        ) as pool:
            for result in pool.imap_unordered(_run_single_config, work_items):
                results.append(result)

        # Signal the reader thread to exit
        progress_queue.put(_POISON)
        reader.join(timeout=5)

    # Sort: best win_rate first, tiebreak by pp_delta
    results.sort(key=lambda r: (-r["win_rate"], -r["pp_delta"]))

    # Assign rank
    for rank, r in enumerate(results, 1):
        r["rank"] = rank

    # Write CSV
    _write_results_csv(results, sweep_cfg["grid"])

    # Print top 5
    _print_top_results(results)

    return results


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _write_results_csv(results: list[dict], grid: dict) -> None:
    """Write sweep results to ``output/sweep_results.csv``."""
    Path("output").mkdir(parents=True, exist_ok=True)
    out_path = Path("output") / "sweep_results.csv"

    swept_keys = list(grid.keys())
    fieldnames = [
        "rank", "run_id", "win_rate", "mean_pp", "pp_delta",
        "final_epsilon", "elapsed_seconds",
    ] + swept_keys

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    console.print(f"\nResults written to [cyan]{out_path}[/cyan]")


def _print_top_results(results: list[dict], n: int = 5) -> None:
    """Print a rich table of the top *n* results."""
    table = Table(title=f"Top {min(n, len(results))} Sweep Results")
    table.add_column("Rank", style="bold", justify="right")
    table.add_column("Run", justify="right")
    table.add_column("Win Rate", justify="right", style="green")
    table.add_column("PP Delta", justify="right", style="cyan")
    table.add_column("Mean PP", justify="right")
    table.add_column("Time (s)", justify="right")
    table.add_column("alpha", justify="right")
    table.add_column("gamma", justify="right")
    table.add_column("eps_decay", justify="right")
    table.add_column("w_decay", justify="right")

    for r in results[:n]:
        table.add_row(
            str(r["rank"]),
            str(r["run_id"]),
            f"{r['win_rate']:.3f}",
            f"{r['pp_delta']:+.1f}",
            f"{r['mean_pp']:.1f}",
            f"{r['elapsed_seconds']:.0f}",
            str(r.get("alpha", "")),
            str(r.get("gamma", "")),
            str(r.get("epsilon_decay_games", "")),
            str(r.get("weight_decay", "")),
        )

    console.print(table)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a parallel hyperparameter sweep for Q-learning training."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/sweep_config.json"),
        help="Path to sweep config JSON (default: config/sweep_config.json)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional global random seed for reproducibility",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print grid info without running any training",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    sweep_cfg = json.loads(Path(args.config).read_text())
    grid_combos = expand_grid(sweep_cfg["grid"])
    max_workers = sweep_cfg.get("max_workers") or os.cpu_count() or 4

    console.print(f"[bold]Hyperparameter Sweep[/bold]")
    console.print(f"  Base config: {sweep_cfg['base_config']}")
    console.print(f"  Grid size:   {len(grid_combos)} combinations")
    console.print(f"  Workers:     {max_workers} (CPU cores)")
    console.print(f"  Games/run:   {sweep_cfg.get('screening_games', 2000)}")
    console.print(f"  Eval every:  {sweep_cfg.get('screening_eval_interval', 500)} games")
    console.print(f"  Eval games:  {sweep_cfg.get('screening_eval_games', 50)} (screening)")
    console.print(f"  Final eval:  {sweep_cfg.get('final_eval_games', 100)} games")

    for param, values in sweep_cfg["grid"].items():
        console.print(f"  {param}: {values}")

    if args.dry_run:
        console.print("\n[yellow]Dry run — no training performed.[/yellow]")
        return

    console.print()
    run_sweep(args.config, seed=args.seed)


if __name__ == "__main__":
    main()
