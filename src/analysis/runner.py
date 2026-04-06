"""Batch game runner for generating statistical results.

Function: run_batch(n_games, agents, data, base_seed) -> list[GameResult].

See requirements section 7.2.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.game.simulation import GameResult, run_game

if TYPE_CHECKING:
    from src.ai.agent import Agent
    from src.game.data_loader import GameDataLoader

logger = logging.getLogger(__name__)


def run_batch(
    n_games: int,
    agents: list["Agent"],
    data: "GameDataLoader",
    base_seed: int | None = None,
) -> list[GameResult]:
    """Run *n_games* sequential games and return all results.

    If *base_seed* is provided, game *i* is run with seed ``base_seed + i``
    for full reproducibility.  Agents are reused across games.

    Logs progress at INFO level every 100 games.
    """
    results: list[GameResult] = []
    for i in range(n_games):
        seed = (base_seed + i) if base_seed is not None else None
        result = run_game(agents, data, seed=seed)
        results.append(result)
        if (i + 1) % 100 == 0:
            logger.info("Completed %d/%d games", i + 1, n_games)
    return results
