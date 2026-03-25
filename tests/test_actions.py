"""Tests for legal move generation. See 2-requirements.md section 3.2.6."""

import pytest

from src.game.actions import (
    GatherAction,
    MakeCheeseAction,
    MilkingParlourAction,
    TurnAction,
    UnlockStructureAction,
    all_legal_turn_actions,
    legal_gather_actions,
    legal_make_cheese_actions,
    legal_milking_parlour_actions,
    legal_unlock_actions,
    MAX_ACTIONS_PER_TURN,
)
from src.game.board import setup_game
from src.game.data_loader import GameDataLoader
from src.game.state import GameState, PlayerState, Worker
from src.game.types import (
    CheeseType,
    ResourceType,
    VenueType,
    WorkerLocation,
)


@pytest.fixture(scope="module")
def data():
    return GameDataLoader()


@pytest.fixture
def fresh_state(data):
    """A freshly set-up game state with seed=0."""
    return setup_game(data, seed=0)


# ---------------------------------------------------------------------------
# 3.2.6 — Required tests
# ---------------------------------------------------------------------------

class TestAllLegalTurnActions:
    def test_fresh_state_returns_nonempty(self, fresh_state, data):
        """all_legal_turn_actions for a fresh game returns a non-empty list."""
        actions = all_legal_turn_actions(fresh_state, 0, data)
        assert len(actions) > 0

    def test_result_capped_at_max(self, fresh_state, data):
        """Result never exceeds MAX_ACTIONS_PER_TURN."""
        for pid in range(4):
            actions = all_legal_turn_actions(fresh_state, pid, data)
            assert len(actions) <= MAX_ACTIONS_PER_TURN

    def test_all_results_are_turn_actions(self, fresh_state, data):
        actions = all_legal_turn_actions(fresh_state, 0, data)
        for a in actions:
            assert isinstance(a, TurnAction)


class TestLegalMakeCheese:
    def test_no_workers_in_hand_cannot_make_cheese(self, fresh_state, data):
        """A player with no workers in hand cannot make cheese."""
        import copy
        state = copy.deepcopy(fresh_state)
        # Put all workers of player 0 on the resource tile.
        for w in state.players[0].workers:
            w.location = WorkerLocation.ON_RESOURCE_TILE
            w.venue = None
            w.space_id = 1
            w.return_after_rotation = 1

        actions = legal_make_cheese_actions(state, 0, data)
        # Only None (skip) should remain.
        assert actions == [None]

    def test_no_tokens_remaining_cannot_make_cheese(self, fresh_state, data):
        """A player with 0 cheese tokens remaining cannot make cheese."""
        import copy
        state = copy.deepcopy(fresh_state)
        state.players[0].cheese_tokens_remaining = 0

        actions = legal_make_cheese_actions(state, 0, data)
        assert actions == [None]

    def test_skip_always_included(self, fresh_state, data):
        """None (skip) is always in the make-cheese choices."""
        actions = legal_make_cheese_actions(fresh_state, 0, data)
        assert None in actions

    def test_facing_venue_respected(self, fresh_state, data):
        """All non-skip cheese actions target the venue currently facing the player."""
        for pid in range(4):
            facing = fresh_state.venue_facing(pid)
            actions = legal_make_cheese_actions(fresh_state, pid, data)
            for a in actions:
                if a is not None:
                    assert a.venue == facing, (
                        f"Player {pid} facing {facing} but got action for {a.venue}"
                    )

    def test_no_fruit_excludes_fruited_spaces(self, data):
        """A space with fruit_requirement != NONE is excluded when player has 0 Fruit."""
        import copy
        # Determine which venue player 0 faces in a fresh state and whether
        # any spaces there require fruit.
        state = setup_game(data, seed=42)
        state = copy.deepcopy(state)
        # Force player 0's fruit to 0.
        state.players[0].resources[ResourceType.FRUIT] = 0

        facing = state.venue_facing(0)
        actions = legal_make_cheese_actions(state, 0, data)
        for a in actions:
            if a is None:
                continue
            # Verify the action's space doesn't require fruit.
            if facing == VenueType.FROMAGERIE:
                sp = next(s for s in data.fromagerie_spaces if s.space_id == a.space_id)
                from src.game.types import FruitRequirement
                assert sp.fruit_requirement == FruitRequirement.NONE
            elif facing == VenueType.BISTRO:
                sp = next(s for s in data.bistro_spaces if s.space_id == a.space_id)
                from src.game.types import FruitRequirement
                assert sp.fruit_requirement == FruitRequirement.NONE


