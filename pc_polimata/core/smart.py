"""Saúde dos discos via `smartctl` (smartmontools), quando instalado.

Usa a saída JSON (`smartctl -j`, smartmontools >= 7). Sem o binário, sem
permissão (requer admin/root) ou em discos sem SMART, retorna status 'n/d'.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from pc_polimata.i18n import N_, tr

Runner = Callable[[list[str]], str]


@dataclass
class DiskHealth:
    device: str
    model: str | None = None
    passed: bool | None = None
    temperature_c: float | None = None
    power_on_hours: int | None = None
    percentage_used: int | None = None  # desgaste NVMe
    reallocated_sectors: int | None = None
    error: str | None = None

    @property
    def status(self) -> str:
        if self.passed is None:
            return "n/d"
        if not self.passed:
            return N_("FALHA")
        if (self.reallocated_sectors or 0) > 0 or (self.percentage_used or 0) >= 90:
            return N_("ATENÇÃO")
        return "OK"

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "status": self.status}


def _default_runner(args: list[str]) -> str:
    # smartctl usa bits do exit code para avisos; a saída JSON continua válida.
    proc = subprocess.run(args, capture_output=True, text=True, timeout=15, check=False)
    return proc.stdout


def find_smartctl() -> str | None:
    return shutil.which("smartctl")


def parse_smartctl(device: str, output: str) -> DiskHealth:
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return DiskHealth(device, error=tr("saída inválida do smartctl"))
    messages = data.get("smartctl", {}).get("messages", [])
    errors = [m.get("string", "") for m in messages if m.get("severity") == "error"]
    health = DiskHealth(device, model=data.get("model_name"))
    if "smart_status" in data:
        health.passed = bool(data["smart_status"].get("passed"))
    elif errors:
        health.error = errors[0]
    health.temperature_c = data.get("temperature", {}).get("current")
    health.power_on_hours = data.get("power_on_time", {}).get("hours")
    nvme = data.get("nvme_smart_health_information_log", {})
    health.percentage_used = nvme.get("percentage_used")
    for attr in data.get("ata_smart_attributes", {}).get("table", []):
        if attr.get("id") == 5:  # Reallocated_Sector_Ct
            health.reallocated_sectors = attr.get("raw", {}).get("value")
    return health


def scan_devices(runner: Runner, exe: str) -> list[str]:
    try:
        data = json.loads(runner([exe, "--scan", "-j"]))
    except (json.JSONDecodeError, OSError, subprocess.SubprocessError):
        return []
    return [d["name"] for d in data.get("devices", []) if "name" in d]


def check_disks(runner: Runner = _default_runner, exe: str | None = None) -> list[DiskHealth]:
    """Retorna a saúde de cada disco; lista vazia se smartctl não está disponível."""
    exe = exe or find_smartctl()
    if not exe:
        return []
    results = []
    for dev in scan_devices(runner, exe):
        try:
            results.append(parse_smartctl(dev, runner([exe, "-a", "-j", dev])))
        except (OSError, subprocess.SubprocessError) as exc:
            results.append(DiskHealth(dev, error=str(exc)))
    return results
