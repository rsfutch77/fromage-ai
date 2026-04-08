"""Parallel hyperparameter sweep for Q-learning agent training.

Runs multiple short training runs in parallel across CPU cores, each with
a different hyperparameter config from a Cartesian product grid.  Produces
a ranked comparison CSV so the best config can be identified before
committing to a full-length training run.

Supports ``"repeats": N`` in the sweep config to run each combo N times
with different seeds, producing both a per-run CSV and an aggregated
summary CSV with mean/std across repeats.

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
import math
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
    ``(run_id, combo_id, repeat, config, n_games, eval_interval,
      eval_games, final_eval_games, seed, swept_keys)``.
    """
    run_id, combo_id, repeat, config, n_games, eval_interval, eval_games, final_eval_games, seed, swept_keys = args

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
    swept_params = {k: config[k] for k in swept_keys if k in config}

    return {
        "run_id": run_id,
        "combo_id": combo_id,
        "repeat": repeat,
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
# Aggregation
# ---------------------------------------------------------------------------

def _aggregate_results(
    results: list[dict], swept_keys: list[str],
) -> list[dict]:
    """Group results by combo_id, compute mean/std for key metrics.

    Returns one row per combo, sorted by mean_win_rate descending
    (tiebreak by mean_pp_delta).
    """
    from collections import defaultdict

    by_combo: dict[int, list[dict]] = defaultdict(list)
    for r in results:
        by_combo[r["combo_id"]].append(r)

    aggregated: list[dict] = []
    for combo_id, runs in by_combo.items():
        n = len(runs)
        win_rates = [r["win_rate"] for r in runs]
        pp_deltas = [r["pp_delta"] for r in runs]
        mean_pps = [r["mean_pp"] for r in runs]

        mean_wr = sum(win_rates) / n
        mean_ppd = sum(pp_deltas) / n
        mean_pp = sum(mean_pps) / n

        row: dict = {
            "combo_id": combo_id,
            "repeats": n,
            "mean_win_rate": round(mean_wr, 4),
            "std_win_rate": round(_std(win_rates), 4),
            "mean_pp_delta": round(mean_ppd, 2),
            "std_pp_delta": round(_std(pp_deltas), 2),
            "mean_pp": round(mean_pp, 2),
            "min_win_rate": round(min(win_rates), 4),
            "max_win_rate": round(max(win_rates), 4),
        }
        # Copy swept params from first run (same for all repeats)
        for k in swept_keys:
            row[k] = runs[0].get(k)
        aggregated.append(row)

    aggregated.sort(key=lambda r: (-r["mean_win_rate"], -r["mean_pp_delta"]))
    for rank, r in enumerate(aggregated, 1):
        r["rank"] = rank
    return aggregated


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))


# ---------------------------------------------------------------------------
# Sweep runner
# ---------------------------------------------------------------------------

def run_sweep(sweep_config_path: Path, seed: int | None = None) -> list[dict]:
    """Run a full hyperparameter sweep and write results CSV.

    Returns per-run results sorted by win_rate descending.
    If ``repeats > 1``, also writes an aggregated summary CSV.
    """
    sweep_cfg = json.loads(Path(sweep_config_path).read_text())
    base_config = json.loads(Path(sweep_cfg["base_config"]).read_text())

    n_games = int(sweep_cfg.get("screening_games", 2000))
    eval_interval = int(sweep_cfg.get("screening_eval_interval", 500))
    eval_games = int(sweep_cfg.get("screening_eval_games", 50))
    final_eval_games = int(sweep_cfg.get("final_eval_games", 100))
    max_workers = sweep_cfg.get("max_workers") or os.cpu_count() or 4
    repeats = int(sweep_cfg.get("repeats", 1))

    grid_combos = expand_grid(sweep_cfg["grid"])
    total_runs = len(grid_combos) * repeats
    console.print(
        f"[bold]Sweep:[/bold] {len(grid_combos)} configs × {repeats} repeat(s) "
        f"= {total_runs} runs × {n_games} games, {max_workers} workers"
    )

    # Build argument tuples: one per (combo, repeat)
    swept_keys = list(sweep_cfg["grid"].keys())
    work_items: list[tuple] = []
    run_id = 0
    for combo_id, combo in enumerate(grid_combos):
        config = {**base_config, **combo, "eval_interval": eval_interval}
        for repeat in range(repeats):
            # Each repeat gets a different seed offset
            run_seed = (seed + run_id) if seed is not None else None
            work_items.append(
                (run_id, combo_id, repeat, config, n_games, eval_interval,
                 eval_games, final_eval_games, run_seed, swept_keys)
            )
            run_id += 1

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

    # Sort per-run results: best win_rate first, tiebreak by pp_delta
    results.sort(key=lambda r: (-r["win_rate"], -r["pp_delta"]))
    for rank, r in enumerate(results, 1):
        r["rank"] = rank

    swept_keys = list(sweep_cfg["grid"].keys())

    # Write per-run CSV
    _write_results_csv(results, swept_keys)

    if repeats > 1:
        # Write aggregated summary CSV and print it
        aggregated = _aggregate_results(results, swept_keys)
        _write_summary_csv(aggregated, swept_keys)
        _print_top_summary(aggregated, swept_keys)
    else:
        _print_top_results(results, swept_keys)

    return results


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _write_results_csv(results: list[dict], swept_keys: list[str]) -> None:
    """Write per-run sweep results to ``output/sweep_results.csv``."""
    Path("output").mkdir(parents=True, exist_ok=True)
    out_path = Path("output") / "sweep_results.csv"

    fieldnames = [
        "rank", "run_id", "combo_id", "repeat",
        "win_rate", "mean_pp", "pp_delta",
        "final_epsilon", "elapsed_seconds",
    ] + swept_keys

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    console.print(f"\nPer-run results written to [cyan]{out_path}[/cyan]")


