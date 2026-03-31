"""Interactive board visualiser — runs a 4-RandomAgent game step by step.

Each turn is split into two phases:
  1. Place Workers — workers are retrieved and all 4 agents act.
  2. Rotate       — the physical board rotates; player labels update.

This lets you inspect where every token landed before the rotation clears
short-lived workers.

Usage:
    python ui.py                      # manual stepping
    python ui.py --auto               # auto-run at 500 ms/phase
    python ui.py --seed 7             # fixed seed
    python ui.py --auto --delay 200   # auto-run at 200 ms/phase
"""

import argparse
import tkinter as tk

from src.ai.random_agent import RandomAgent
from src.game.board import setup_game
from src.game.data_loader import GameDataLoader
from src.game.scoring import score_game, winner
from src.game.simulation import run_placements, run_rotation
from src.game.state import GameState
from src.ui.board_display import BoardDisplay

# Phase labels
_PHASE_PLACE  = "place"
_PHASE_ROTATE = "rotate"


def main() -> None:
    parser = argparse.ArgumentParser(description="Fromage board visualiser")
    parser.add_argument("--seed",  type=int, default=42)
    parser.add_argument("--auto",  action="store_true")
    parser.add_argument("--delay", type=int, default=500)
    args = parser.parse_args()

    data   = GameDataLoader()
    agents = [RandomAgent(data, seed=args.seed + i) for i in range(4)]

    display = BoardDisplay(data)

    # ── game state & history ───────────────────────────────────────────────
    # Each history entry is (phase_label, GameState) recorded *before* that
    # phase runs, so browsing shows what the board looked like at each moment.
    #
    # history[0] = ("place", initial_state)  ← start of turn 1 placement
    # history[1] = ("rotate", post-placement state)
    # history[2] = ("place", post-rotation state)  ← start of turn 2
    # …

    initial_state = setup_game(data, args.seed)
    history: list[tuple[str, GameState]] = [(_PHASE_PLACE, initial_state)]
    view_idx = 0
    game_over = False

    status_var = tk.StringVar()

    # ── helpers ────────────────────────────────────────────────────────────

    def current_state():
        return history[view_idx][1]

    def current_phase():
        return history[view_idx][0]

    def at_tip() -> bool:
        return view_idx == len(history) - 1

    def refresh() -> None:
        state = current_state()
        display.update(state)

        if game_over and at_tip():
            scores = score_game(state, data)
            wids   = winner(scores)
            wstr   = ", ".join(f"P{w}" for w in wids)
            status_var.set(f"Game over — Turn {state.turn_number} — Winner(s): {wstr}")
        else:
            phase = current_phase()
            phase_str = "Workers placed" if phase == _PHASE_ROTATE else "Pre-placement"
            pos   = f"{view_idx + 1}/{len(history)}"
            hist  = "  [history]" if not at_tip() else ""
            status_var.set(
                f"Turn {state.turn_number}  ·  {phase_str}  ({pos}){hist}"
            )

        btn_prev.config(state="normal" if view_idx > 0 else "disabled")
        can_fwd = not (game_over and at_tip())
        btn_fwd.config(state="normal" if can_fwd else "disabled")
        btn_action.config(
            text=_action_label(),
            state="normal" if at_tip() and not game_over else "disabled",
        )

    def _action_label() -> str:
        if current_phase() == _PHASE_PLACE:
            return "Place Workers ▶"
        return "Rotate Board ▶"

    def _advance() -> None:
        """Compute and append the next snapshot to history."""
        nonlocal game_over, view_idx
        _phase, state = history[-1]

        if _phase == _PHASE_PLACE:
            next_state = run_placements(state, agents, data)
            history.append((_PHASE_ROTATE, next_state))
        else:
            next_state = run_rotation(state)
            history.append((_PHASE_PLACE, next_state))
            if next_state.game_over:
                game_over = True

        view_idx = len(history) - 1

    def do_action() -> None:
        """Advance one phase from the tip."""
        if game_over or not at_tip():
            return
        _advance()
        refresh()

    def do_prev() -> None:
        nonlocal view_idx
        if view_idx > 0:
            view_idx -= 1
            refresh()

    def do_fwd() -> None:
        """Step forward through history, or advance if at the tip."""
        nonlocal view_idx
        if not at_tip():
            view_idx += 1
            refresh()
        elif not game_over:
            do_action()

    def do_auto() -> None:
        if game_over:
            return
        if at_tip():
            do_action()
        display.root.after(args.delay, do_auto)

    # ── control bar ────────────────────────────────────────────────────────
    ctrl = tk.Frame(display.root, bg="#ECEFF1", pady=4)
    ctrl.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 6))

    btn_prev = tk.Button(ctrl, text="◀ Back",   width=10, command=do_prev)
    btn_prev.pack(side="left", padx=4)

    btn_fwd  = tk.Button(ctrl, text="Fwd ▶",    width=10, command=do_fwd)
    btn_fwd.pack(side="left", padx=4)

    btn_action = tk.Button(ctrl, text=_action_label(), width=16, command=do_action,
                           font=("Helvetica", 9, "bold"))
    btn_action.pack(side="left", padx=8)

    btn_run = tk.Button(ctrl, text="Run to End", width=12, command=do_auto)
    btn_run.pack(side="left", padx=4)

    tk.Label(ctrl, textvariable=status_var, bg="#ECEFF1", fg="#37474F",
             font=("Helvetica", 9)).pack(side="left", padx=8)

    display.root.bind("<Left>",  lambda _: do_prev())
    display.root.bind("<Right>", lambda _: do_fwd())
    display.root.bind("<space>", lambda _: do_action())

    refresh()

    if args.auto:
        display.root.after(args.delay, do_auto)

    display.root.mainloop()


if __name__ == "__main__":
    main()
