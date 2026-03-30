"""Random agent baseline: selects a uniformly random legal action each turn.

Used to establish baseline win rates and score distributions before
training the Q-learning agent.

See requirements section 7.1.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from src.ai.agent import Agent
from src.game.actions import TurnAction, all_legal_turn_actions

if TYPE_CHECKING:
    from src.game.data_loader import GameDataLoader
    from src.game.state import GameState


class RandomAgent(Agent):
    """Selects a uniformly random legal TurnAction each turn.

    Accepts an optional *seed* for reproducible play.  The agent never raises
    an error: if only the skip-everything turn is legal it returns that.
    """

    def __init__(self, data: GameDataLoader, seed: int | None = None) -> None:
        self._data = data
        self._rng = random.Random(seed)

    def choose_action(self, state: GameState, player_id: int) -> TurnAction:
        actions = all_legal_turn_actions(state, player_id, self._data)
        return self._rng.choice(actions)