def _write_summary_csv(aggregated: list[dict], swept_keys: list[str]) -> None:
    """Write aggregated summary to ``output/sweep_summary.csv``."""
    out_path = Path("output") / "sweep_summary.csv"

    fieldnames = [
        "rank", "combo_id", "repeats",
        "mean_win_rate", "std_win_rate", "min_win_rate", "max_win_rate",
        "mean_pp_delta", "std_pp_delta", "mean_pp",
    ] + swept_keys

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in aggregated:
            writer.writerow(r)

    console.print(f"Summary results written to [cyan]{out_path}[/cyan]")


def _print_top_results(results: list[dict], swept_keys: list[str], n: int = 5) -> None:
    """Print a rich table of the top *n* per-run results."""
    table = Table(title=f"Top {min(n, len(results))} Sweep Results")
    table.add_column("Rank", style="bold", justify="right")
    table.add_column("Run", justify="right")
    table.add_column("Win Rate", justify="right", style="green")
    table.add_column("PP Delta", justify="right", style="cyan")
    table.add_column("Mean PP", justify="right")
    table.add_column("Time (s)", justify="right")
    for k in swept_keys:
        table.add_column(k, justify="right")

    for r in results[:n]:
        row = [
            str(r["rank"]),
            str(r["run_id"]),
            f"{r['win_rate']:.3f}",
            f"{r['pp_delta']:+.1f}",
            f"{r['mean_pp']:.1f}",
            f"{r['elapsed_seconds']:.0f}",
        ]
        row += [str(r.get(k, "")) for k in swept_keys]
        table.add_row(*row)

    console.print(table)


def _print_top_summary(aggregated: list[dict], swept_keys: list[str], n: int = 10) -> None:
    """Print a rich table of the top *n* aggregated combos."""
    table = Table(title=f"Top {min(n, len(aggregated))} Configs (averaged across repeats)")
    table.add_column("Rank", style="bold", justify="right")
    table.add_column("Combo", justify="right")
    table.add_column("Mean WR", justify="right", style="green")
    table.add_column("Std WR", justify="right", style="dim")
    table.add_column("Range WR", justify="right")
    table.add_column("Mean PPD", justify="right", style="cyan")
    for k in swept_keys:
        table.add_column(k, justify="right")

    for r in aggregated[:n]:
        row = [
            str(r["rank"]),
            str(r["combo_id"]),
            f"{r['mean_win_rate']:.3f}",
            f"{r['std_win_rate']:.3f}",
            f"{r['min_win_rate']:.2f}–{r['max_win_rate']:.2f}",
            f"{r['mean_pp_delta']:+.1f}",
        ]
        row += [str(r.get(k, "")) for k in swept_keys]
        table.add_row(*row)

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
    repeats = int(sweep_cfg.get("repeats", 1))
    total_runs = len(grid_combos) * repeats

    console.print(f"[bold]Hyperparameter Sweep[/bold]")
    console.print(f"  Base config: {sweep_cfg['base_config']}")
    console.print(f"  Grid size:   {len(grid_combos)} combinations")
    console.print(f"  Repeats:     {repeats}")
    console.print(f"  Total runs:  {total_runs}")
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
