"""Q-learning agent with linear or feedforward function approximation.

Implements ε-greedy action selection and TD(0) weight updates.
Supports save/load via .npz files.

Q(s, a) = w · φ(s, a)
  where φ(s, a) = concat(state_vector, one_hot(action_index, MAX_ACTIONS_PER_TURN))

Or optionally a 2-hidden-layer feedforward network (numpy-only).

See requirements section 10.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from src.ai.agent import Agent
from src.ai.state_encoder import STATE_VECTOR_SIZE, _BASE_SIZE, encode_state
from src.game.actions import MAX_ACTIONS_PER_TURN, TurnAction, all_legal_turn_actions

if TYPE_CHECKING:
    from src.game.data_loader import GameDataLoader
    from src.game.state import GameState

# NOTE: Saved models trained with STATE_VECTOR_SIZE=197 are incompatible with
# the enhanced encoder (292). Set use_enhanced_encoder=False in agent config
# to use legacy 197-feature encoding, or retrain from scratch.
_FEATURE_SIZE: int = STATE_VECTOR_SIZE + MAX_ACTIONS_PER_TURN  # 492
_HIDDEN: int = 64


class QAgent(Agent):
    """Q-learning agent using linear or feedforward function approximation.

    Linear (default): Q(s,a) = w · φ(s,a); weight vector shape (_FEATURE_SIZE,).
    Network: 2-hidden-layer feedforward, 64 units, ReLU, numpy only.

    *config* keys: epsilon_start, epsilon_end, alpha, gamma, use_network_approx.
    """

    def __init__(
        self,
        data: GameDataLoader,
        config: dict,
        seed: int | None = None,
    ) -> None:
        self._data = data
        self._config = config
        self._rng = random.Random(seed)
        self._np_rng = np.random.default_rng(seed)
        self._epsilon: float = float(config.get("epsilon_start", 1.0))
        self._alpha: float = float(config.get("alpha", 0.001))
        self._gamma: float = float(config.get("gamma", 0.95))
        self._use_network: bool = bool(config.get("use_network_approx", False))
        self._weight_decay: float = float(config.get("weight_decay", 1e-6))
        self._enhanced_encoder: bool = bool(config.get("use_enhanced_encoder", True))
        self._state_size: int = STATE_VECTOR_SIZE if self._enhanced_encoder else _BASE_SIZE
        self._feature_size: int = self._state_size + MAX_ACTIONS_PER_TURN

        if self._use_network:
            scale = 0.01
            self._params: dict[str, np.ndarray] = {
                "W1": self._np_rng.normal(0, scale, (self._feature_size, _HIDDEN)).astype(np.float64),
                "b1": np.zeros(_HIDDEN, dtype=np.float64),
                "W2": self._np_rng.normal(0, scale, (_HIDDEN, _HIDDEN)).astype(np.float64),
                "b2": np.zeros(_HIDDEN, dtype=np.float64),
                "W3": self._np_rng.normal(0, scale, (_HIDDEN, 1)).astype(np.float64),
                "b3": np.zeros(1, dtype=np.float64),
            }
        else:
            self._weights: np.ndarray = np.zeros(self._feature_size, dtype=np.float64)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def choose_action(self, state: GameState, player_id: int) -> TurnAction:
        """Return a TurnAction using ε-greedy policy."""
        legal = all_legal_turn_actions(state, player_id, self._data)
        if not legal:
            return TurnAction()
        if self._rng.random() < self._epsilon:
            return self._rng.choice(legal)
        state_vec = encode_state(state, player_id, self._data, enhanced=self._enhanced_encoder)
        q_values = [self._q_value(state_vec, i) for i in range(len(legal))]
        return legal[int(np.argmax(q_values))]

    def choose_action_with_info(
        self, state: GameState, player_id: int,
    ) -> tuple[TurnAction, np.ndarray, int, int]:
        """Return (action, state_vec, action_idx, n_legal) with cached info for training.

        Always computes the state encoding (even on random picks) so the
        caller can store it for the TD update without re-encoding later.
        """
        legal = all_legal_turn_actions(state, player_id, self._data)
        if not legal:
            return TurnAction(), np.zeros(self._state_size, dtype=np.float32), 0, 0
        state_vec = encode_state(state, player_id, self._data, enhanced=self._enhanced_encoder)
        if self._rng.random() < self._epsilon:
            idx = self._rng.randrange(len(legal))
            return legal[idx], state_vec, idx, len(legal)
        q_values = [self._q_value(state_vec, i) for i in range(len(legal))]
        idx = int(np.argmax(q_values))
        return legal[idx], state_vec, idx, len(legal)

    def update(
        self,
        state: GameState,
        player_id: int,
        action: TurnAction,
        reward: float,
        next_state: GameState,
    ) -> None:
        """TD(0) Q-learning weight update.

        w ← w + α(r + γ max_a' Q(s',a') − Q(s,a)) ∇Q(s,a)
        """
        legal_cur = all_legal_turn_actions(state, player_id, self._data)
        action_idx = next((i for i, a in enumerate(legal_cur) if a == action), 0)

        state_vec = encode_state(state, player_id, self._data, enhanced=self._enhanced_encoder)
        next_state_vec = encode_state(next_state, player_id, self._data, enhanced=self._enhanced_encoder)

        legal_next = all_legal_turn_actions(next_state, player_id, self._data)
        self.update_precomputed(state_vec, action_idx, reward, next_state_vec, len(legal_next))

    def update_precomputed(
        self,
        state_vec: np.ndarray,
        action_idx: int,
        reward: float,
        next_state_vec: np.ndarray,
        n_legal_next: int,
    ) -> None:
        """TD(0) update using pre-computed state vectors (avoids re-encoding)."""
        if n_legal_next > 0:
            max_q_next = max(
                self._q_value(next_state_vec, i) for i in range(n_legal_next)
            )
        else:
            max_q_next = 0.0

        q_sa = self._q_value(state_vec, action_idx)
        delta = reward + self._gamma * max_q_next - q_sa

        # Clip TD error to prevent weight explosion
        delta = float(np.clip(delta, -10.0, 10.0))

        if self._use_network:
            self._update_network(state_vec, action_idx, delta)
        else:
            phi = self._phi(state_vec, action_idx)
            # L2 weight decay to prevent unbounded growth
            self._weights *= (1.0 - self._weight_decay)
            self._weights += self._alpha * delta * phi

    def save(self, path: Path) -> None:
        """Serialise weights + hyperparameters to *path* (.npz)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        config_arr = np.array([json.dumps(self._config)], dtype=object)
        epsilon_arr = np.array([self._epsilon], dtype=np.float64)
        if self._use_network:
            np.savez(
                path,
                config=config_arr,
                epsilon=epsilon_arr,
                W1=self._params["W1"],
                b1=self._params["b1"],
                W2=self._params["W2"],
                b2=self._params["b2"],
                W3=self._params["W3"],
                b3=self._params["b3"],
            )
        else:
            np.savez(path, weights=self._weights, config=config_arr, epsilon=epsilon_arr)

    @classmethod
    def load(cls, path: Path, data: GameDataLoader) -> "QAgent":
        """Deserialise weights + hyperparameters from *path* (.npz)."""
        path = Path(path)
        npz = np.load(path, allow_pickle=True)
        config = json.loads(str(npz["config"][0]))
        agent = cls(data=data, config=config)
        agent._epsilon = float(npz["epsilon"][0])
        if config.get("use_network_approx", False):
            agent._params = {
                "W1": npz["W1"],
                "b1": npz["b1"],
                "W2": npz["W2"],
                "b2": npz["b2"],
                "W3": npz["W3"],
                "b3": npz["b3"],
            }
        else:
            agent._weights = npz["weights"]
        return agent

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _phi(self, state_vec: np.ndarray, action_idx: int) -> np.ndarray:
        """Feature vector: [state_vec; one_hot(action_idx, MAX_ACTIONS_PER_TURN)]."""
        one_hot = np.zeros(MAX_ACTIONS_PER_TURN, dtype=np.float32)
        if 0 <= action_idx < MAX_ACTIONS_PER_TURN:
            one_hot[action_idx] = 1.0
        return np.concatenate([state_vec, one_hot]).astype(np.float64)

    def _q_value(self, state_vec: np.ndarray, action_idx: int) -> float:
        """Compute Q(s, action_idx)."""
        phi = self._phi(state_vec, action_idx)
        if self._use_network:
            q, _ = self._forward(phi)
            return q
        return float(np.dot(self._weights, phi))

    def _forward(self, x: np.ndarray) -> tuple[float, dict]:
        """Feedforward pass. Returns (q_value, cache for backprop)."""
        z1 = x @ self._params["W1"] + self._params["b1"]
        h1 = np.maximum(0.0, z1)
        z2 = h1 @ self._params["W2"] + self._params["b2"]
        h2 = np.maximum(0.0, z2)
        q = float((h2 @ self._params["W3"] + self._params["b3"])[0])
        return q, {"x": x, "z1": z1, "h1": h1, "z2": z2, "h2": h2}

    def _update_network(self, state_vec: np.ndarray, action_idx: int, delta: float) -> None:
        """Gradient ascent on Q by delta (equivalent to minimising TD-error loss)."""
        phi = self._phi(state_vec, action_idx)
        _, cache = self._forward(phi)

        # Gradient of Q w.r.t. each parameter (chain rule, output layer first)
        dW3 = cache["h2"].reshape(-1, 1)
        db3 = np.ones(1)

        dh2 = self._params["W3"].flatten()
        dz2 = dh2 * (cache["z2"] > 0).astype(np.float64)
        dW2 = np.outer(cache["h1"], dz2)
        db2 = dz2

        dh1 = dz2 @ self._params["W2"].T
        dz1 = dh1 * (cache["z1"] > 0).astype(np.float64)
        dW1 = np.outer(cache["x"], dz1)
        db1 = dz1

        # Weight decay + gradient ascent: w += alpha * delta * grad_Q
        for key in ("W1", "b1", "W2", "b2", "W3", "b3"):
            self._params[key] *= (1.0 - self._weight_decay)
        self._params["W1"] += self._alpha * delta * dW1
        self._params["b1"] += self._alpha * delta * db1
        self._params["W2"] += self._alpha * delta * dW2
        self._params["b2"] += self._alpha * delta * db2
        self._params["W3"] += self._alpha * delta * dW3
        self._params["b3"] += self._alpha * delta * db3
