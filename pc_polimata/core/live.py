"""Texto e geometria do overlay e do ícone da bandeja (puro, testável sem GUI)."""

from __future__ import annotations

from dataclasses import dataclass

from pc_polimata.core.sensors import SensorSnapshot
from pc_polimata.core.units import format_temp

CORNERS = ("top-left", "top-right", "bottom-left", "bottom-right")
SIZES = {"small": (220, 96, 11), "medium": (280, 120, 13), "large": (360, 156, 16)}  # largura, altura, fonte
MARGIN = 16


@dataclass(frozen=True)
class OverlayConfig:
    corner: str = "top-right"
    opacity: float = 0.8
    size: str = "medium"

    def validate(self) -> OverlayConfig:
        if self.corner not in CORNERS:
            raise ValueError(f"overlay corner must be one of {CORNERS}")
        if self.size not in SIZES:
            raise ValueError(f"overlay size must be one of {tuple(SIZES)}")
        if not 0.2 <= float(self.opacity) <= 1.0:
            raise ValueError("overlay opacity must be between 0.2 and 1.0")
        return self


def overlay_geometry(cfg: OverlayConfig, screen_w: int, screen_h: int) -> str:
    """String de geometria Tk (`LxA+x+y`) para o canto escolhido."""
    w, h, _ = SIZES[cfg.size]
    x = MARGIN if "left" in cfg.corner else max(0, screen_w - w - MARGIN)
    y = MARGIN if cfg.corner.startswith("top") else max(0, screen_h - h - MARGIN)
    return f"{w}x{h}+{x}+{y}"


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.0f}%"


def overlay_lines(snap: SensorSnapshot, unit: str = "C", fps: str | None = None) -> list[str]:
    lines = [
        f"CPU {_pct(snap.cpu_percent):>5}  {format_temp(snap.cpu_temp_c, unit)}",
        f"GPU {_pct(snap.gpu_percent):>5}  {format_temp(snap.gpu_temp_c, unit)}",
        f"RAM {_pct(snap.ram_percent):>5}",
    ]
    if fps:
        lines.append(fps)
    return lines


def tray_tooltip(snap: SensorSnapshot | None, unit: str = "C", monitoring: bool = True) -> str:
    """Tooltip curto (o Windows corta em ~127 caracteres)."""
    if snap is None:
        return "PC Polimata"
    state = "" if monitoring else " (II)"
    text = f"PC Polimata{state} — CPU {_pct(snap.cpu_percent)} {format_temp(snap.cpu_temp_c, unit)}"
    if snap.gpu_percent is not None or snap.gpu_temp_c is not None:
        text += f" | GPU {_pct(snap.gpu_percent)} {format_temp(snap.gpu_temp_c, unit)}"
    return text[:127]
