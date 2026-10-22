"""Plugin de exemplo: saúde da bateria (notebooks).

Carga e status vêm do psutil em qualquer SO. A saúde (capacidade atual vs.
de projeto) só está disponível no Linux, via /sys/class/power_supply.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import psutil

POWER_SUPPLY = Path("/sys/class/power_supply")


def _read_int(path: Path) -> int | None:
    try:
        return int(path.read_text().strip())
    except (OSError, ValueError):
        return None


def sysfs_health(root: Path = POWER_SUPPLY) -> dict[str, Any] | None:
    """Capacidade e ciclos da primeira bateria em `root` (energy_* ou charge_*)."""
    if not root.is_dir():
        return None
    for bat in sorted(root.glob("BAT*")):
        for prefix in ("energy", "charge"):
            full = _read_int(bat / f"{prefix}_full")
            design = _read_int(bat / f"{prefix}_full_design")
            if full and design:
                return {
                    "device": bat.name,
                    "health_percent": round(full / design * 100, 1),
                    "cycle_count": _read_int(bat / "cycle_count"),
                }
    return None


class BatteryPlugin:
    name = "battery"
    version = "1.0.0"
    description = "Battery charge and health"

    def __init__(self, root: Path = POWER_SUPPLY) -> None:
        self.root = root

    def collect(self) -> dict[str, Any]:
        battery = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
        if battery is None:
            return {"present": False}
        secs = battery.secsleft
        data: dict[str, Any] = {
            "present": True,
            "percent": round(battery.percent, 1),
            "plugged_in": battery.power_plugged,
            "minutes_left": None if secs in (psutil.POWER_TIME_UNKNOWN, psutil.POWER_TIME_UNLIMITED) else secs // 60,
        }
        health = sysfs_health(self.root)
        if health:
            data.update(health)
        return data


plugin = BatteryPlugin()
