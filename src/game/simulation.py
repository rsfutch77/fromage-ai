"""Full game simulation loop.

Functions: run_turn, run_game.
Defines GameResult dataclass and imports Agent from src.ai.agent.

See requirements section 6.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from collections.abc import Sequence
from typing import TYPE_CHECKING

from src.game.board import retrieve_workers, rotate_board, setup_game
from src.game.engine import apply_turn
from src.game.scoring import ScoreBreakdown, score_game, winner

if TYPE_CHECKING:
    from src.ai.agent import Agent
    from src.game.data_loader import GameDataLoader
    from src.game.state import GameState

logger = logging.getLogger(__name__)

# Safety cap: if a game exceeds this many turns, force-end it.
MAX_TURNS_PER_GAME: int = 500


# ---------------------------------------------------------------------------
# GameResult
# ---------------------------------------------------------------------------

@dataclass
class GameResult:
    """Complete result of a finished game."""
    scores: list[ScoreBreakdown]
    winner_ids: list[int]
    total_turns: int
    seed: int | None
    final_state: GameState


# ---------------------------------------------------------------------------
# Turn and game loop
# ---------------------------------------------------------------------------

def run_turn(
    state: GameState,
    agents: Sequence[Agent],
    data: GameDataLoader,
) -> GameState:
    """Execute one full turn for all 4 players.

    Steps:
    1. Retrieve workers due to return this rotation.
    2. Each player (0–3) chooses and applies their TurnAction.
    3. Rotate the board.
    4. Increment turn_number.
    5. Set game_over=True if game_end_triggered was set during this turn.
    """
    state = retrieve_workers(state)

    for player_id in range(4):
        action = agents[player_id].choose_action(state, player_id)
        state = apply_turn(state, player_id, action, data)

    # rotate_board returns a new GameState; mutate the new object for bookkeeping
    new_state = rotate_board(state)
    new_state.turn_number += 1

    if new_state.game_end_triggered:
        new_state.game_over = True

    return new_state


class StepRunner:
    """Interactive step-through wrapper for a single game.

    Useful for debugging and manual testing: call step() to advance one turn
    at a time and inspect state between turns.  Call run_to_end() to finish
    the remaining turns at full speed.

    Example::

        runner = StepRunner(agents, data, seed=42)
        while not runner.is_done:
            print(f"Turn {runner.state.turn_number}")
            runner.step()
        result = runner.result()
    """

    def __init__(
        self,
        agents: Sequence[Agent],
        data: GameDataLoader,
        seed: int | None = None,
    ) -> None:
        self._agents = agents
        self._data = data
        self._seed = seed
        self._state = setup_game(data, seed)
        self._turns = 0
        self._scores: list[ScoreBreakdown] | None = None

    @property
    def state(self) -> GameState:
        """Current game state (read-only snapshot)."""
        return self._state

    @property
    def is_done(self) -> bool:
        """True after the game ends."""
        return self._state.game_over

    def step(self) -> None:
        """Advance the game by exactly one turn.

        Does nothing if the game is already over.
        """
        if self._state.game_over:
            return
        self._state = run_turn(self._state, self._agents, self._data)
        self._turns += 1
        if self._turns >= MAX_TURNS_PER_GAME:
            logger.warning(
                "StepRunner reached safety cap of %d turns — forcing game_over",
                MAX_TURNS_PER_GAME,
            )
            self._state.game_over = True

    def run_to_end(self) -> GameResult:
        """Run all remaining turns and return the final GameResult."""
        while not self.is_done:
            self.step()
        return self.result()

    def result(self) -> GameResult:
        """Return the GameResult for the completed game.

        Raises RuntimeError if the game is not yet over.
        """
        if not self._state.game_over:
            raise RuntimeError("Game is not finished yet — call step() or run_to_end() first")
        if self._scores is None:
            self._scores = score_game(self._state, self._data)
        winner_ids = winner(self._scores)
        return GameResult(
            scores=self._scores,
            winner_ids=winner_ids,
            total_turns=self._turns,
            seed=self._seed,
            final_state=self._state,
        )


def run_game(
    agents: Sequence[Agent],
    data: GameDataLoader,
    seed: int | None = None,
) -> GameResult:
    """Run a complete game from setup to scoring.

    Uses *seed* for reproducible setup and (if agents use it) move selection.
    Returns a GameResult with full score breakdowns and winner list.
    """
    state = setup_game(data, seed)
    turns = 0

    while not state.game_over:
        state = run_turn(state, agents, data)
        turns += 1
        if turns >= MAX_TURNS_PER_GAME:
            logger.warning(
                "Game reached safety cap of %d turns — forcing game_over", MAX_TURNS_PER_GAME
            )
            state.game_over = True
            break

    scores = score_game(state, data)
    winner_ids = winner(scores)

    return GameResult(
        scores=scores,
        winner_ids=winner_ids,
        total_turns=turns,
        seed=seed,
        final_state=state,
    )
