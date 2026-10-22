"""Informações de driver de GPU e alerta de driver desatualizado.

Fontes: GPUStatus (NVML/WMI já trazem versão; WMI traz a data) e, como
complemento, `nvidia-smi` para a versão quando NVML não está disponível.
A data do driver só é conhecida no Windows (WMI `DriverDate`).
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date

from pc_polimata.core.gpu import GPUStatus

OUTDATED_AFTER_DAYS = 183  # ~6 meses

Runner = Callable[[list[str]], str]

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # exe sem console: não abrir janela de CMD


@dataclass
class DriverInfo:
    gpu: str
    version: str | None
    release_date: str | None
    age_days: int | None
    outdated: bool | None  # None = data desconhecida

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _run(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True, timeout=5, check=True, creationflags=NO_WINDOW).stdout


def nvidia_smi_versions(runner: Runner = _run, exe: str | None = None) -> dict[str, str]:
    """Mapeia nome da GPU -> versão do driver via `nvidia-smi` (vazio se ausente)."""
    exe = exe or shutil.which("nvidia-smi")
    if not exe:
        return {}
    try:
        out = runner([exe, "--query-gpu=name,driver_version", "--format=csv,noheader"])
    except (OSError, subprocess.SubprocessError):
        return {}
    result = {}
    for line in out.strip().splitlines():
        name, _, version = line.rpartition(",")
        if name.strip() and version.strip():
            result[name.strip()] = version.strip()
    return result


def assess(gpu: GPUStatus, today: date, fallback_version: str | None = None) -> DriverInfo:
    release = gpu.driver_date
    age = outdated = None
    if release:
        try:
            age = (today - date.fromisoformat(release)).days
            outdated = age > OUTDATED_AFTER_DAYS
        except ValueError:
            release = None
    return DriverInfo(gpu.name, gpu.driver or fallback_version, release, age, outdated)


def driver_report(gpus: list[GPUStatus], today: date | None = None, runner: Runner = _run) -> list[DriverInfo]:
    today = today or date.today()
    smi = nvidia_smi_versions(runner) if any(g.driver is None for g in gpus) else {}
    return [assess(g, today, smi.get(g.name)) for g in gpus]
