"""Plugin de exemplo: tempo ligado e horário do último boot."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import psutil


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    return f"{days}d {hours:02d}h {minutes:02d}m" if days else f"{hours:02d}h {minutes:02d}m"


class UptimePlugin:
    name = "uptime"
    version = "1.0.0"
    description = "Uptime and last boot time"

    def __init__(self, boot_time: float | None = None, now: float | None = None) -> None:
        self._boot = boot_time
        self._now = now

    def collect(self) -> dict[str, Any]:
        boot = self._boot if self._boot is not None else psutil.boot_time()
        now = self._now if self._now is not None else time.time()
        return {
            "boot_time_utc": datetime.fromtimestamp(boot, timezone.utc).isoformat(timespec="seconds"),
            "uptime_seconds": int(now - boot),
            "uptime": format_duration(now - boot),
        }


plugin = UptimePlugin()


def _create_tab(master: Any, app: Any) -> None:
    """Aba opcional: demonstra a fábrica de GUI de um plugin (atualiza a cada 30 s)."""
    import customtkinter as ctk

    label = ctk.CTkLabel(master, text="", justify="left", font=ctk.CTkFont(size=16))
    label.pack(anchor="w", padx=16, pady=16)

    def refresh() -> None:
        data = plugin.collect()
        label.configure(text=f"Uptime: {data['uptime']}\nBoot (UTC): {data['boot_time_utc']}")
        label.after(30_000, refresh)

    refresh()


UptimePlugin.create_tab = staticmethod(_create_tab)  # type: ignore[attr-defined]
