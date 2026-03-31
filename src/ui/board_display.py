"""Tkinter-based live board visualiser for Fromage.

BoardDisplay renders the four venue quadrants (Fromagerie, Bistro, Villes,
Festival) in a 2×2 grid. The 'Player N' label above each quadrant rotates
with the board. Cheese token colours reflect type; age is shown via border
colour; a small dot in the corner marks which player placed the token.

Intended for use with StepRunner for step-through debugging.

    runner = StepRunner(agents, data, seed=42, display=BoardDisplay(data))
    while not runner.is_done:
        runner.step()
    runner.display.close()
"""

from __future__ import annotations

import tkinter as tk
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.game.data_loader import GameDataLoader
    from src.game.state import GameState

# ---------------------------------------------------------------------------
# Visual constants
# ---------------------------------------------------------------------------

_CELL = 28          # px per cheese-space cell
_PAD  = 4           # px padding between cells

# Cheese type → fill colour
_CHEESE_FILL: dict[str, str] = {
    "SOFT": "#FFF9C4",   # cream
    "HARD": "#FFE082",   # amber
    "BLEU": "#90CAF9",   # sky blue
    "FREE": "#C8E6C9",   # free-sample: pale green
}
_EMPTY_FILL    = "#EEEEEE"
_EMPTY_OUTLINE = "#BDBDBD"

# Age → border colour
_AGE_OUTLINE: dict[str, str] = {
    "BRONZE": "#A1887F",
    "SILVER": "#90A4AE",
    "GOLD":   "#FFB300",
}

# Player 0-3 → accent colour
_PLAYER_COLOURS = ["#EF5350", "#42A5F5", "#66BB6A", "#FFA726"]


# ---------------------------------------------------------------------------
# BoardDisplay
# ---------------------------------------------------------------------------

