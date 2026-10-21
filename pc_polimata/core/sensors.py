"""Leituras de sensores em tempo real (uso e temperatura)."""

from __future__ import annotations

import sys
import time
from dataclasses import asdict, dataclass, field

import psutil

from pc_polimata.core.gpu import get_gpus

_CPU_SENSOR_KEYS = ("coretemp", "k10temp", "zenpower", "cpu_thermal", "acpitz")


@dataclass
class SensorSnapshot:
    timestamp: float
    cpu_percent: float
    per_core_percent: list[float]
    ram_percent: float
    disk_read_mb_s: float
    disk_write_mb_s: float
    cpu_temp_c: float | None = None
    gpu_percent: float | None = None
    gpu_temp_c: float | None = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def read_cpu_temperature() -> float | None:
    """Temperatura da CPU em °C, ou None se o SO não expõe (Windows: requer LibreHardwareMonitor)."""
    if sys.platform.startswith("win"):
        from pc_polimata.core.windows_temps import read_windows_temps

        return read_windows_temps().cpu_c
    reader = getattr(psutil, "sensors_temperatures", None)
    if reader is None:
        return None
    try:
        temps = reader()
    except Exception:  # noqa: BLE001
        return None
    for key in _CPU_SENSOR_KEYS:
        entries = temps.get(key)
        if entries:
            return max(e.current for e in entries)
    return None


class SensorMonitor:
    """Gera snapshots consecutivos calculando taxas de disco entre chamadas."""

    def __init__(self, include_gpu: bool = True) -> None:
        self.include_gpu = include_gpu
        self._last_io = psutil.disk_io_counters()
        self._last_time = time.monotonic()
        psutil.cpu_percent(percpu=True)  # primeira chamada inicializa o contador

    def read(self) -> SensorSnapshot:
        now = time.monotonic()
        elapsed = max(now - self._last_time, 1e-6)
        io = psutil.disk_io_counters()
        read_rate = write_rate = 0.0
        if io and self._last_io:
            read_rate = (io.read_bytes - self._last_io.read_bytes) / elapsed / 2**20
            write_rate = (io.write_bytes - self._last_io.write_bytes) / elapsed / 2**20
        self._last_io, self._last_time = io, now

        per_core = psutil.cpu_percent(percpu=True)
        gpu_pct = gpu_temp = None
        if self.include_gpu:
            gpus = get_gpus()
            if gpus:
                gpu_pct, gpu_temp = gpus[0].load_percent, gpus[0].temperature_c
        return SensorSnapshot(
            timestamp=time.time(),
            cpu_percent=round(sum(per_core) / max(len(per_core), 1), 1),
            per_core_percent=per_core,
            ram_percent=psutil.virtual_memory().percent,
            disk_read_mb_s=round(max(read_rate, 0.0), 2),
            disk_write_mb_s=round(max(write_rate, 0.0), 2),
            cpu_temp_c=read_cpu_temperature(),
            gpu_percent=gpu_pct,
            gpu_temp_c=gpu_temp,
        )
