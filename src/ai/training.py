"""Self-play training loop for the Q-learning agent.

Functions: train(), evaluate().
Handles epsilon decay, checkpointing, and periodic evaluation vs. RandomAgent.

Reward design
-------------
Terminal reward (last transition per player):
    score_total + tokens_placed / 16

  tokens_placed = 15 − cheese_tokens_remaining; the fractional tiebreaker is
  always < 1 PP so score differences always dominate. Using the raw score
  rather than a binary win/loss preserves cardinal information — a 45-point
  game and a 12-point game carry very different signal.

Intermediate rewards (all other transitions):
    Potential-based shaping: r(s, a, s') = partial_score(s') − partial_score(s)

  Partial score = Festival + Fromagerie + Bistro + Orders + Fruit deltas.
  Villes is excluded: region leads flip mid-game so intermediate villes
  rewards add noise rather than signal.
  This shaping is provably policy-invariant (Ng et al. 1999).

See requirements section 11.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import TYPE_CHECKING

from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeRemainingColumn

from src.ai.q_agent import QAgent
from src.ai.random_agent import RandomAgent
from src.game.board import retrieve_workers, rotate_board, setup_game
from src.game.engine import apply_turn
from src.game.scoring import (
    ScoreBreakdown,
    score_bistro,
    score_festival,
    score_fromagerie,
    score_fruit,
    score_orders,
    score_game,
    winner,
)
from src.game.simulation import MAX_TURNS_PER_GAME, run_game

if TYPE_CHECKING:
    from src.game.actions import TurnAction
    from src.game.data_loader import GameDataLoader
    from src.game.state import GameState

logger = logging.getLogger(__name__)

EVAL_INTERVAL: int = 500
CHECKPOINT_INTERVAL: int = 1000

# (pre_state, player_id, action, post_state, intermediate_reward)
_Transition = tuple["GameState", int, "TurnAction", "GameState", float]


def train(n_games: int, data: "GameDataLoader", config_path: Path) -> QAgent:
    """Train a QAgent via self-play for *n_games* games.

    Creates one QAgent whose weights are shared across all 4 player seats.
    Applies TD(0) updates in reverse chronological order after each game.
    Intermediate transitions use potential-based score-delta rewards;
    the final transition per player uses the terminal reward.

    Logs metrics every EVAL_INTERVAL games to ``output/training_log.jsonl``.
    Saves checkpoints every CHECKPOINT_INTERVAL games to ``models/``.
    Always saves the final model to ``models/trained_agent.npz``.

    Returns the trained QAgent.
    """
    config = json.loads(Path(config_path).read_text())

    epsilon_start: float = float(config.get("epsilon_start", 1.0))
    epsilon_end: float = float(config.get("epsilon_end", 0.05))
    epsilon_decay_games: int = int(config.get("epsilon_decay_games", 5000))
    model_save_dir = Path(config.get("model_save_dir", "models/"))
    eval_interval: int = int(config.get("eval_interval", EVAL_INTERVAL))
    checkpoint_interval: int = int(config.get("checkpoint_interval", CHECKPOINT_INTERVAL))

    Path("output").mkdir(parents=True, exist_ok=True)
    model_save_dir.mkdir(parents=True, exist_ok=True)
    log_path = Path("output") / "training_log.jsonl"
    log_path.write_text("", encoding="utf-8")  # clear previous run

    agent = QAgent(data=data, config=config)

    window_scores: list[float] = []
    status_text = "training…"

    progress_bar = Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeRemainingColumn(),
    )

    with progress_bar:
        task = progress_bar.add_task(status_text, total=n_games)

        for game_num in range(1, n_games + 1):
            # Decay epsilon linearly
            progress = min((game_num - 1) / max(epsilon_decay_games, 1), 1.0)
            agent._epsilon = epsilon_start - progress * (epsilon_start - epsilon_end)

            # Run one self-play game, collecting per-player transitions + rewards
            transitions, scores = _run_training_game(agent, data, seed=game_num)

            # Apply updates: intermediate rewards already stored; terminal computed here
            _apply_updates(agent, transitions, scores)

            mean_score = sum(s.total for s in scores) / 4.0
            window_scores.append(mean_score)

            # Periodic evaluation
            if game_num % eval_interval == 0:
                eval_result = evaluate(agent, 100, data)
                mean_window = sum(window_scores) / len(window_scores)
                std_window = _std(window_scores)

                log_entry = {
                    "game": game_num,
                    "epsilon": round(agent._epsilon, 4),
                    "win_rate": round(eval_result["win_rate"], 4),
                    "mean_score": round(mean_window, 2),
                    "std_score": round(std_window, 2),
                    "pp_delta": round(eval_result["mean_pp_delta_vs_random"], 2),
                }
                with log_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry) + "\n")

                status_text = (
                    f"ε={agent._epsilon:.3f} | win={eval_result['win_rate']:.2f}"
                    f" | score={mean_window:.1f}"
                )
                progress_bar.update(task, description=status_text)
                window_scores.clear()

            # Checkpoint
            if game_num % checkpoint_interval == 0:
                agent.save(model_save_dir / f"checkpoint_{game_num}.npz")

            progress_bar.advance(task)

    agent.save(model_save_dir / "trained_agent.npz")
    return agent


def evaluate(agent: QAgent, n_games: int, data: "GameDataLoader") -> dict:
    """Evaluate *agent* (player 0) vs. 3 RandomAgents over *n_games* games.

    Temporarily sets agent epsilon to 0 (greedy) during evaluation and
    restores it afterwards.

    Returns::

        {
            "win_rate": float,
            "mean_pp": float,
            "mean_pp_delta_vs_random": float,
        }
    """
    saved_epsilon = agent._epsilon
    agent._epsilon = 0.0  # greedy evaluation

    wins = 0
    total_q_pp = 0.0
    total_random_pp = 0.0

    try:
        for i in range(n_games):
            randoms = [RandomAgent(data=data, seed=i * 10 + j) for j in range(3)]
            agents = [agent, randoms[0], randoms[1], randoms[2]]
            result = run_game(agents, data, seed=i)

            q_score = next(s for s in result.scores if s.player_id == 0)
            random_scores = [s for s in result.scores if s.player_id != 0]

            if 0 in result.winner_ids:
                wins += 1
            total_q_pp += q_score.total
            total_random_pp += sum(s.total for s in random_scores) / 3.0
    finally:
        agent._epsilon = saved_epsilon

    win_rate = wins / n_games
    mean_pp = total_q_pp / n_games
    mean_random_pp = total_random_pp / n_games
    return {
        "win_rate": win_rate,
        "mean_pp": mean_pp,
        "mean_pp_delta_vs_random": mean_pp - mean_random_pp,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_training_game(
    agent: QAgent,
    data: "GameDataLoader",
    seed: int | None = None,
) -> tuple[list[_Transition], list[ScoreBreakdown]]:
    """Run one self-play game collecting transitions with intermediate rewards.

    Returns ``(transitions, scores)`` where each transition is
    ``(pre_state, player_id, action, post_state, intermediate_reward)``.
    The intermediate reward is the partial score delta for that placement
    (Festival + Fromagerie + Bistro + Orders + Fruit — Villes excluded).
    """
    state = setup_game(data, seed)
    transitions: list[_Transition] = []
    turns = 0

    while not state.game_over and turns < MAX_TURNS_PER_GAME:
        state = retrieve_workers(state)
        for player_id in range(4):
            pre_state = state
            action = agent.choose_action(state, player_id)
            state = apply_turn(state, player_id, action, data)
            intermediate_reward = _compute_placement_reward(pre_state, state, player_id, data)
            transitions.append((pre_state, player_id, action, state, intermediate_reward))
        state = rotate_board(state)
        state.turn_number += 1
        if state.game_end_triggered:
            state.game_over = True
        turns += 1

    if turns >= MAX_TURNS_PER_GAME:
        logger.warning("Training game hit safety cap of %d turns", MAX_TURNS_PER_GAME)

    scores = score_game(state, data)
    return transitions, scores


def _compute_placement_reward(
    pre_state: "GameState",
    post_state: "GameState",
    player_id: int,
    data: "GameDataLoader",
) -> float:
    """Potential-based shaping reward: partial_score(s') − partial_score(s).

    Covers Festival, Fromagerie, Bistro, Orders, and Fruit.
    Villes is excluded (terminal only — mid-game leads flip too often).
    """
    pre_player = pre_state.players[player_id]
    post_player = post_state.players[player_id]

    pre_all = [pc for p in pre_state.players for pc in p.cheese_tokens_on_board]
    post_all = [pc for p in post_state.players for pc in p.cheese_tokens_on_board]

    fest_delta = (
        score_festival(player_id, post_all, data.festival_spaces, data.scoring_festival)
        - score_festival(player_id, pre_all, data.festival_spaces, data.scoring_festival)
    )
    frm_delta = (
        score_fromagerie(player_id, post_all, data.fromagerie_shelves, data.fromagerie_spaces, data.scoring_fromagerie)
        - score_fromagerie(player_id, pre_all, data.fromagerie_shelves, data.fromagerie_spaces, data.scoring_fromagerie)
    )
    bis_delta = (
        score_bistro(player_id, post_all, data.bistro_spaces, data.scoring_bistro)
        - score_bistro(player_id, pre_all, data.bistro_spaces, data.scoring_bistro)
    )
    ord_delta = (
        score_orders(post_player.orders_completed, data.scoring_orders)
        - score_orders(pre_player.orders_completed, data.scoring_orders)
    )
    fruit_delta = score_fruit(post_player) - score_fruit(pre_player)

    return float(fest_delta + frm_delta + bis_delta + ord_delta + fruit_delta)


def _apply_updates(
    agent: QAgent,
    transitions: list[_Transition],
    scores: list[ScoreBreakdown],
) -> None:
    """Apply TD(0) updates in reverse chronological order for each player.

    Terminal reward (last transition): score_total + tokens_placed / 16.
    Intermediate transitions: use the stored potential-based shaping reward.
    """
    terminal_rewards: dict[int, float] = {
        s.player_id: s.total + s.tokens_placed / 16.0
        for s in scores
    }

    # Group transitions by player, preserving chronological order
    by_player: dict[int, list[_Transition]] = {pid: [] for pid in range(4)}
    for t in transitions:
        by_player[t[1]].append(t)

    for pid, player_transitions in by_player.items():
        terminal_reward = terminal_rewards[pid]
        for i, (pre_state, player_id, action, post_state, shaping_reward) in enumerate(
            reversed(player_transitions)
        ):
            # i == 0 is the chronologically last transition
            r = terminal_reward if i == 0 else shaping_reward
            agent.update(pre_state, player_id, action, r, post_state)


def _std(values: list[float]) -> float:
    """Population standard deviation of *values*."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)
