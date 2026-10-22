"""Análise heurística de gargalo CPU x GPU.

Ideia: durante uma carga real (ex.: um jogo aberto), amostramos uso de CPU
(média e núcleo mais carregado) e de GPU. Se a GPU está quase saturada, ela
limita o desempenho; se a GPU está ociosa enquanto a CPU (ou um único
núcleo) está saturada, a CPU é o gargalo.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import asdict, dataclass

from pc_polimata.core.sensors import SensorMonitor, SensorSnapshot
from pc_polimata.i18n import N_, tr

GPU_BOUND_THRESHOLD = 90.0
CPU_BOUND_THRESHOLD = 85.0
CORE_BOUND_THRESHOLD = 95.0


@dataclass
class BottleneckResult:
    verdict: str  # "CPU", "GPU", "Equilibrado" ou "Indeterminado"
    explanation: str
    avg_cpu: float
    avg_max_core: float
    avg_gpu: float | None
    samples: int

    def to_dict(self) -> dict:
        return asdict(self)


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 1) if values else 0.0


def analyze(samples: list[SensorSnapshot]) -> BottleneckResult:
    if not samples:
        return BottleneckResult(N_("Indeterminado"), tr("Nenhuma amostra coletada."), 0, 0, None, 0)
    avg_cpu = _mean([s.cpu_percent for s in samples])
    avg_core = _mean([max(s.per_core_percent or [s.cpu_percent]) for s in samples])
    gpu_vals = [s.gpu_percent for s in samples if s.gpu_percent is not None]
    avg_gpu = _mean(gpu_vals) if gpu_vals else None
    n = len(samples)

    if avg_gpu is None:
        if avg_cpu >= CPU_BOUND_THRESHOLD or avg_core >= CORE_BOUND_THRESHOLD:
            return BottleneckResult(
                "CPU",
                tr("Sem telemetria de GPU, mas a CPU está saturada."),
                avg_cpu,
                avg_core,
                None,
                n,
            )
        return BottleneckResult(
            N_("Indeterminado"),
            tr("GPU sem telemetria neste sistema."),
            avg_cpu,
            avg_core,
            None,
            n,
        )
    if avg_gpu >= GPU_BOUND_THRESHOLD:
        return BottleneckResult(
            "GPU",
            tr("GPU em {gpu}% de uso médio: ela limita o desempenho.", gpu=avg_gpu),
            avg_cpu,
            avg_core,
            avg_gpu,
            n,
        )
    if avg_cpu >= CPU_BOUND_THRESHOLD or avg_core >= CORE_BOUND_THRESHOLD:
        return BottleneckResult(
            "CPU",
            tr(
                "GPU em apenas {gpu}% enquanto a CPU (núcleo mais carregado {core}%) está saturada.",
                gpu=avg_gpu,
                core=avg_core,
            ),
            avg_cpu,
            avg_core,
            avg_gpu,
            n,
        )
    return BottleneckResult(
        N_("Equilibrado"),
        tr("Nenhum componente saturado durante a amostragem."),
        avg_cpu,
        avg_core,
        avg_gpu,
        n,
    )


def sample_and_analyze(
    duration_s: float = 30.0,
    interval_s: float = 1.0,
    monitor: SensorMonitor | None = None,
    on_progress: Callable[[float], None] | None = None,
    should_stop: Callable[[], bool] = lambda: False,
) -> BottleneckResult:
    monitor = monitor or SensorMonitor()
    samples: list[SensorSnapshot] = []
    start = time.monotonic()
    while (elapsed := time.monotonic() - start) < duration_s and not should_stop():
        time.sleep(interval_s)
        samples.append(monitor.read())
        if on_progress:
            on_progress(min(elapsed / duration_s, 1.0))
    return analyze(samples)
