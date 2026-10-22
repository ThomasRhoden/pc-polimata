"""Coleta de informações estáticas do sistema (SO, CPU, RAM, discos, GPU)."""

from __future__ import annotations

import platform
from typing import Any

import psutil

from pc_polimata.core.gpu import get_gpus


def _bytes_to_gb(value: float) -> float:
    return round(value / 2**30, 2)


def get_os_info() -> dict[str, Any]:
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "hostname": platform.node(),
        "python": platform.python_version(),
    }


def get_cpu_info() -> dict[str, Any]:
    name = platform.processor() or "Desconhecido"
    flags_count = None
    try:
        import cpuinfo

        info = cpuinfo.get_cpu_info()
        name = info.get("brand_raw") or name
        flags_count = len(info.get("flags", []))
    except Exception:  # noqa: BLE001 - py-cpuinfo é opcional
        pass
    freq = psutil.cpu_freq()
    return {
        "name": name,
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "max_freq_mhz": round(freq.max, 1) if freq and freq.max else None,
        "current_freq_mhz": round(freq.current, 1) if freq else None,
        "instruction_flags": flags_count,
    }


def get_memory_info() -> dict[str, Any]:
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    return {
        "total_gb": _bytes_to_gb(vm.total),
        "available_gb": _bytes_to_gb(vm.available),
        "used_percent": vm.percent,
        "swap_total_gb": _bytes_to_gb(sw.total),
    }


def get_disks_info() -> list[dict[str, Any]]:
    disks = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except (PermissionError, OSError):
            continue
        disks.append(
            {
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total_gb": _bytes_to_gb(usage.total),
                "used_percent": usage.percent,
            }
        )
    return disks


def get_system_info() -> dict[str, Any]:
    """Snapshot completo do hardware, serializável em JSON."""
    return {
        "os": get_os_info(),
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "disks": get_disks_info(),
        "gpus": [g.to_dict() for g in get_gpus()],
    }


_CACHE: dict[str, Any] = {}


def get_system_info_cached(refresh: bool = False) -> dict[str, Any]:
    """`get_system_info()` memorizado: hardware estático não muda durante a sessão."""
    if refresh or "info" not in _CACHE:
        _CACHE["info"] = get_system_info()
    return _CACHE["info"]  # type: ignore[no-any-return]
