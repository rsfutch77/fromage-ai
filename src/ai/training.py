"""Self-play training loop for the Q-learning agent.

Functions: train(), evaluate().
Handles epsilon decay, checkpointing, and periodic evaluation vs. RandomAgent.

See requirements section 11.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import TYPE_CHECKING

from src.ai.q_agent import QAgent
from src.ai.random_agent import RandomAgent
from src.game.board import retrieve_workers, rotate_board, setup_game
from src.game.engine import apply_turn
from src.game.scoring import score_game, winner
from src.game.simulation import MAX_TURNS_PER_GAME, run_game

if TYPE_CHECKING:
    from src.game.actions import TurnAction
    from src.game.data_loader import GameDataLoader
    from src.game.scoring import ScoreBreakdown
    from src.game.state import GameState

logger = logging.getLogger(__name__)

EVAL_INTERVAL: int = 500
CHECKPOINT_INTERVAL: int = 1000

# Type alias for a recorded transition
_Transition = tuple["GameState", int, "TurnAction", "GameState"]


def train(n_games: int, data: "GameDataLoader", config_path: Path) -> QAgent:
    """Train a QAgent via self-play for *n_games* games.

    Creates one QAgent whose weights are shared across all 4 player seats.
    Applies TD(0) updates in reverse chronological order after each game
    (Monte Carlo-style within a Q-learning framework).

    Logs metrics every EVAL_INTERVAL games to ``output/training_log.jsonl``.
    Saves checkpoints every CHECKPOINT_INTERVAL games to ``models/``.
    Always saves the final model to ``models/trained_agent.npz``.

    Returns the trained QAgent.
    """
    config = json.loads(Path(config_path).read_text())

    epsilon_start: float = float(config.get("epsilon_start", 1.0))
    epsilon_end: float = float(config.get("epsilon_end", 0.05))
    epsilon_decay_games: int = int(config.get("epsilon_decay_games", 5000))
    reward_win: float = float(config.get("reward_win", 1.0))
    reward_loss: float = float(config.get("reward_loss", 0.0))
    reward_per_pp: float = float(config.get("reward_per_pp", 0.0))
    model_save_dir = Path(config.get("model_save_dir", "models/"))
    eval_interval: int = int(config.get("eval_interval", EVAL_INTERVAL))
    checkpoint_interval: int = int(config.get("checkpoint_interval", CHECKPOINT_INTERVAL))

    Path("output").mkdir(parents=True, exist_ok=True)
    model_save_dir.mkdir(parents=True, exist_ok=True)
    log_path = Path("output") / "training_log.jsonl"

    agent = QAgent(data=data, config=config)

    window_scores: list[float] = []

    for game_num in range(1, n_games + 1):
        # Decay epsilon linearly
        progress = min((game_num - 1) / max(epsilon_decay_games, 1), 1.0)
        agent._epsilon = epsilon_start - progress * (epsilon_start - epsilon_end)

        # Run one self-play game, collecting per-player transitions
        transitions, scores = _run_training_game(agent, data, seed=game_num)

        # Compute and apply updates
        winner_ids = winner(scores)
        _apply_updates(agent, transitions, scores, winner_ids, reward_win, reward_loss, reward_per_pp)

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

            logger.info(
                "Game %d/%d | ε=%.3f | win_rate=%.3f | mean_score=%.1f",
                game_num, n_games, agent._epsilon,
                eval_result["win_rate"], mean_window,
            )
            window_scores.clear()

        # Checkpoint
        if game_num % checkpoint_interval == 0:
            agent.save(model_save_dir / f"checkpoint_{game_num}.npz")
            logger.info("Saved checkpoint at game %d", game_num)

    agent.save(model_save_dir / "trained_agent.npz")
    logger.info("Training complete. Final model saved to %s", model_save_dir / "trained_agent.npz")
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
) -> tuple[list[_Transition], list["ScoreBreakdown"]]:
    """Run one self-play game with a single shared-weight agent for all seats.

    Returns ``(transitions, scores)`` where *transitions* is a flat list of
    ``(pre_state, player_id, action, post_state)`` tuples in chronological order.
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
            transitions.append((pre_state, player_id, action, state))
        state = rotate_board(state)
        state.turn_number += 1
        if state.game_end_triggered:
            state.game_over = True
        turns += 1

    if turns >= MAX_TURNS_PER_GAME:
        logger.warning("Training game hit safety cap of %d turns", MAX_TURNS_PER_GAME)

    scores = score_game(state, data)
    return transitions, scores


def _apply_updates(
    agent: QAgent,
    transitions: list[_Transition],
    scores: list["ScoreBreakdown"],
    winner_ids: list[int],
    reward_win: float,
    reward_loss: float,
    reward_per_pp: float,
) -> None:
    """Apply TD(0) updates in reverse chronological order for each player."""
    rewards: dict[int, float] = {}
    for score in scores:
        pid = score.player_id
        base = reward_win if pid in winner_ids else reward_loss
        rewards[pid] = base + reward_per_pp * score.total

    # Group transitions by player, preserving order
    by_player: dict[int, list[_Transition]] = {pid: [] for pid in range(4)}
    for t in transitions:
        by_player[t[1]].append(t)

    for pid, player_transitions in by_player.items():
        reward = rewards[pid]
        for pre_state, player_id, action, post_state in reversed(player_transitions):
            agent.update(pre_state, player_id, action, reward, post_state)


def _std(values: list[float]) -> float:
    """Population standard deviation of *values*."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)
