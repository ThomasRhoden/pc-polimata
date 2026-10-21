"""Paleta escura com acentos verde-escuro e marrom terroso."""

import sys

BG = "#141a14"
PANEL = "#1d251c"
GREEN = "#3f6b3a"
GREEN_HOVER = "#4f8248"
GREEN_LIGHT = "#8fbf7a"
BROWN = "#7a5a3a"
BROWN_HOVER = "#93704b"
BROWN_LIGHT = "#c79a64"
SKY = "#7fa7b8"
GRID = "#2c3529"
TEXT = "#e4e0d4"
MUTED = "#a39e8c"
DANGER = "#8a3b2e"
FONT = ("Segoe UI", 13)
FONT_TITLE = ("Segoe UI", 18, "bold")
MONO = ("Consolas" if sys.platform == "win32" else "DejaVu Sans Mono", 12)


def apply_accent(accent: str) -> None:
    """'floresta' = verde primário/marrom secundário; 'terra' = invertido."""
    global GREEN, GREEN_HOVER, BROWN, BROWN_HOVER
    green, green_hover, brown, brown_hover = "#3f6b3a", "#4f8248", "#7a5a3a", "#93704b"
    if accent == "terra":
        green, green_hover, brown, brown_hover = brown, brown_hover, green, green_hover
    GREEN, GREEN_HOVER, BROWN, BROWN_HOVER = green, green_hover, brown, brown_hover
