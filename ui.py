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
from src.game.board import retrieve_workers, setup_game
from src.game.data_loader import GameDataLoader
from src.game.scoring import score_game, winner
from src.game.simulation import run_placements, run_rotation
from src.game.state import GameState
from src.ui.board_display import BoardDisplay
from src.ui.styles import (
    BG_INPUT,
    BG_SURFACE_ALT,
    BORDER_SUBTLE,
    BTN_ACCENT_BG,
    BTN_ACCENT_FG,
    BTN_ACTIVE_BG,
    BTN_BG,
    BTN_FG,
    FG_PRIMARY,
    FG_SECONDARY,
    FONT_BODY_BOLD,
    FONT_SMALL,
    FONT_SMALL_BOLD,
    FONT_TINY,
    FONT_TINY_BOLD,
    PLAYER_COLOURS,
    STATUS_BG,
    STATUS_FG,
)

# Phase labels
_PHASE_PLACE = "place"
_PHASE_ROTATE = "rotate"

# Structure slot names — index matches structures_unlocked list
_STRUCT_NAMES = ["Barn", "Dock", "Grnhs", "HQ"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fromage board visualiser")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--delay", type=int, default=500)
    args = parser.parse_args()

    data = GameDataLoader()
    agents = [RandomAgent(data, seed=args.seed + i) for i in range(4)]

    display = BoardDisplay(data)

    # ---- game state & history ----------------------------------------------
    initial_state = setup_game(data, args.seed)
    history: list[tuple[str, GameState]] = [(_PHASE_PLACE, initial_state)]
    view_idx = 0
    game_over = False

    status_var = tk.StringVar()

    # ---- helpers -----------------------------------------------------------

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
            wids = winner(scores)
            wstr = ", ".join(f"P{w}" for w in wids)
            status_var.set(f"Game over \u2014 Turn {state.turn_number} \u2014 Winner(s): {wstr}")
            display.update_scores(scores)
        else:
            display.clear_scores()
            phase = current_phase()
            phase_str = "Workers placed" if phase == _PHASE_ROTATE else "Pre-placement"
            pos = f"{view_idx + 1}/{len(history)}"
            hist = "  [history]" if not at_tip() else ""
            status_var.set(
                f"Turn {state.turn_number}  \u00b7  {phase_str}  ({pos}){hist}"
            )

        btn_prev.config(state="normal" if view_idx > 0 else "disabled")
        can_fwd = not (game_over and at_tip())
        btn_fwd.config(state="normal" if can_fwd else "disabled")
        btn_action.config(
            text=_action_label(),
            state="normal" if at_tip() and not game_over else "disabled",
        )

        # Update debug structure buttons to reflect current tip state
        tip_state = history[-1][1]
        can_debug = at_tip() and not game_over
        for pid in range(4):
            for slot in range(4):
                unlocked = tip_state.players[pid].structures_unlocked[slot]
                btn = _struct_btns[pid][slot]
                btn.config(
                    relief="flat" if unlocked else "raised",
                    bg="#2E7D32" if unlocked else BG_INPUT,
                    fg="white" if unlocked else FG_SECONDARY,
                    state="normal" if can_debug else "disabled",
                )

    def _action_label() -> str:
        if current_phase() == _PHASE_PLACE:
            return "Place Workers \u25b6"
        return "Rotate Board \u25b6"

    def _advance() -> None:
        nonlocal game_over, view_idx
        _phase, state = history[-1]

        if _phase == _PHASE_PLACE:
            next_state = run_placements(state, agents, data)
            history.append((_PHASE_ROTATE, next_state))
        else:
            next_state = retrieve_workers(run_rotation(state))
            history.append((_PHASE_PLACE, next_state))
            if next_state.game_over:
                game_over = True

        view_idx = len(history) - 1

    def do_action() -> None:
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

    def do_toggle_structure(player_id: int, slot_idx: int) -> None:
        """Debug: toggle structure slot on/off in the tip state."""
        if not at_tip() or game_over:
            return
        tip_state = history[-1][1]
        player = tip_state.players[player_id]
        player.structures_unlocked[slot_idx] = not player.structures_unlocked[slot_idx]
        refresh()

    # ---- control bar -------------------------------------------------------
    ctrl = tk.Frame(display.root, bg=STATUS_BG, pady=6)
    ctrl.grid(row=2, column=0, columnspan=3, sticky="ew", padx=0, pady=0)

    btn_prev = tk.Button(
        ctrl, text="\u25c0 Back", width=10, command=do_prev,
        bg=BTN_BG, fg=BTN_FG, activebackground=BTN_ACTIVE_BG,
        font=FONT_SMALL_BOLD, relief="flat", bd=0, cursor="hand2",
    )
    btn_prev.pack(side="left", padx=(10, 4))

    btn_fwd = tk.Button(
        ctrl, text="Fwd \u25b6", width=10, command=do_fwd,
        bg=BTN_BG, fg=BTN_FG, activebackground=BTN_ACTIVE_BG,
        font=FONT_SMALL_BOLD, relief="flat", bd=0, cursor="hand2",
    )
    btn_fwd.pack(side="left", padx=4)

    btn_action = tk.Button(
        ctrl, text=_action_label(), width=18, command=do_action,
        bg=BTN_ACCENT_BG, fg=BTN_ACCENT_FG, activebackground="#7C75FF",
        font=FONT_BODY_BOLD, relief="flat", bd=0, cursor="hand2",
    )
    btn_action.pack(side="left", padx=8)

    btn_run = tk.Button(
        ctrl, text="Run to End", width=12, command=do_auto,
        bg=BTN_BG, fg=BTN_FG, activebackground=BTN_ACTIVE_BG,
        font=FONT_SMALL_BOLD, relief="flat", bd=0, cursor="hand2",
    )
    btn_run.pack(side="left", padx=4)

    tk.Label(
        ctrl, textvariable=status_var,
        bg=STATUS_BG, fg=STATUS_FG,
        font=FONT_SMALL,
    ).pack(side="left", padx=10)

    # ---- debug: force-unlock structures ------------------------------------
    dbg = tk.LabelFrame(
        display.root, text="Debug \u2014 Force Structures (tip only)",
        font=FONT_TINY_BOLD,
        bg=BG_SURFACE_ALT, fg=FG_SECONDARY,
        bd=1, relief="flat",
        highlightbackground=BORDER_SUBTLE,
        highlightthickness=1,
        padx=8, pady=6,
    )
    dbg.grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 10))

    # Header row: slot labels
    for col, name in enumerate(_STRUCT_NAMES):
        tk.Label(
            dbg, text=name, font=FONT_TINY_BOLD,
            bg=BG_SURFACE_ALT, fg=FG_PRIMARY, width=6,
        ).grid(row=0, column=col + 1, padx=2)

    # One row per player
    _struct_btns: list[list[tk.Button]] = []
    for pid in range(4):
        tk.Label(
            dbg, text=f"P{pid}", font=FONT_TINY_BOLD,
            bg=BG_SURFACE_ALT, fg=PLAYER_COLOURS[pid], width=3,
        ).grid(row=pid + 1, column=0, padx=(0, 4))
        row_btns: list[tk.Button] = []
        for slot in range(4):
            btn = tk.Button(
                dbg, text=_STRUCT_NAMES[slot], width=6,
                font=FONT_TINY,
                bg=BG_INPUT, fg=FG_SECONDARY,
                activebackground=BTN_ACTIVE_BG,
                relief="flat", bd=0, cursor="hand2",
                command=lambda p=pid, s=slot: do_toggle_structure(p, s),
            )
            btn.grid(row=pid + 1, column=slot + 1, padx=2, pady=2)
            row_btns.append(btn)
        _struct_btns.append(row_btns)

    display.root.bind("<Left>", lambda _: do_prev())
    display.root.bind("<Right>", lambda _: do_fwd())
    display.root.bind("<space>", lambda _: do_action())

    refresh()

    if args.auto:
        display.root.after(args.delay, do_auto)

    display.root.mainloop()


if __name__ == "__main__":
    main()
