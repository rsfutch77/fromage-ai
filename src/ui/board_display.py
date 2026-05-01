"""Tkinter-based live board visualiser for Fromage.

BoardDisplay renders the four venue quadrants (Fromagerie, Bistro, Villes,
Festival) in a 2x2 grid. The 'Player N' label above each quadrant rotates
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

from src.ui._score_widgets import ScoreTable, VillesTable
from src.ui.styles import (
    AGE_OUTLINE,
    BG_PRIMARY,
    BG_SURFACE,
    BORDER_SUBTLE,
    CANVAS_BG,
    CELL_PAD,
    CELL_RADIUS,
    CELL_SIZE,
    CHEESE_FILL,
    EMPTY_FILL,
    EMPTY_OUTLINE,
    FG_MUTED,
    FG_PRIMARY,
    FONT_HEADING,
    FONT_SMALL,
    FONT_SMALL_BOLD,
    FONT_TITLE,
    PLAYER_COLOURS,
    RESOURCE_FILL,
)

if TYPE_CHECKING:
    from src.game.data_loader import GameDataLoader
    from src.game.state import GameState

_CELL = CELL_SIZE
_PAD = CELL_PAD


class BoardDisplay:
    """Tkinter board visualiser.

    Args:
        data: Loaded GameDataLoader (used once to build space lookup tables).
    """

    def __init__(self, data: "GameDataLoader") -> None:
        self._fromag_spaces = {s.space_id: s for s in data.fromagerie_spaces}
        self._bistro_spaces = {s.space_id: s for s in data.bistro_spaces}
        self._villes_spaces = {s.space_id: s for s in data.villes_spaces}
        self._festival_spaces = {(s.row, s.col): s for s in data.festival_spaces}
        self._region_names = [ct.region_name for ct in data.customer_tokens]
        customer_token_values: dict[str, tuple[int, int]] = {
            ct.region_name: (ct.win_value, ct.tie_value)
            for ct in data.customer_tokens
        }
        self._parlours: dict[int, list] = {}
        for p in data.milking_parlours:
            self._parlours.setdefault(p.board_id, []).append(p)
        for lst in self._parlours.values():
            lst.sort(key=lambda p: p.parlour_num)
        self._structure_costs: dict[int, list[int]] = {
            b.board_id: b.structure_costs for b in data.player_board_structures
        }

        fest = data.festival_spaces
        self._fest_rows = max(s.row for s in fest)
        self._fest_cols = max(s.col for s in fest)

        self._root = tk.Tk()
        self._root.title("Fromage")
        self._root.resizable(False, False)
        self._root.configure(bg=BG_PRIMARY)

        self._build_ui(customer_token_values)

    # ---- UI construction ---------------------------------------------------

    def _build_ui(self, customer_token_values: dict[str, tuple[int, int]]) -> None:
        # title bar
        top = tk.Frame(self._root, bg=BG_SURFACE, pady=8)
        top.grid(row=0, column=0, columnspan=3, sticky="ew")
        self._turn_label = tk.Label(
            top, text="Turn \u2014", fg=FG_PRIMARY, bg=BG_SURFACE,
            font=FONT_TITLE,
        )
        self._turn_label.pack()

        # 2x2 quadrant grid
        grid_frame = tk.Frame(self._root, bg=BG_PRIMARY)
        grid_frame.grid(row=1, column=0, padx=10, pady=10)

        venues = ["FROMAGERIE", "BISTRO", "VILLES", "FESTIVAL"]
        positions = [(0, 1), (1, 1), (1, 0), (0, 0)]
        canvas_dims = {
            "FROMAGERIE": (3, 7),
            "BISTRO": (3, 10),
            "VILLES": (3, 7),
            "FESTIVAL": (self._fest_cols, self._fest_rows + 1),
        }

        self._quad_labels: dict[str, tk.Label] = {}
        self._quad_frames: dict[str, tk.LabelFrame] = {}
        self._canvases: dict[str, tk.Canvas] = {}

        for venue, (gr, gc) in zip(venues, positions):
            cols, rows = canvas_dims[venue]
            w = cols * (_CELL + _PAD) + _PAD
            h = rows * (_CELL + _PAD) + _PAD

            frame = tk.LabelFrame(
                grid_frame, text=venue,
                font=FONT_HEADING,
                bg=BG_SURFACE, fg=FG_PRIMARY,
                bd=1, relief="flat",
                highlightbackground=BORDER_SUBTLE,
                highlightthickness=1,
                padx=6, pady=4,
            )
            frame.grid(row=gr, column=gc, padx=6, pady=6, sticky="nsew")
            self._quad_frames[venue] = frame

            lbl = tk.Label(
                frame, text="\u2190 Player \u2014",
                font=FONT_SMALL,
                bg=BG_SURFACE, fg=FG_MUTED,
            )
            lbl.pack(anchor="w")
            self._quad_labels[venue] = lbl

            if venue == "VILLES":
                row_frame = tk.Frame(frame, bg=BG_SURFACE)
                row_frame.pack()
                canvas = tk.Canvas(
                    row_frame, width=w, height=h, bg=CANVAS_BG,
                    highlightthickness=0, bd=0,
                )
                canvas.pack(side="left")
                self._canvases[venue] = canvas
                self._villes_table = VillesTable(
                    row_frame, self._region_names, customer_token_values,
                )
            else:
                canvas = tk.Canvas(
                    frame, width=w, height=h, bg=CANVAS_BG,
                    highlightthickness=0, bd=0,
                )
                canvas.pack()
                self._canvases[venue] = canvas

        # sidebar: player stats
        sidebar = tk.Frame(self._root, bg=BG_PRIMARY, padx=8)
        sidebar.grid(row=1, column=1, sticky="n", pady=10)

        tk.Label(
            sidebar, text="Players",
            font=FONT_HEADING, bg=BG_PRIMARY, fg=FG_PRIMARY,
        ).pack(anchor="w", pady=(0, 6))

        self._player_labels: list[tk.Label] = []
        for pid in range(4):
            colour = PLAYER_COLOURS[pid]
            pf = tk.Frame(
                sidebar, bg=BG_SURFACE,
                highlightbackground=colour, highlightthickness=2,
                padx=8, pady=6,
            )
            pf.pack(fill="x", pady=4, ipadx=2)
            lbl = tk.Label(
                pf, text=f"P{pid}",
                font=("Cascadia Mono", 9),
                justify="left", bg=BG_SURFACE, fg=colour, anchor="w",
            )
            lbl.pack(fill="x")
            self._player_labels.append(lbl)

        # score breakdown table (far right)
        score_frame = tk.Frame(self._root, bg=BG_PRIMARY, padx=8)
        score_frame.grid(row=1, column=2, sticky="n", pady=10)
        self._score_table = ScoreTable(score_frame)

        self._root.update()

    # ---- cell geometry -----------------------------------------------------

    @staticmethod
    def _cell_xy(row: int, col: int) -> tuple[int, int, int, int]:
        x1 = _PAD + col * (_CELL + _PAD)
        y1 = _PAD + row * (_CELL + _PAD)
        return x1, y1, x1 + _CELL, y1 + _CELL

    # ---- rounded rectangle helper ------------------------------------------

    @staticmethod
    def _rounded_rect(
        canvas: tk.Canvas,
        x1: int, y1: int, x2: int, y2: int,
        r: int,
        **kwargs,
    ) -> int:
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    # ---- token drawing -----------------------------------------------------

    def _draw_worker_ring(
        self, canvas: tk.Canvas, row: int, col: int, player_id: int,
    ) -> None:
        x1, y1, x2, y2 = self._cell_xy(row, col)
        inset = 4
        canvas.create_rectangle(
            x1 + inset, y1 + inset, x2 - inset, y2 - inset,
            outline=PLAYER_COLOURS[player_id], fill="", width=3,
        )

    def _draw_milking_parlour_marker(
        self, canvas: tk.Canvas, row: int, col: int, player_id: int,
    ) -> None:
        x1, y1, x2, y2 = self._cell_xy(row, col)
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        r = 6
        colour = PLAYER_COLOURS[player_id]
        canvas.create_polygon(
            cx, cy - r, cx + r, cy, cx, cy + r, cx - r, cy,
            fill=colour, outline=CANVAS_BG, width=1,
        )

    def _draw_resource_row(
        self, canvas: tk.Canvas, row_idx: int, resource_workers: dict[int, int],
    ) -> None:
        for col, (age_name, amount) in enumerate(
            [("BRONZE", 1), ("SILVER", 2), ("GOLD", 3)]
        ):
            outline = AGE_OUTLINE[age_name]
            self._draw_space(canvas, row_idx, col, RESOURCE_FILL, outline, width=2)
            pid = resource_workers.get(amount)
            if pid is not None:
                self._draw_worker_ring(canvas, row_idx, col, pid)
            x1, y1, x2, y2 = self._cell_xy(row_idx, col)
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            canvas.create_text(
                cx, cy, text=str(amount),
                font=FONT_SMALL_BOLD, fill="#9090D0",
            )

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
        self._rounded_rect(
            canvas, x1, y1, x2, y2, CELL_RADIUS,
            fill=fill, outline=outline, width=width,
        )
        if player_id is not None:
            r = 6
            canvas.create_oval(
                x2 - r * 2 - 1, y1 + 1, x2 - 1, y1 + r * 2 + 1,
                fill=PLAYER_COLOURS[player_id], outline="",
            )

    # ---- public API --------------------------------------------------------

    def update(self, state: "GameState") -> None:
        self._turn_label.config(
            text=f"Turn {state.turn_number}   (rotation {state.rotation_index})"
        )
        self._update_quad_labels(state)
        self._update_venues(state)
        self._update_sidebar(state)
        self._root.update()

    @property
    def root(self) -> tk.Tk:
        return self._root

    def close(self) -> None:
        self._root.destroy()

    def update_scores(self, breakdowns: list) -> None:
        self._score_table.update(breakdowns)

    def clear_scores(self) -> None:
        self._score_table.clear()

    # ---- internal update helpers -------------------------------------------

    def _update_quad_labels(self, state: "GameState") -> None:
        from src.game.types import VENUE_ORDER
        for venue_idx, venue in enumerate(VENUE_ORDER):
            player_id = (venue_idx - state.rotation_index) % 4
            resource = state.resource_facing(player_id)
            self._quad_frames[venue.name].config(
                text=f"{venue.name}  \u2014  {resource.name.capitalize()}"
            )
            colour = PLAYER_COLOURS[player_id]
            self._quad_labels[venue.name].config(
                text=f"\u2190 Player {player_id}", fg=colour,
            )

    def _update_venues(self, state: "GameState") -> None:
        fromag: dict[int, int] = {}
        bistro: dict[int, int] = {}
        villes: dict[int, int] = {}
        festival: dict[tuple[int, int], int] = {}

        w_fromag: dict[int, int] = {}
        w_bistro: dict[int, int] = {}
        w_villes: dict[int, int] = {}
        w_festival: dict[tuple[int, int], int] = {}

        mp_fromag: dict[int, int] = {}
        mp_bistro: dict[int, int] = {}
        mp_villes: dict[int, int] = {}
        mp_festival: dict[tuple[int, int], int] = {}

        resource_on_tile: dict[str, dict[int, int]] = {
            "FROMAGERIE": {}, "BISTRO": {}, "VILLES": {}, "FESTIVAL": {},
        }

        for player in state.players:
            pid = player.player_id
            for pc in player.cheese_tokens_on_board:
                vname = pc.venue.name
                mp = pc.from_milking_parlour
                if vname == "FROMAGERIE" and pc.space_id is not None:
                    fromag[pc.space_id] = pid
                    if mp:
                        mp_fromag[pc.space_id] = pid
                elif vname == "BISTRO" and pc.space_id is not None:
                    bistro[pc.space_id] = pid
                    if mp:
                        mp_bistro[pc.space_id] = pid
                elif vname == "VILLES" and pc.space_id is not None:
                    villes[pc.space_id] = pid
                    if mp:
                        mp_villes[pc.space_id] = pid
                elif vname == "FESTIVAL" and pc.row is not None and pc.col is not None:
                    festival[(pc.row, pc.col)] = pid
                    if mp:
                        mp_festival[(pc.row, pc.col)] = pid

            for w in player.workers:
                if w.location.name == "IN_HAND":
                    continue
                vname = w.venue.name if w.venue else None
                if w.location.name == "ON_RESOURCE_TILE" and w.space_id is not None:
                    if vname in resource_on_tile:
                        resource_on_tile[vname][w.space_id] = pid
                    continue
                if vname == "FROMAGERIE" and w.space_id is not None:
                    w_fromag[w.space_id] = pid
                elif vname == "BISTRO" and w.space_id is not None:
                    w_bistro[w.space_id] = pid
                elif vname == "VILLES" and w.space_id is not None:
                    w_villes[w.space_id] = pid
                elif vname == "FESTIVAL" and w.row is not None and w.col is not None:
                    w_festival[(w.row, w.col)] = pid

        self._redraw_fromagerie(fromag, w_fromag, mp_fromag, resource_on_tile["FROMAGERIE"])
        self._redraw_bistro(bistro, w_bistro, mp_bistro, resource_on_tile["BISTRO"])
        self._redraw_villes(villes, w_villes, mp_villes, resource_on_tile["VILLES"])
        self._redraw_festival(festival, w_festival, mp_festival, resource_on_tile["FESTIVAL"])

    def _redraw_fromagerie(
        self,
        occupied: dict[int, int],
        workers: dict[int, int],
        mp: dict[int, int],
        resource_workers: dict[int, int],
    ) -> None:
        c = self._canvases["FROMAGERIE"]
        c.delete("all")
        cheese_col = {"SOFT": 0, "HARD": 1, "BLEU": 2}
        n_rows = 0
        for space in sorted(
            self._fromag_spaces.values(),
            key=lambda s: (s.shelf_id, s.cheese_type.name),
        ):
            row = space.shelf_id - 1
            col = cheese_col.get(space.cheese_type.name, 0)
            n_rows = max(n_rows, row + 1)
            outline = AGE_OUTLINE.get(space.age.name, EMPTY_OUTLINE)
            pid = occupied.get(space.space_id)
            fill = (
                CHEESE_FILL.get(space.cheese_type.name, EMPTY_FILL)
                if pid is not None else EMPTY_FILL
            )
            self._draw_space(
                c, row, col, fill, outline, pid,
                width=2 if pid is not None else 1,
            )
            if space.space_id in workers:
                self._draw_worker_ring(c, row, col, workers[space.space_id])
            elif space.space_id in mp:
                self._draw_milking_parlour_marker(c, row, col, mp[space.space_id])
        self._draw_resource_row(c, n_rows, resource_workers)

    def _redraw_bistro(
        self,
        occupied: dict[int, int],
        workers: dict[int, int],
        mp: dict[int, int],
        resource_workers: dict[int, int],
    ) -> None:
        c = self._canvases["BISTRO"]
        c.delete("all")
        tables: dict[int, list] = defaultdict(list)
        for space in self._bistro_spaces.values():
            tables[space.table_id].append(space)
        n_rows = 0
        for table_id in sorted(tables):
            plates = sorted(tables[table_id], key=lambda s: s.plate_age.name)
            row = table_id - 1
            n_rows = max(n_rows, row + 1)
            for col, space in enumerate(plates):
                outline = AGE_OUTLINE.get(space.plate_age.name, EMPTY_OUTLINE)
                pid = occupied.get(space.space_id)
                fill = (
                    CHEESE_FILL.get(space.cheese_type.name, EMPTY_FILL)
                    if pid is not None else EMPTY_FILL
                )
                self._draw_space(
                    c, row, col, fill, outline, pid,
                    width=2 if pid is not None else 1,
                )
                if space.space_id in workers:
                    self._draw_worker_ring(c, row, col, workers[space.space_id])
                elif space.space_id in mp:
                    self._draw_milking_parlour_marker(c, row, col, mp[space.space_id])
        self._draw_resource_row(c, n_rows, resource_workers)

    def _redraw_villes(
        self,
        occupied: dict[int, int],
        workers: dict[int, int],
        mp: dict[int, int],
        resource_workers: dict[int, int],
    ) -> None:
        c = self._canvases["VILLES"]
        c.delete("all")
        n_rows = 0
        for idx, space in enumerate(
            sorted(self._villes_spaces.values(), key=lambda s: s.space_id)
        ):
            row, col = divmod(idx, 3)
            n_rows = max(n_rows, row + 1)
            outline = AGE_OUTLINE.get(space.age.name, EMPTY_OUTLINE)
            pid = occupied.get(space.space_id)
            fill = (
                CHEESE_FILL.get(space.cheese_type.name, EMPTY_FILL)
                if pid is not None else EMPTY_FILL
            )
            self._draw_space(
                c, row, col, fill, outline, pid,
                width=2 if pid is not None else 1,
            )
            if space.space_id in workers:
                self._draw_worker_ring(c, row, col, workers[space.space_id])
            elif space.space_id in mp:
                self._draw_milking_parlour_marker(c, row, col, mp[space.space_id])
        self._draw_resource_row(c, n_rows, resource_workers)
        self._villes_table.update(occupied, self._villes_spaces)

    def _redraw_festival(
        self,
        occupied: dict[tuple[int, int], int],
        workers: dict[tuple[int, int], int],
        mp: dict[tuple[int, int], int],
        resource_workers: dict[int, int],
    ) -> None:
        c = self._canvases["FESTIVAL"]
        c.delete("all")
        for (row, col), space in self._festival_spaces.items():
            stype = space.space_type.name
            if stype == "FREE_SAMPLE":
                self._draw_space(c, row - 1, col - 1, CHEESE_FILL["FREE"], "#4CAF50")
            elif stype == "EMPTY":
                self._draw_space(c, row - 1, col - 1, EMPTY_FILL, EMPTY_OUTLINE)
            else:
                outline = AGE_OUTLINE.get(
                    space.age.name if space.age else "BRONZE", EMPTY_OUTLINE
                )
                pid = occupied.get((row, col))
                fill = (
                    CHEESE_FILL.get(
                        space.cheese_type.name if space.cheese_type else "SOFT",
                        EMPTY_FILL,
                    )
                    if pid is not None else EMPTY_FILL
                )
                self._draw_space(
                    c, row - 1, col - 1, fill, outline, pid,
                    width=2 if pid is not None else 1,
                )
                if (row, col) in workers:
                    self._draw_worker_ring(c, row - 1, col - 1, workers[(row, col)])
                elif (row, col) in mp:
                    self._draw_milking_parlour_marker(
                        c, row - 1, col - 1, mp[(row, col)],
                    )
        self._draw_resource_row(c, self._fest_rows, resource_workers)

    @staticmethod
    def _fmt_order(oc) -> str:
        _cheese = {"SOFT": "S", "HARD": "H", "BLEU": "B"}
        _age = {"BRONZE": "Br", "SILVER": "Si", "GOLD": "Go"}
        return f"{_cheese[oc.cheese_type.name]}-{_age[oc.age.name]}"

    def _update_sidebar(self, state: "GameState") -> None:
        _res = {"STRUCTURE": "STR", "LIVESTOCK": "LST", "FRUIT": "FRT"}
        for player in state.players:
            pid = player.player_id
            res_parts = [
                f"{_res[r.name]}:{v}"
                for r, v in player.resources.items()
                if r.name in _res and r.name != "FRUIT"
            ]
            fruit_stock = next(
                (v for r, v in player.resources.items() if r.name == "FRUIT"), 0
            )
            fruit_str = (
                f"  Fruit: {fruit_stock} stock  "
                f"\u2192chz:{player.fruit_spent_on_fruited}  "
                f"\u2192jam:{player.fruit_spent_on_jam}"
            )

            def _wstr(w) -> str:
                if w.location.name == "IN_HAND":
                    return f"\u25cf{w.cheese_type.name[0]}"
                if w.location.name == "ON_BARN":
                    return f"\u25b2{w.cheese_type.name[0]}"
                return f"\u25cb{w.cheese_type.name[0]}"

            workers_str = " ".join(_wstr(w) for w in player.workers)
            parlours = self._parlours.get(player.board_id, [])
            parlour_parts = []
            for p in parlours:
                uses = player.milking_parlours_used[p.parlour_num - 1]
                spent = p.livestock_cost * uses
                parlour_parts.append(f"P{p.parlour_num}:{p.livestock_cost}LST({spent}spent)")
            parlour_str = "  ".join(parlour_parts)
            _slot_names = ["Barn", "Dock", "Grnhs", "HQ"]
            costs = self._structure_costs.get(player.board_id, [1, 2, 3, 4])
            barn_occupied = any(
                w.location.name == "ON_BARN" for w in player.workers
            )

            def _slot_str(i: int, unlocked: bool) -> str:
                name = _slot_names[i]
                cost = costs[i]
                if not unlocked:
                    return f"({name}:{cost}STR)"
                if i == 0 and barn_occupied:
                    return f"[\u25b2{name}:{cost}STR]"
                return f"[{name}:{cost}STR]"

            unlocked_str = " ".join(
                _slot_str(i, unlocked)
                for i, unlocked in enumerate(player.structures_unlocked)
            )
            hand_str = (
                " ".join(self._fmt_order(o) for o in player.order_cards_held) or "\u2014"
            )
            done_str = (
                " ".join(self._fmt_order(o) for o in player.orders_completed) or "\u2014"
            )
            text = (
                f"Player {pid}  (board {player.board_id})\n"
                f"  Tokens: {player.cheese_tokens_remaining:>2}\n"
                f"  {' '.join(res_parts)}\n"
                f"{fruit_str}\n"
                f"  {workers_str}\n"
                f"  {unlocked_str}\n"
                f"  {parlour_str}\n"
                f"  Hand: {hand_str}\n"
                f"  Done: {done_str}"
            )
            self._player_labels[pid].config(text=text)
