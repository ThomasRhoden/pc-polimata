"""Benchmark aproximado de memória RAM.

- Largura de banda: cópia de um buffer maior que o cache L3 (numpy se
  disponível; senão `bytearray` + slicing, que também copia em C).
- Latência: "pointer chasing" em uma permutação aleatória com um único
  ciclo, o que derrota o prefetcher. Em Python puro o overhead do
  interpretador domina, então o valor é um teto, não a latência real.
"""

from __future__ import annotations

import random
import time
from dataclasses import asdict, dataclass


@dataclass
class MemoryBenchmarkResult:
    bandwidth_gb_s: float
    latency_ns: float
    size_mb: int
    backend: str

    def to_dict(self) -> dict:
        return asdict(self)


def single_cycle_permutation(n: int, rng: random.Random) -> list[int]:
    """Permutação em que seguir next[i] visita todos os n índices (algoritmo de Sattolo)."""
    order = list(range(n))
    for i in range(n - 1, 0, -1):
        j = rng.randrange(i)
        order[i], order[j] = order[j], order[i]
    nxt = [0] * n
    for a, b in zip(order, order[1:] + order[:1], strict=True):
        nxt[a] = b
    return nxt


def _bandwidth_numpy(size: int, repeats: int) -> float:
    import numpy as np

    src = np.ones(size, dtype=np.uint8)
    dst = np.empty_like(src)
    best = float("inf")
    for _ in range(repeats):
        start = time.perf_counter()
        np.copyto(dst, src)
        best = min(best, time.perf_counter() - start)
    return 2 * size / best / 1e9  # leitura + escrita


def _bandwidth_python(size: int, repeats: int) -> float:
    src = bytearray(size)
    best = float("inf")
    for _ in range(repeats):
        start = time.perf_counter()
        dst = src[:]  # cópia em C
        best = min(best, time.perf_counter() - start)
        del dst
    return 2 * size / best / 1e9


def _latency_numpy(n: int, steps: int, rng: random.Random) -> float:
    import numpy as np

    nxt = np.array(single_cycle_permutation(n, rng), dtype=np.int64)
    # numpy não acelera um laço dependente; usamos list para acesso escalar rápido
    chain = nxt.tolist()
    return _chase(chain, steps)


def _chase(chain: list[int], steps: int) -> float:
    i = 0
    start = time.perf_counter()
    for _ in range(steps):
        i = chain[i]
    return (time.perf_counter() - start) / steps * 1e9


def run_memory_benchmark(
    size_mb: int = 128, latency_elements: int = 2_000_000, steps: int = 1_000_000, seed: int = 42
) -> MemoryBenchmarkResult:
    if size_mb < 1 or latency_elements < 2 or steps < 1:
        raise ValueError("invalid benchmark parameters")
    rng = random.Random(seed)
    size = size_mb * 2**20
    try:
        bandwidth = _bandwidth_numpy(size, repeats=5)
        latency = _latency_numpy(latency_elements, steps, rng)
        backend = "numpy"
    except ImportError:
        bandwidth = _bandwidth_python(size, repeats=5)
        latency = _chase(single_cycle_permutation(latency_elements, rng), steps)
        backend = "python"
    return MemoryBenchmarkResult(round(bandwidth, 2), round(latency, 1), size_mb, backend)
