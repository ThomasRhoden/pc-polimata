"""Telemetria do Windows via WMI: temperaturas (LibreHardwareMonitor /
OpenHardwareMonitor), lista de GPUs (Win32_VideoController) e uso de GPU
de qualquer fabricante (contadores de desempenho "GPU Engine").

O psutil não expõe temperaturas no Windows. Quando o LibreHardwareMonitor
(ou o antigo OpenHardwareMonitor) está em execução, ele publica os sensores
no namespace WMI `root\\LibreHardwareMonitor` (ou `root\\OpenHardwareMonitor`).
Sem o programa, sem o pacote `wmi` ou fora do Windows, tudo retorna None.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from typing import Any

from pc_polimata.i18n import N_

NAMESPACES = ("root\\LibreHardwareMonitor", "root\\OpenHardwareMonitor")
HINT = N_("Abra o LibreHardwareMonitor (como administrador) para ver temperaturas no Windows.")


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


def parse_driver_date(raw: object) -> str | None:
    """Converte o CIM_DATETIME do WMI (ex.: '20240315000000.000000-000') em 'AAAA-MM-DD'."""
    match = re.match(r"^(\d{4})(\d{2})(\d{2})", str(raw or ""))
    return f"{match[1]}-{match[2]}-{match[3]}" if match else None


_ENGINE_RE = re.compile(r"luid_(0x[0-9a-fA-F]+_0x[0-9a-fA-F]+)_phys_(\d+).*engtype_(\w+)$")


def parse_gpu_engines(counters: list[Any]) -> dict[str, float]:
    """Soma a utilização dos motores 3D por adaptador (luid + phys), limitada a 100 %.

    Cada instância de Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine
    tem nome como `pid_1234_luid_0x0_0xD1B1_phys_0_eng_0_engtype_3D` e um
    `UtilizationPercentage` por processo; o Gerenciador de Tarefas usa a mesma soma.
    """
    totals: dict[str, float] = {}
    for c in counters:
        match = _ENGINE_RE.search(str(getattr(c, "Name", "")))
        if not match or match[3].lower() != "3d":
            continue
        try:
            value = float(getattr(c, "UtilizationPercentage", 0) or 0)
        except (TypeError, ValueError):
            continue
        key = f"{match[1].lower()}_phys_{match[2]}"
        totals[key] = totals.get(key, 0.0) + value
    return {k: min(v, 100.0) for k, v in sorted(totals.items())}


def read_gpu_utilization(wmi_module: Any = None, platform: str = sys.platform) -> dict[str, float]:
    """Uso 3D (%) por adaptador; vazio fora do Windows ou sem os contadores (Windows 10 1709+)."""
    if not platform.startswith("win"):
        return {}
    try:
        if wmi_module is None:
            import wmi as wmi_module  # type: ignore[no-redef]
        counters = wmi_module.WMI().Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine()
    except Exception:  # noqa: BLE001
        return {}
    return parse_gpu_engines(counters)


def list_video_controllers(wmi_module: Any = None, platform: str = sys.platform) -> list[dict[str, Any]]:
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
                "driver_date": parse_driver_date(getattr(c, "DriverDate", None)),
                "memory_total_mb": round(int(ram) / 2**20) if ram else None,
            }
        )
    return out
