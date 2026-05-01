"""Score breakdown table and Villes region table widgets for BoardDisplay."""

from __future__ import annotations

import tkinter as tk

from src.ui.styles import (
    BG_PRIMARY,
    BG_SURFACE,
    BG_SURFACE_ALT,
    FG_MUTED,
    FG_PRIMARY,
    FG_SECONDARY,
    FONT_HEADING,
    FONT_MONO,
    FONT_MONO_BOLD,
    PLAYER_COLOURS,
    TABLE_CELL_BG,
    TABLE_CELL_FG,
    TABLE_HEADER_BG,
    TABLE_SEPARATOR,
)

# Score-breakdown table rows: (ScoreBreakdown field name, display label)
_SCORE_ROW_DEFS: list[tuple[str, str]] = [
    ("festival",         "Festival"),
    ("villes",           "Customer"),
    ("fromagerie",       "Fromager"),
    ("bistro",           "Bistro"),
    ("orders",           "Orders"),
    ("fruit",            "Fruit"),
    ("headquarters",     "HQ"),
    ("unused_resources", "Unused"),
]


class ScoreTable:
    """Score breakdown table widget.

    Builds itself inside *parent* on construction.  Call update() with a list
    of ScoreBreakdown objects to fill in end-game numbers, or clear() to reset
    to dashes.
    """

    def __init__(self, parent: tk.Frame) -> None:
        tk.Label(
            parent, text="Score Breakdown",
            font=FONT_HEADING,
            bg=BG_PRIMARY, fg=FG_PRIMARY,
        ).pack(anchor="w", pady=(0, 6))

        tbl = tk.Frame(parent, bg=BG_SURFACE)
        tbl.pack(fill="x")

        # Header row
        tk.Label(
            tbl, text="", width=9, bg=TABLE_HEADER_BG,
            font=FONT_MONO,
        ).grid(row=0, column=0)
        for pid in range(4):
            tk.Label(
                tbl, text=f"P{pid}", width=4,
                bg=PLAYER_COLOURS[pid], fg="white",
                font=FONT_MONO_BOLD,
            ).grid(row=0, column=pid + 1, padx=1)

        self._score_cells: dict[str, dict[int, tk.Label]] = {}
        for row_idx, (field, label) in enumerate(_SCORE_ROW_DEFS):
            tk.Label(
                tbl, text=label, width=9, bg=BG_SURFACE,
                fg=FG_SECONDARY, font=FONT_MONO, anchor="w",
            ).grid(row=row_idx + 1, column=0)
            self._score_cells[field] = {}
            for pid in range(4):
                lbl = tk.Label(
                    tbl, text="\u2014", width=4,
                    bg=TABLE_CELL_BG, fg=TABLE_CELL_FG,
                    font=FONT_MONO,
                )
                lbl.grid(row=row_idx + 1, column=pid + 1, padx=1, pady=1)
                self._score_cells[field][pid] = lbl

        sep_row = len(_SCORE_ROW_DEFS) + 1
        tk.Frame(tbl, bg=TABLE_SEPARATOR, height=1).grid(
            row=sep_row, column=0, columnspan=5, sticky="ew", pady=3,
        )

        tk.Label(
            tbl, text="TOTAL", width=9, bg=BG_SURFACE,
            fg=FG_PRIMARY, font=FONT_MONO_BOLD, anchor="w",
        ).grid(row=sep_row + 1, column=0)
        self._total_cells: dict[int, tk.Label] = {}
        for pid in range(4):
            lbl = tk.Label(
                tbl, text="\u2014", width=4,
                bg=TABLE_CELL_BG, fg=TABLE_CELL_FG,
                font=FONT_MONO_BOLD,
            )
            lbl.grid(row=sep_row + 1, column=pid + 1, padx=1, pady=1)
            self._total_cells[pid] = lbl

    def update(self, breakdowns: list) -> None:
        bd_map: dict[int, object] = {b.player_id: b for b in breakdowns}

        for field, cells in self._score_cells.items():
            for pid, lbl in cells.items():
                bd = bd_map.get(pid)
                val = getattr(bd, field, 0) if bd else 0
                lbl.config(
                    text=str(val), bg=TABLE_CELL_BG, fg=TABLE_CELL_FG,
                    font=FONT_MONO,
                )

        max_total = max((b.total for b in breakdowns), default=0)
        for pid, lbl in self._total_cells.items():
            bd = bd_map.get(pid)
            val = bd.total if bd else 0
            if val == max_total:
                lbl.config(
                    text=str(val),
                    bg=PLAYER_COLOURS[pid], fg="white",
                    font=FONT_MONO_BOLD,
                )
            else:
                lbl.config(
                    text=str(val),
                    bg=TABLE_CELL_BG, fg=TABLE_CELL_FG,
                    font=FONT_MONO_BOLD,
                )

    def clear(self) -> None:
        for cells in self._score_cells.values():
            for lbl in cells.values():
                lbl.config(
                    text="\u2014", bg=TABLE_CELL_BG, fg=TABLE_CELL_FG,
                    font=FONT_MONO,
                )
        for lbl in self._total_cells.values():
            lbl.config(
                text="\u2014", bg=TABLE_CELL_BG, fg=TABLE_CELL_FG,
                font=FONT_MONO_BOLD,
            )


