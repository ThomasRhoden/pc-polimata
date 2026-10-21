import pytest

from pc_polimata.core import benchmark


def test_count_primes_known_values():
    assert benchmark.count_primes(10) == 4
    assert benchmark.count_primes(100) == 25


def test_compute_score():
    assert benchmark.compute_score(10, 2.0) == 500.0
    with pytest.raises(ValueError):
        benchmark.compute_score(1, 0)


def test_scaling():
    r = benchmark.CPUBenchmarkResult(100.0, 400.0, 4, 1.0)
    assert r.scaling == 4.0
    assert r.to_dict()["scaling"] == 4.0


def test_cpu_benchmark_runs_quickly():
    r = benchmark.run_cpu_benchmark(duration=0.3, processes=2)
    assert r.single_core_score > 0 and r.multi_core_score > 0


def test_disk_benchmark_cleans_up(tmp_path):
    r = benchmark.run_disk_benchmark(size_mb=4, directory=str(tmp_path))
    assert r.write_mb_s > 0 and r.read_mb_s > 0
    assert list(tmp_path.iterdir()) == []
