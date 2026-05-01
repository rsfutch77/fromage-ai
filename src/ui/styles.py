"""Shared visual constants for the modern Fromage UI.

Centralises palette, fonts, and sizing so board_display, _score_widgets,
and the top-level ui module all stay in sync.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Window / layout
# ---------------------------------------------------------------------------

BG_PRIMARY = "#1E1E2E"       # deep charcoal — main window background
BG_SURFACE = "#2A2A3C"       # card / panel surface
BG_SURFACE_ALT = "#33334A"   # alternate surface (hover, debug panel)
BG_INPUT = "#3A3A52"         # input / button background
BORDER_SUBTLE = "#44446A"    # subtle borders between panels

# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------

FG_PRIMARY = "#E0E0F0"       # main text on dark background
FG_SECONDARY = "#A0A0C0"     # secondary / muted text
FG_MUTED = "#6C6C8A"         # disabled text / placeholders

FONT_FAMILY = "Segoe UI"     # modern sans-serif (falls back gracefully)
FONT_TITLE = (FONT_FAMILY, 14, "bold")
FONT_HEADING = (FONT_FAMILY, 11, "bold")
FONT_BODY = (FONT_FAMILY, 10)
FONT_BODY_BOLD = (FONT_FAMILY, 10, "bold")
FONT_SMALL = (FONT_FAMILY, 9)
FONT_SMALL_BOLD = (FONT_FAMILY, 9, "bold")
FONT_MONO = ("Cascadia Mono", 9)
FONT_MONO_BOLD = ("Cascadia Mono", 9, "bold")
FONT_TINY = (FONT_FAMILY, 8)
FONT_TINY_BOLD = (FONT_FAMILY, 8, "bold")

# ---------------------------------------------------------------------------
# Board cells
# ---------------------------------------------------------------------------

CELL_SIZE = 36               # px per cheese-space cell (up from 28)
CELL_PAD = 5                 # px padding between cells
CELL_RADIUS = 6              # corner radius for rounded rects
CANVAS_BG = "#23233A"        # canvas background

# Cheese type fill
CHEESE_FILL: dict[str, str] = {
    "SOFT": "#FFF3B0",       # warm cream
    "HARD": "#FFCC66",       # golden amber
    "BLEU": "#7EB8E0",       # soft sky blue
    "FREE": "#8DD5A0",       # minty green
}
EMPTY_FILL = "#2E2E44"
EMPTY_OUTLINE = "#44446A"
RESOURCE_FILL = "#3A3A60"    # lavender-dark tint for resource spaces

# Age tier outlines
AGE_OUTLINE: dict[str, str] = {
    "BRONZE": "#CD7F32",
    "SILVER": "#B0BEC5",
    "GOLD": "#FFD700",
}

# ---------------------------------------------------------------------------
# Player accents
# ---------------------------------------------------------------------------

PLAYER_COLOURS = ["#FF6B6B", "#4DABF7", "#69DB7C", "#FFA94D"]

# Lighter tints for backgrounds / badges
PLAYER_TINTS = ["#FF6B6B22", "#4DABF722", "#69DB7C22", "#FFA94D22"]

# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------

BTN_BG = "#3A3A52"
BTN_FG = "#E0E0F0"
BTN_ACTIVE_BG = "#50507A"
BTN_ACCENT_BG = "#6C63FF"    # primary action button
BTN_ACCENT_FG = "#FFFFFF"

# ---------------------------------------------------------------------------
# Score table
# ---------------------------------------------------------------------------

TABLE_HEADER_BG = "#33334A"
TABLE_CELL_BG = "#2A2A3C"
TABLE_CELL_FG = "#D0D0E8"
TABLE_SEPARATOR = "#555580"

# ---------------------------------------------------------------------------
# Status bar
# ---------------------------------------------------------------------------

STATUS_BG = "#252540"
STATUS_FG = "#B0B0D0"
