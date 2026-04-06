"""Score breakdown table and Villes region table widgets for BoardDisplay."""

from __future__ import annotations

import tkinter as tk

# Player 0-3 → accent colour (kept in sync with board_display._PLAYER_COLOURS)
_PLAYER_COLOURS = ["#EF5350", "#42A5F5", "#66BB6A", "#FFA726"]

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
        tk.Label(parent, text="Score Breakdown", font=("Helvetica", 10, "bold"),
                 bg="#ECEFF1").pack(anchor="w", pady=(0, 4))

        tbl = tk.Frame(parent, bg="#ECEFF1")
        tbl.pack(fill="x")

        # Header row
        tk.Label(tbl, text="", width=9, bg="#ECEFF1",
                 font=("Courier", 7)).grid(row=0, column=0)
        for pid in range(4):
            tk.Label(
                tbl, text=f"P{pid}", width=4,
                bg=_PLAYER_COLOURS[pid], fg="white",
                font=("Courier", 7, "bold"),
            ).grid(row=0, column=pid + 1, padx=1)

        self._score_cells: dict[str, dict[int, tk.Label]] = {}
        for row_idx, (field, label) in enumerate(_SCORE_ROW_DEFS):
            tk.Label(
                tbl, text=label, width=9, bg="#ECEFF1",
                font=("Courier", 7), anchor="w",
            ).grid(row=row_idx + 1, column=0)
            self._score_cells[field] = {}
            for pid in range(4):
                lbl = tk.Label(
                    tbl, text="—", width=4,
                    bg="white", fg="#424242",
                    font=("Courier", 7),
                )
                lbl.grid(row=row_idx + 1, column=pid + 1, padx=1, pady=1)
                self._score_cells[field][pid] = lbl

        sep_row = len(_SCORE_ROW_DEFS) + 1
        tk.Frame(tbl, bg="#90A4AE", height=1).grid(
            row=sep_row, column=0, columnspan=5, sticky="ew", pady=2,
        )

        tk.Label(
            tbl, text="TOTAL", width=9, bg="#ECEFF1",
            font=("Courier", 7, "bold"), anchor="w",
        ).grid(row=sep_row + 1, column=0)
        self._total_cells: dict[int, tk.Label] = {}
        for pid in range(4):
            lbl = tk.Label(
                tbl, text="—", width=4,
                bg="white", fg="#424242",
                font=("Courier", 7, "bold"),
            )
            lbl.grid(row=sep_row + 1, column=pid + 1, padx=1, pady=1)
            self._total_cells[pid] = lbl

    def update(self, breakdowns: list) -> None:
        """Populate the score breakdown table with end-game results."""
        bd_map: dict[int, object] = {b.player_id: b for b in breakdowns}

        for field, cells in self._score_cells.items():
            for pid, lbl in cells.items():
                bd = bd_map.get(pid)
                val = getattr(bd, field, 0) if bd else 0
                lbl.config(text=str(val), bg="white", fg="#424242",
                           font=("Courier", 7))

        max_total = max((b.total for b in breakdowns), default=0)
        for pid, lbl in self._total_cells.items():
            bd = bd_map.get(pid)
            val = bd.total if bd else 0
            if val == max_total:
                lbl.config(
                    text=str(val),
                    bg=_PLAYER_COLOURS[pid], fg="white",
                    font=("Courier", 7, "bold"),
                )
            else:
                lbl.config(
                    text=str(val),
                    bg="white", fg="#424242",
                    font=("Courier", 7, "bold"),
                )

    def clear(self) -> None:
        """Reset all cells to dashes (pre-game-over state)."""
        for cells in self._score_cells.values():
            for lbl in cells.values():
                lbl.config(text="—", bg="white", fg="#424242",
                           font=("Courier", 7))
        for lbl in self._total_cells.values():
            lbl.config(text="—", bg="white", fg="#424242",
                       font=("Courier", 7, "bold"))


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

        tbl = tk.Frame(parent, bg="#ECEFF1")
        tbl.pack(side="left", anchor="n", padx=(6, 0))

        # Header row
        tk.Label(tbl, text="", width=7, bg="#ECEFF1",
                 font=("Courier", 7)).grid(row=0, column=0)
        for pid in range(4):
            tk.Label(
                tbl, text=f"P{pid}", width=3,
                bg=_PLAYER_COLOURS[pid], fg="white",
                font=("Courier", 7, "bold"),
            ).grid(row=0, column=pid + 1, padx=1)

        self._cells: dict[str, dict[int, tk.Label]] = {}
        self._region_labels: dict[str, tk.Label] = {}
        for row_idx, region in enumerate(region_names):
            lbl = tk.Label(
                tbl, text=region, width=11, bg="#ECEFF1",
                font=("Courier", 7), anchor="w",
            )
            lbl.grid(row=row_idx + 1, column=0)
            self._region_labels[region] = lbl
            self._cells[region] = {}
            for pid in range(4):
                cell = tk.Label(
                    tbl, text="0", width=3,
                    bg="white", fg="#424242",
                    font=("Courier", 7),
                )
                cell.grid(row=row_idx + 1, column=pid + 1, padx=1, pady=1)
                self._cells[region][pid] = cell

    def update(self, occupied: dict[int, int], villes_spaces: dict) -> None:
        """Refresh influence counts and leader highlighting from *occupied*.

        Args:
            occupied:     space_id → player_id for all placed Villes tokens.
            villes_spaces: space_id → VillesSpace (for region membership lookup).
        """
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
                rlbl.config(text=region, fg="#424242", bg="#ECEFF1",
                            font=("Courier", 7))
            elif len(leaders) == 1:
                sole = next(iter(leaders))
                rlbl.config(
                    text=f"{region} ({win_val})",
                    fg=_PLAYER_COLOURS[sole], bg="#ECEFF1",
                    font=("Courier", 7, "bold"),
                )
            else:
                rlbl.config(
                    text=f"{region} ({tie_val})",
                    fg="#757575", bg="#ECEFF1",
                    font=("Courier", 7),
                )

            for pid, lbl in cells.items():
                count = inf[pid]
                if pid in leaders and len(leaders) == 1:
                    lbl.config(
                        text=str(count),
                        bg=_PLAYER_COLOURS[pid], fg="white",
                        font=("Courier", 7, "bold"),
                    )
                elif pid in leaders:
                    lbl.config(
                        text=str(count),
                        bg="#E0E0E0", fg="#424242",
                        font=("Courier", 7, "bold"),
                    )
                else:
                    lbl.config(
                        text=str(count),
                        bg="white", fg="#424242",
                        font=("Courier", 7),
                    )
