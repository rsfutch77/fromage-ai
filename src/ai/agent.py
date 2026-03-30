"""Abstract base class for all agents.

All agent implementations (RandomAgent, QAgent) must subclass Agent
and implement choose_action(state, player_id) -> TurnAction.

See requirements section 6.1.3.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.game.actions import TurnAction
    from src.game.state import GameState


class Agent(ABC):
    """Abstract base class for all game-playing agents."""

    @abstractmethod
    def choose_action(self, state: GameState, player_id: int) -> TurnAction:
        """Return the TurnAction this agent wants to play.

        Must always return a legal TurnAction (the skip-everything turn is
        always legal and must be a valid fallback).
        """