class TestLegalGatherActions:
    def test_skip_always_included(self, fresh_state, data):
        assert None in legal_gather_actions(fresh_state, 0, data)

    def test_occupied_space_excluded(self, fresh_state, data):
        """A resource space occupied by this player's worker is excluded."""
        import copy
        state = copy.deepcopy(fresh_state)
        # Place player 0's first worker on space 2.
        state.players[0].workers[0].location = WorkerLocation.ON_RESOURCE_TILE
        state.players[0].workers[0].space_id = 2
        state.players[0].workers[0].return_after_rotation = 1

        actions = legal_gather_actions(state, 0, data)
        for a in actions:
            if a is not None:
                assert a.resource_space != 2

    def test_barn_excluded_when_not_unlocked(self, fresh_state, data):
        """use_barn=True actions are absent when Barn is not unlocked."""
        actions = legal_gather_actions(fresh_state, 0, data)
        for a in actions:
            if a is not None:
                assert not a.use_barn

    def test_barn_included_when_unlocked(self, fresh_state, data):
        """use_barn=True actions appear when slot 1 (Barn) is unlocked."""
        import copy
        state = copy.deepcopy(fresh_state)
        state.players[0].structures_unlocked[0] = True  # unlock slot 1 (Barn)

        actions = legal_gather_actions(state, 0, data)
        barn_actions = [a for a in actions if a is not None and a.use_barn]
        assert len(barn_actions) > 0


class TestLegalMilkingParlour:
    def test_insufficient_livestock_excluded(self, fresh_state, data):
        """A parlour with insufficient livestock is excluded."""
        import copy
        state = copy.deepcopy(fresh_state)
        # Set livestock to 0 so no parlour can be used.
        state.players[0].resources[ResourceType.LIVESTOCK] = 0

        combos = legal_milking_parlour_actions(state, 0, data)
        # Only empty combination should remain.
        assert combos == [[]]

    def test_empty_combination_always_present(self, fresh_state, data):
        combos = legal_milking_parlour_actions(fresh_state, 0, data)
        assert [] in combos

    def test_already_used_parlour_excluded(self, fresh_state, data):
        """A parlour already used this game is excluded."""
        import copy
        state = copy.deepcopy(fresh_state)
        # Give lots of livestock.
        state.players[0].resources[ResourceType.LIVESTOCK] = 10
        # Mark all parlours as used.
        state.players[0].milking_parlours_used = [True, True, True, True]

        combos = legal_milking_parlour_actions(state, 0, data)
        assert combos == [[]]


class TestLegalUnlockActions:
    def test_no_structure_resources_only_empty(self, fresh_state, data):
        """With 0 Structure resources, only the empty sequence is returned."""
        import copy
        state = copy.deepcopy(fresh_state)
        state.players[0].resources[ResourceType.STRUCTURE] = 0
        state.players[0].structures_unlocked = [False, False, False, False]

        seqs = legal_unlock_actions(state, 0)
        assert seqs == [[]]

    def test_one_structure_unlocks_slot_1(self, fresh_state, data):
        """With 1 Structure resource and no slots unlocked, can unlock slot 1."""
        import copy
        state = copy.deepcopy(fresh_state)
        state.players[0].resources[ResourceType.STRUCTURE] = 1
        state.players[0].structures_unlocked = [False, False, False, False]

        seqs = legal_unlock_actions(state, 0)
        assert [UnlockStructureAction(slot=1)] in seqs

    def test_any_order_unlock_allowed(self, fresh_state, data):
        """Slot 3 can be unlocked even if slots 1 and 2 are not yet unlocked."""
        import copy
        state = copy.deepcopy(fresh_state)
        state.players[0].resources[ResourceType.STRUCTURE] = 10
        state.players[0].structures_unlocked = [False, False, False, False]

        seqs = legal_unlock_actions(state, 0)
        slot_sets = [frozenset(a.slot for a in seq) for seq in seqs]
        # Slot 3 alone should be a valid choice.
        assert frozenset({3}) in slot_sets

    def test_already_unlocked_slot_excluded(self, fresh_state, data):
        """A slot already unlocked cannot be unlocked again."""
        import copy
        state = copy.deepcopy(fresh_state)
        state.players[0].resources[ResourceType.STRUCTURE] = 10
        state.players[0].structures_unlocked = [True, False, False, False]  # slot 1 done

        seqs = legal_unlock_actions(state, 0)
        for seq in seqs:
            assert all(a.slot != 1 for a in seq)

    def test_empty_always_present(self, fresh_state, data):
        seqs = legal_unlock_actions(fresh_state, 0)
        assert [] in seqs

    def test_cannot_exceed_slot_4(self, data):
        """No sequences unlock beyond slot 4."""
        import copy
        state = setup_game(data, seed=1)
        state = copy.deepcopy(state)
        state.players[0].resources[ResourceType.STRUCTURE] = 100
        state.players[0].structures_unlocked = [False, False, False, False]

        seqs = legal_unlock_actions(state, 0)
        for seq in seqs:
            assert all(a.slot <= 4 for a in seq)