class BoardDisplay:
    """Tkinter board visualiser.

    Args:
        data: Loaded GameDataLoader (used once to build space lookup tables).
    """

    def __init__(self, data: "GameDataLoader") -> None:
        # ── pre-build space lookup tables ──────────────────────────────────
        self._fromag_spaces = {s.space_id: s for s in data.fromagerie_spaces}
        self._bistro_spaces  = {s.space_id: s for s in data.bistro_spaces}
        self._villes_spaces  = {s.space_id: s for s in data.villes_spaces}
        self._festival_spaces = {(s.row, s.col): s for s in data.festival_spaces}

        fest = data.festival_spaces
        self._fest_rows = max(s.row for s in fest)
        self._fest_cols = max(s.col for s in fest)

        # ── build root window ──────────────────────────────────────────────
        self._root = tk.Tk()
        self._root.title("Fromage — Board Visualiser")
        self._root.resizable(False, False)
        self._root.configure(bg="#ECEFF1")

        self._build_ui()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # title bar
        top = tk.Frame(self._root, bg="#37474F", pady=5)
        top.grid(row=0, column=0, columnspan=2, sticky="ew")
        self._turn_label = tk.Label(
            top, text="Turn —", fg="white", bg="#37474F",
            font=("Helvetica", 12, "bold"),
        )
        self._turn_label.pack()

        # 2×2 quadrant grid
        grid_frame = tk.Frame(self._root, bg="#ECEFF1")
        grid_frame.grid(row=1, column=0, padx=8, pady=8)

        venues = ["FROMAGERIE", "BISTRO", "VILLES", "FESTIVAL"]
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        canvas_dims = {
            "FROMAGERIE": (3, 6),   # (cols, rows) in cell-grid units
            "BISTRO":     (2, 9),
            "VILLES":     (3, 6),
            "FESTIVAL":   (self._fest_cols, self._fest_rows),
        }

        self._quad_labels: dict[str, tk.Label] = {}
        self._canvases: dict[str, tk.Canvas] = {}

        for venue, (gr, gc) in zip(venues, positions):
            cols, rows = canvas_dims[venue]
            w = cols * (_CELL + _PAD) + _PAD
            h = rows * (_CELL + _PAD) + _PAD

            frame = tk.LabelFrame(
                grid_frame, text=venue,
                font=("Helvetica", 9, "bold"),
                bg="#ECEFF1", padx=4, pady=2,
            )
            frame.grid(row=gr, column=gc, padx=5, pady=5, sticky="nsew")

            lbl = tk.Label(frame, text="← Player —", font=("Helvetica", 8),
                           bg="#ECEFF1", fg="#757575")
            lbl.pack(anchor="w")
            self._quad_labels[venue] = lbl

            canvas = tk.Canvas(frame, width=w, height=h, bg="white",
                               highlightthickness=0)
            canvas.pack()
            self._canvases[venue] = canvas

        # sidebar: player stats
        sidebar = tk.Frame(self._root, bg="#ECEFF1", padx=6)
        sidebar.grid(row=1, column=1, sticky="n", pady=8)

        tk.Label(sidebar, text="Players", font=("Helvetica", 10, "bold"),
                 bg="#ECEFF1").pack(anchor="w", pady=(0, 4))

        self._player_labels: list[tk.Label] = []
        for pid in range(4):
            colour = _PLAYER_COLOURS[pid]
            pf = tk.Frame(sidebar, bd=2, relief="groove", bg="white", padx=6, pady=4)
            pf.pack(fill="x", pady=3, ipadx=2)
            lbl = tk.Label(pf, text=f"P{pid}", font=("Courier", 8),
                           justify="left", bg="white", fg=colour, anchor="w")
            lbl.pack(fill="x")
            self._player_labels.append(lbl)

        self._root.update()

    # ── cell geometry ──────────────────────────────────────────────────────

    @staticmethod
    def _cell_xy(row: int, col: int) -> tuple[int, int, int, int]:
        """Canvas coords for the cell at grid position (row, col), 0-indexed."""
        x1 = _PAD + col * (_CELL + _PAD)
        y1 = _PAD + row * (_CELL + _PAD)
        return x1, y1, x1 + _CELL, y1 + _CELL

    # ── token drawing ──────────────────────────────────────────────────────

    def _draw_space(
        self,
        canvas: tk.Canvas,
        row: int,
        col: int,
        fill: str,
        outline: str,
        player_id: int | None = None,
        width: int = 1,
    ) -> None:
        x1, y1, x2, y2 = self._cell_xy(row, col)
        canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=width)
        if player_id is not None:
            r = 5
            canvas.create_oval(
                x2 - r * 2 - 1, y1 + 1, x2 - 1, y1 + r * 2 + 1,
                fill=_PLAYER_COLOURS[player_id], outline="",
            )

    # ── public API ─────────────────────────────────────────────────────────

    def update(self, state: "GameState") -> None:
        """Redraw all quadrants and the sidebar from *state*."""
        self._turn_label.config(
            text=f"Turn {state.turn_number}   (rotation {state.rotation_index})"
        )
        self._update_quad_labels(state)
        self._update_venues(state)
        self._update_sidebar(state)
        self._root.update()

    @property
    def root(self) -> tk.Tk:
        """The underlying tkinter root window (for attaching extra widgets)."""
        return self._root

    def close(self) -> None:
        """Destroy the tkinter window."""
        self._root.destroy()

    # ── internal update helpers ────────────────────────────────────────────

    def _update_quad_labels(self, state: "GameState") -> None:
        from src.game.types import VENUE_ORDER
        for venue_idx, venue in enumerate(VENUE_ORDER):
            # which player currently faces this venue?
            player_id = (venue_idx - state.rotation_index) % 4
            colour = _PLAYER_COLOURS[player_id]
            self._quad_labels[venue.name].config(
                text=f"← Player {player_id}", fg=colour,
            )

    def _update_venues(self, state: "GameState") -> None:
        fromag: dict[int, int] = {}
        bistro: dict[int, int] = {}
        villes: dict[int, int] = {}
        festival: dict[tuple[int, int], int] = {}

        for player in state.players:
            pid = player.player_id
            for pc in player.cheese_tokens_on_board:
                vname = pc.venue.name
                if vname == "FROMAGERIE" and pc.space_id is not None:
                    fromag[pc.space_id] = pid
                elif vname == "BISTRO" and pc.space_id is not None:
                    bistro[pc.space_id] = pid
                elif vname == "VILLES" and pc.space_id is not None:
                    villes[pc.space_id] = pid
                elif vname == "FESTIVAL" and pc.row is not None and pc.col is not None:
                    festival[(pc.row, pc.col)] = pid

        self._redraw_fromagerie(fromag)
        self._redraw_bistro(bistro)
        self._redraw_villes(villes)
        self._redraw_festival(festival)

    def _redraw_fromagerie(self, occupied: dict[int, int]) -> None:
        c = self._canvases["FROMAGERIE"]
        c.delete("all")
        cheese_col = {"SOFT": 0, "HARD": 1, "BLEU": 2}
        for space in sorted(self._fromag_spaces.values(),
                             key=lambda s: (s.shelf_id, s.cheese_type.name)):
            row = space.shelf_id - 1
            col = cheese_col.get(space.cheese_type.name, 0)
            outline = _AGE_OUTLINE.get(space.age.name, _EMPTY_OUTLINE)
            pid = occupied.get(space.space_id)
            fill = _CHEESE_FILL.get(space.cheese_type.name, _EMPTY_FILL) if pid is not None else _EMPTY_FILL
            self._draw_space(c, row, col, fill, outline, pid, width=2 if pid is not None else 1)

    def _redraw_bistro(self, occupied: dict[int, int]) -> None:
        c = self._canvases["BISTRO"]
        c.delete("all")
        tables: dict[int, list] = defaultdict(list)
        for space in self._bistro_spaces.values():
            tables[space.table_id].append(space)
        for table_id in sorted(tables):
            plates = sorted(tables[table_id], key=lambda s: s.plate_age.name)
            row = table_id - 1
            for col, space in enumerate(plates):
                outline = _AGE_OUTLINE.get(space.plate_age.name, _EMPTY_OUTLINE)
                pid = occupied.get(space.space_id)
                fill = _CHEESE_FILL.get(space.cheese_type.name, _EMPTY_FILL) if pid is not None else _EMPTY_FILL
                self._draw_space(c, row, col, fill, outline, pid, width=2 if pid is not None else 1)

    def _redraw_villes(self, occupied: dict[int, int]) -> None:
        c = self._canvases["VILLES"]
        c.delete("all")
        for idx, space in enumerate(sorted(self._villes_spaces.values(),
                                           key=lambda s: s.space_id)):
            row, col = divmod(idx, 3)
            outline = _AGE_OUTLINE.get(space.age.name, _EMPTY_OUTLINE)
            pid = occupied.get(space.space_id)
            fill = _CHEESE_FILL.get(space.cheese_type.name, _EMPTY_FILL) if pid is not None else _EMPTY_FILL
            self._draw_space(c, row, col, fill, outline, pid, width=2 if pid is not None else 1)

    def _redraw_festival(self, occupied: dict[tuple[int, int], int]) -> None:
        c = self._canvases["FESTIVAL"]
        c.delete("all")
        for (row, col), space in self._festival_spaces.items():
            stype = space.space_type.name
            if stype == "FREE_SAMPLE":
                self._draw_space(c, row - 1, col - 1, _CHEESE_FILL["FREE"], "#81C784")
            elif stype == "EMPTY":
                self._draw_space(c, row - 1, col - 1, "#F5F5F5", "#E0E0E0")
            else:
                outline = _AGE_OUTLINE.get(
                    space.age.name if space.age else "BRONZE", _EMPTY_OUTLINE
                )
                pid = occupied.get((row, col))
                fill = (
                    _CHEESE_FILL.get(space.cheese_type.name if space.cheese_type else "SOFT", _EMPTY_FILL)
                    if pid is not None else _EMPTY_FILL
                )
                self._draw_space(c, row - 1, col - 1, fill, outline, pid,
                                 width=2 if pid is not None else 1)

    def _update_sidebar(self, state: "GameState") -> None:
        _res = {"STRUCTURE": "STR", "LIVESTOCK": "LST", "FRUIT": "FRT", "ORDER": "ORD"}
        for player in state.players:
            pid = player.player_id
            res_parts = [f"{_res[r.name]}:{v}" for r, v in player.resources.items()]
            workers_str = " ".join(
                f"{'●' if w.location.name == 'IN_HAND' else '○'}{w.cheese_type.name[0]}"
                for w in player.workers
            )
            text = (
                f"Player {pid}  (board {player.board_id})\n"
                f"  Tokens: {player.cheese_tokens_remaining:>2}  "
                f"Orders: {len(player.orders_completed)}\n"
                f"  {' '.join(res_parts)}\n"
                f"  {workers_str}"
            )
            self._player_labels[pid].config(text=text)
