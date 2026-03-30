"""Tests for the simulation module. See 2-requirements.md section 6.3."""

import dataclasses

import pytest

from src.game.board import setup_game
from src.game.data_loader import GameDataLoader
from src.game.simulation import GameResult, StepRunner, run_game
from src.ai.random_agent import RandomAgent


@pytest.fixture
def data():
    return GameDataLoader()


def _make_agents(data, seed=0):
    return [RandomAgent(data, seed=seed + i) for i in range(4)]


# ---------------------------------------------------------------------------
# req 6.3.1 — one full game with 4 RandomAgents completes without error
# ---------------------------------------------------------------------------

def test_run_game_completes(data):
    """run_game with 4 RandomAgents finishes and returns a valid GameResult."""
    agents = _make_agents(data, seed=100)
    result = run_game(agents, data, seed=100)

    assert isinstance(result, GameResult)
    assert len(result.scores) == 4
    assert result.total_turns >= 1
    assert result.final_state.game_over is True
    for sb in result.scores:
        assert sb.total >= 0


# ---------------------------------------------------------------------------
# req 6.3.2 — same seed → identical GameResult
# ---------------------------------------------------------------------------

def test_run_game_deterministic_with_seed(data):
    """Two runs with the same seed produce identical scores and turn counts."""
    agents_a = _make_agents(data, seed=7)
    agents_b = _make_agents(data, seed=7)
    result_a = run_game(agents_a, data, seed=7)
    result_b = run_game(agents_b, data, seed=7)

    assert result_a.total_turns == result_b.total_turns
    assert result_a.winner_ids == result_b.winner_ids
    for sa, sb in zip(result_a.scores, result_b.scores):
        assert dataclasses.asdict(sa) == dataclasses.asdict(sb)


# ---------------------------------------------------------------------------
# req 6.3.3 — game_end_triggered and game_over semantics
# ---------------------------------------------------------------------------

def test_game_end_triggered_and_game_over(data):
    """game_over is True after the turn in which game_end_triggered was set."""
    agents = _make_agents(data, seed=42)
    result = run_game(agents, data, seed=42)

    assert result.final_state.game_end_triggered is True
    assert result.final_state.game_over is True


def test_at_least_one_player_exhausted_tokens(data):
    """At least one player should have 0 cheese tokens remaining at game end."""
    agents = _make_agents(data, seed=3)
    result = run_game(agents, data, seed=3)
    min_remaining = min(p.cheese_tokens_remaining for p in result.final_state.players)
    assert min_remaining == 0


# ---------------------------------------------------------------------------
# StepRunner — interactive step-through
# ---------------------------------------------------------------------------

def test_step_runner_single_step(data):
    """StepRunner.step() advances the game by exactly one turn."""
    agents = _make_agents(data, seed=5)
    runner = StepRunner(agents, data, seed=5)
    assert runner.state.turn_number == 1
    runner.step()
    assert runner.state.turn_number == 2


def test_step_runner_run_to_end(data):
    """StepRunner.run_to_end() completes the game and returns a GameResult."""
    agents = _make_agents(data, seed=9)
    runner = StepRunner(agents, data, seed=9)
    result = runner.run_to_end()
    assert isinstance(result, GameResult)
    assert runner.is_done
    assert result.total_turns >= 1


def test_step_runner_result_matches_run_game(data):
    """StepRunner with the same seed produces the same turn count as run_game."""
    seed = 21
    agents_step = _make_agents(data, seed=seed)
    runner = StepRunner(agents_step, data, seed=seed)
    step_result = runner.run_to_end()

    agents_full = _make_agents(data, seed=seed)
    full_result = run_game(agents_full, data, seed=seed)

    assert step_result.total_turns == full_result.total_turns
    assert step_result.winner_ids == full_result.winner_ids