class VillesTable:
    """Villes region control table widget.

    Builds itself inside *parent* on construction.  Call update() after each
    board redraw to refresh token counts and leader highlighting.
    """

    def __init__(
        self,
        parent: tk.Frame,
        region_names: list[str],
        customer_token_values: dict[str, tuple[int, int]],
    ) -> None:
        self._region_names = region_names
        self._customer_token_values = customer_token_values

        tbl = tk.Frame(parent, bg=BG_SURFACE)
        tbl.pack(side="left", anchor="n", padx=(8, 0))

        # Header row
        tk.Label(
            tbl, text="", width=7, bg=TABLE_HEADER_BG,
            font=FONT_MONO,
        ).grid(row=0, column=0)
        for pid in range(4):
            tk.Label(
                tbl, text=f"P{pid}", width=3,
                bg=PLAYER_COLOURS[pid], fg="white",
                font=FONT_MONO_BOLD,
            ).grid(row=0, column=pid + 1, padx=1)

        self._cells: dict[str, dict[int, tk.Label]] = {}
        self._region_labels: dict[str, tk.Label] = {}
        for row_idx, region in enumerate(region_names):
            lbl = tk.Label(
                tbl, text=region, width=11, bg=BG_SURFACE,
                fg=FG_SECONDARY, font=FONT_MONO, anchor="w",
            )
            lbl.grid(row=row_idx + 1, column=0)
            self._region_labels[region] = lbl
            self._cells[region] = {}
            for pid in range(4):
                cell = tk.Label(
                    tbl, text="0", width=3,
                    bg=TABLE_CELL_BG, fg=TABLE_CELL_FG,
                    font=FONT_MONO,
                )
                cell.grid(row=row_idx + 1, column=pid + 1, padx=1, pady=1)
                self._cells[region][pid] = cell

    def update(self, occupied: dict[int, int], villes_spaces: dict) -> None:
        influence: dict[str, dict[int, int]] = {
            r: {p: 0 for p in range(4)} for r in self._region_names
        }
        for space_id, pid in occupied.items():
            sp = villes_spaces.get(space_id)
            if sp:
                for region in sp.regions:
                    if region in influence:
                        influence[region][pid] += 1

        for region, cells in self._cells.items():
            inf = influence[region]
            max_count = max(inf.values())
            leaders = {p for p, c in inf.items() if c == max_count and max_count > 0}

            win_val, tie_val = self._customer_token_values.get(region, (0, 0))
            rlbl = self._region_labels[region]
            if not leaders:
                rlbl.config(
                    text=region, fg=FG_SECONDARY, bg=BG_SURFACE,
                    font=FONT_MONO,
                )
            elif len(leaders) == 1:
                sole = next(iter(leaders))
                rlbl.config(
                    text=f"{region} ({win_val})",
                    fg=PLAYER_COLOURS[sole], bg=BG_SURFACE,
                    font=FONT_MONO_BOLD,
                )
            else:
                rlbl.config(
                    text=f"{region} ({tie_val})",
                    fg=FG_MUTED, bg=BG_SURFACE,
                    font=FONT_MONO,
                )

            for pid, lbl in cells.items():
                count = inf[pid]
                if pid in leaders and len(leaders) == 1:
                    lbl.config(
                        text=str(count),
                        bg=PLAYER_COLOURS[pid], fg="white",
                        font=FONT_MONO_BOLD,
                    )
                elif pid in leaders:
                    lbl.config(
                        text=str(count),
                        bg=BG_SURFACE_ALT, fg=TABLE_CELL_FG,
                        font=FONT_MONO_BOLD,
                    )
                else:
                    lbl.config(
                        text=str(count),
                        bg=TABLE_CELL_BG, fg=TABLE_CELL_FG,
                        font=FONT_MONO,
                    )
