"""Detecção de GPU com degradação graciosa.

Ordem de tentativa: NVML (nvidia-ml-py) -> GPUtil. Sem nenhum dos dois,
retorna lista vazia em vez de lançar exceção.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


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


def get_gpus() -> list[GPUStatus]:
    """Retorna as GPUs detectadas (apenas NVIDIA possui telemetria completa)."""
    for backend in (_from_nvml, _from_gputil):
        try:
            gpus = backend()
        except Exception:  # noqa: BLE001 - backend opcional pode falhar de várias formas
            continue
        if gpus:
            return gpus
    return []
