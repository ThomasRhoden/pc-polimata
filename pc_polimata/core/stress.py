"""Stress test de CPU com limites de segurança e parada cooperativa."""

from __future__ import annotations

import multiprocessing as mp
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from pc_polimata.core.sensors import read_cpu_temperature


def _burn(stop_event) -> None:  # pragma: no cover - executa em subprocesso
    x = 0.0001
    while not stop_event.is_set():
        for _ in range(50_000):
            x = (x * x + 1.0001) % 1000.0


@dataclass
class StressConfig:
    duration_s: float = 60.0
    max_temp_c: float | None = 90.0
    workers: int = field(default_factory=lambda: os.cpu_count() or 1)
    poll_interval_s: float = 1.0

    def __post_init__(self) -> None:
        if self.duration_s <= 0:
            raise ValueError("duration_s must be positive")
        if self.workers < 1:
            raise ValueError("workers must be >= 1")


@dataclass
class StressResult:
    elapsed_s: float
    stop_reason: str
    max_temp_c: float | None
    samples: list[dict]

    def to_dict(self) -> dict:
        return {
            "elapsed_s": self.elapsed_s,
            "stop_reason": self.stop_reason,
            "max_temp_c": self.max_temp_c,
            "samples": len(self.samples),
        }


def check_limits(temp_c: float | None, config: StressConfig) -> str | None:
    """Retorna o motivo de parada se algum limite foi violado."""
    if config.max_temp_c is not None and temp_c is not None and temp_c >= config.max_temp_c:
        return f"temperatura {temp_c:.0f}°C >= limite {config.max_temp_c:.0f}°C"
    return None


class StressTest:
    """Executa workers em processos separados; `stop()` é seguro a qualquer momento."""

    def __init__(
        self,
        config: StressConfig,
        temp_reader: Callable[[], float | None] = read_cpu_temperature,
    ) -> None:
        self.config = config
        self.temp_reader = temp_reader
        self._ctx = mp.get_context("spawn")
        self._stop = self._ctx.Event()
        self._user_stop = False

    def stop(self) -> None:
        self._user_stop = True
        self._stop.set()

    def run(self, on_sample: Callable[[dict], None] | None = None) -> StressResult:
        import psutil

        workers = [self._ctx.Process(target=_burn, args=(self._stop,), daemon=True) for _ in range(self.config.workers)]
        for w in workers:
            w.start()
        start = time.monotonic()
        reason, max_temp, samples = "duração concluída", None, []
        try:
            while True:
                elapsed = time.monotonic() - start
                temp = self.temp_reader()
                if temp is not None:
                    max_temp = temp if max_temp is None else max(max_temp, temp)
                sample = {
                    "elapsed_s": round(elapsed, 1),
                    "cpu_percent": psutil.cpu_percent(),
                    "temp_c": temp,
                }
                samples.append(sample)
                if on_sample:
                    on_sample(sample)
                if self._user_stop:
                    reason = "parado pelo usuário"
                    break
                if (limit := check_limits(temp, self.config)) is not None:
                    reason = limit
                    break
                if elapsed >= self.config.duration_s:
                    break
                self._stop.wait(self.config.poll_interval_s)
        finally:
            self._stop.set()
            for w in workers:
                w.join(timeout=3)
                if w.is_alive():
                    w.terminate()
        return StressResult(round(time.monotonic() - start, 1), reason, max_temp, samples)
