"""Detecção de GPU com degradação graciosa.

Backends, em ordem: NVML (NVIDIA) -> GPUtil (NVIDIA) -> sysfs amdgpu (Linux)
-> rocm-smi (AMD, Linux) -> WMI Win32_VideoController (qualquer GPU no
Windows, só nome/VRAM). Temperatura de GPU no Windows pode vir do
LibreHardwareMonitor (ver `windows_temps`). Nada aqui lança exceção.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

DRM_ROOT = Path("/sys/class/drm")
AMD_VENDOR_ID = "0x1002"


@dataclass
class GPUStatus:
    name: str
    load_percent: float | None = None
    memory_total_mb: float | None = None
    memory_used_mb: float | None = None
    temperature_c: float | None = None
    driver: str | None = None
    source: str = "unknown"

    def to_dict(self) -> dict:
        return asdict(self)


def _from_nvml() -> list[GPUStatus]:
    import pynvml  # provided by nvidia-ml-py

    pynvml.nvmlInit()
    try:
        driver = pynvml.nvmlSystemGetDriverVersion()
        driver = driver.decode() if isinstance(driver, bytes) else driver
        gpus = []
        for i in range(pynvml.nvmlDeviceGetCount()):
            h = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(h)
            name = name.decode() if isinstance(name, bytes) else name
            mem = pynvml.nvmlDeviceGetMemoryInfo(h)
            util = pynvml.nvmlDeviceGetUtilizationRates(h)
            temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
            gpus.append(
                GPUStatus(
                    name=name,
                    load_percent=float(util.gpu),
                    memory_total_mb=mem.total / 2**20,
                    memory_used_mb=mem.used / 2**20,
                    temperature_c=float(temp),
                    driver=driver,
                    source="nvml",
                )
            )
        return gpus
    finally:
        pynvml.nvmlShutdown()


def _from_gputil() -> list[GPUStatus]:
    import GPUtil

    return [
        GPUStatus(
            name=g.name,
            load_percent=g.load * 100,
            memory_total_mb=g.memoryTotal,
            memory_used_mb=g.memoryUsed,
            temperature_c=g.temperature,
            driver=g.driver,
            source="gputil",
        )
        for g in GPUtil.getGPUs()
    ]


def _read(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except OSError:
        return None


def _read_float(path: Path) -> float | None:
    raw = _read(path)
    try:
        return float(raw) if raw is not None else None
    except ValueError:
        return None


def from_amd_sysfs(root: Path = DRM_ROOT) -> list[GPUStatus]:
    """Lê GPUs AMD (driver amdgpu) em /sys/class/drm/card*/device."""
    gpus = []
    for card in sorted(root.glob("card[0-9]*")):
        if "-" in card.name:  # conectores como card0-HDMI-A-1
            continue
        dev = card / "device"
        if _read(dev / "vendor") != AMD_VENDOR_ID:
            continue
        temp = None
        for hwmon in sorted((dev / "hwmon").glob("hwmon*")):
            milli = _read_float(hwmon / "temp1_input")
            if milli is not None:
                temp = milli / 1000
                break
        total = _read_float(dev / "mem_info_vram_total")
        used = _read_float(dev / "mem_info_vram_used")
        name = _read(dev / "product_name") or f"AMD GPU ({_read(dev / 'device') or card.name})"
        gpus.append(
            GPUStatus(
                name=name,
                load_percent=_read_float(dev / "gpu_busy_percent"),
                memory_total_mb=total / 2**20 if total is not None else None,
                memory_used_mb=used / 2**20 if used is not None else None,
                temperature_c=temp,
                source="amd-sysfs",
            )
        )
    return gpus


def _num(card: dict, *names: str) -> float | None:
    for n in names:
        if n in card:
            try:
                return float(str(card[n]).rstrip("%"))
            except ValueError:
                return None
    return None


def parse_rocm_smi(output: str) -> list[GPUStatus]:
    data = json.loads(output)
    gpus = []
    for key, card in data.items():
        if not key.startswith("card"):
            continue

        total = _num(card, "VRAM Total Memory (B)")
        used = _num(card, "VRAM Total Used Memory (B)")
        gpus.append(
            GPUStatus(
                name=card.get("Card series") or card.get("Card SKU") or f"AMD {key}",
                load_percent=_num(card, "GPU use (%)"),
                memory_total_mb=total / 2**20 if total else None,
                memory_used_mb=used / 2**20 if used else None,
                temperature_c=_num(
                    card, "Temperature (Sensor edge) (C)", "Temperature (Sensor junction) (C)"
                ),
                source="rocm-smi",
            )
        )
    return gpus


def _from_rocm_smi() -> list[GPUStatus]:
    exe = shutil.which("rocm-smi")
    if not exe:
        return []
    out = subprocess.run(
        [exe, "--showuse", "--showtemp", "--showmeminfo", "vram", "--showproductname", "--json"],
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    ).stdout
    return parse_rocm_smi(out)


def _from_wmi() -> list[GPUStatus]:
    from pc_polimata.core.windows_temps import list_video_controllers, read_windows_temps

    controllers = list_video_controllers()
    temp = read_windows_temps().gpu_c if controllers else None
    return [
        GPUStatus(
            name=c["name"],
            memory_total_mb=c["memory_total_mb"],
            driver=c["driver"],
            temperature_c=temp if i == 0 else None,
            source="wmi",
        )
        for i, c in enumerate(controllers)
    ]


BACKENDS = (_from_nvml, _from_gputil, from_amd_sysfs, _from_rocm_smi, _from_wmi)


def get_gpus() -> list[GPUStatus]:
    """Retorna as GPUs detectadas pelo primeiro backend que funcionar."""
    for backend in BACKENDS:
        try:
            gpus = backend()
        except Exception:  # noqa: BLE001 - backend opcional pode falhar de várias formas
            continue
        if gpus:
            return gpus
    return []
