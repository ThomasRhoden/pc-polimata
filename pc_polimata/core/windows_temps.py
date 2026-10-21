"""Temperaturas no Windows via LibreHardwareMonitor / OpenHardwareMonitor (WMI).

O psutil não expõe temperaturas no Windows. Quando o LibreHardwareMonitor
(ou o antigo OpenHardwareMonitor) está em execução, ele publica os sensores
no namespace WMI `root\\LibreHardwareMonitor` (ou `root\\OpenHardwareMonitor`).
Sem o programa, sem o pacote `wmi` ou fora do Windows, tudo retorna None.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

NAMESPACES = ("root\\LibreHardwareMonitor", "root\\OpenHardwareMonitor")
HINT = "Abra o LibreHardwareMonitor (como administrador) para ver temperaturas no Windows."


@dataclass
class WindowsTemps:
    cpu_c: float | None = None
    gpu_c: float | None = None
    source: str | None = None


def _query_sensors(wmi_module: Any) -> tuple[list[Any], str] | None:
    for ns in NAMESPACES:
        try:
            sensors = wmi_module.WMI(namespace=ns).Sensor()
        except Exception:  # noqa: BLE001 - namespace ausente => programa fechado
            continue
        if sensors:
            return sensors, ns
    return None


def parse_sensors(sensors: list[Any]) -> tuple[float | None, float | None]:
    """Extrai (cpu, gpu) em °C de objetos com SensorType, Name, Parent e Value."""
    cpu_pkg: list[float] = []
    cpu_any: list[float] = []
    gpu: list[float] = []
    for s in sensors:
        if getattr(s, "SensorType", "") != "Temperature" or getattr(s, "Value", None) is None:
            continue
        parent = str(getattr(s, "Parent", "")).lower()
        name = str(getattr(s, "Name", "")).lower()
        value = float(s.Value)
        if "gpu" in parent:
            gpu.append(value)
        elif "cpu" in parent:
            (cpu_pkg if ("package" in name or "tctl" in name) else cpu_any).append(value)
    cpu = max(cpu_pkg) if cpu_pkg else (max(cpu_any) if cpu_any else None)
    return cpu, (max(gpu) if gpu else None)


def read_windows_temps(wmi_module: Any = None, platform: str = sys.platform) -> WindowsTemps:
    if not platform.startswith("win"):
        return WindowsTemps()
    if wmi_module is None:
        try:
            import wmi as wmi_module  # type: ignore[no-redef]
        except ImportError:
            return WindowsTemps()
    found = _query_sensors(wmi_module)
    if found is None:
        return WindowsTemps()
    sensors, ns = found
    cpu, gpu = parse_sensors(sensors)
    return WindowsTemps(cpu, gpu, ns)


def list_video_controllers(wmi_module: Any = None, platform: str = sys.platform) -> list[dict]:
    """Nomes de GPUs (qualquer fabricante) via Win32_VideoController."""
    if not platform.startswith("win"):
        return []
    try:
        if wmi_module is None:
            import wmi as wmi_module  # type: ignore[no-redef]
        controllers = wmi_module.WMI().Win32_VideoController()
    except Exception:  # noqa: BLE001
        return []
    out = []
    for c in controllers:
        ram = getattr(c, "AdapterRAM", None)
        out.append(
            {
                "name": getattr(c, "Name", "GPU"),
                "driver": getattr(c, "DriverVersion", None),
                "memory_total_mb": round(int(ram) / 2**20) if ram else None,
            }
        )
    return out
