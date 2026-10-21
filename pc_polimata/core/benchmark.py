"""Benchmarks de CPU (single/multi-core) e de disco.

O score de CPU é próprio do PC Polimata: número de iterações de uma carga
fixa (primos + ponto flutuante) por segundo, escalado. Não é comparável
com Cinebench ou outras ferramentas.
"""

from __future__ import annotations

import math
import multiprocessing as mp
import os
import tempfile
import time
from dataclasses import asdict, dataclass

WORKLOAD_SIZE = 20_000
SCORE_SCALE = 100


@dataclass
class CPUBenchmarkResult:
    single_core_score: float
    multi_core_score: float
    processes: int
    duration_s: float

    @property
    def scaling(self) -> float:
        if self.single_core_score <= 0:
            return 0.0
        return round(self.multi_core_score / self.single_core_score, 2)

    def to_dict(self) -> dict:
        return {**asdict(self), "scaling": self.scaling}


@dataclass
class DiskBenchmarkResult:
    write_mb_s: float
    read_mb_s: float
    size_mb: int

    def to_dict(self) -> dict:
        return asdict(self)


def count_primes(limit: int) -> int:
    """Conta primos < limit via divisão por tentativa (carga inteira)."""
    count = 0
    for n in range(2, limit):
        is_prime = True
        for d in range(2, math.isqrt(n) + 1):
            if n % d == 0:
                is_prime = False
                break
        if is_prime:
            count += 1
    return count


def workload_unit(size: int = WORKLOAD_SIZE) -> float:
    """Uma unidade de trabalho determinística: inteiros + ponto flutuante."""
    acc = float(count_primes(size // 4))
    for i in range(1, size):
        acc += math.sin(i) * math.sqrt(i)
    return acc


def _iterations_in(duration: float) -> int:
    end = time.perf_counter() + duration
    iterations = 0
    while time.perf_counter() < end:
        workload_unit()
        iterations += 1
    return iterations


def compute_score(iterations: int, duration: float) -> float:
    if duration <= 0:
        raise ValueError("duration must be positive")
    return round(iterations / duration * SCORE_SCALE, 1)


def run_cpu_benchmark(duration: float = 5.0, processes: int | None = None) -> CPUBenchmarkResult:
    processes = processes or os.cpu_count() or 1
    start = time.perf_counter()
    single = compute_score(_iterations_in(duration), duration)
    with mp.Pool(processes) as pool:
        results = pool.map(_iterations_in, [duration] * processes)
    multi = compute_score(sum(results), duration)
    return CPUBenchmarkResult(single, multi, processes, round(time.perf_counter() - start, 2))


def run_disk_benchmark(size_mb: int = 128, directory: str | None = None) -> DiskBenchmarkResult:
    """Escreve e lê um arquivo temporário. A leitura pode ser afetada pelo cache do SO."""
    chunk = os.urandom(2**20)
    fd, path = tempfile.mkstemp(prefix="pcpolimata_", dir=directory)
    try:
        start = time.perf_counter()
        with os.fdopen(fd, "wb", buffering=0) as f:
            for _ in range(size_mb):
                f.write(chunk)
            os.fsync(f.fileno())
        write_time = time.perf_counter() - start

        start = time.perf_counter()
        with open(path, "rb", buffering=0) as f:
            while f.read(2**20):
                pass
        read_time = time.perf_counter() - start
    finally:
        os.remove(path)
    return DiskBenchmarkResult(
        write_mb_s=round(size_mb / max(write_time, 1e-9), 1),
        read_mb_s=round(size_mb / max(read_time, 1e-9), 1),
        size_mb=size_mb,
    )
