import random

import pytest

from pc_polimata.core import memory_bench as mb


def test_permutation_is_single_cycle():
    nxt = mb.single_cycle_permutation(1000, random.Random(1))
    seen, i = set(), 0
    for _ in range(1000):
        seen.add(i)
        i = nxt[i]
    assert len(seen) == 1000 and i == 0


def test_runs_small():
    r = mb.run_memory_benchmark(size_mb=4, latency_elements=10_000, steps=10_000)
    assert r.bandwidth_gb_s > 0 and r.latency_ns > 0 and r.backend in {"numpy", "python"}


def test_python_fallback(monkeypatch):
    def no_numpy(*a, **k):
        raise ImportError

    monkeypatch.setattr(mb, "_bandwidth_numpy", no_numpy)
    r = mb.run_memory_benchmark(size_mb=2, latency_elements=1000, steps=1000)
    assert r.backend == "python"


def test_validation():
    with pytest.raises(ValueError):
        mb.run_memory_benchmark(size_mb=0)
