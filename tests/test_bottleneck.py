from pc_polimata.core.bottleneck import analyze
from pc_polimata.core.sensors import SensorSnapshot


def snap(cpu, cores, gpu):
    return SensorSnapshot(0, cpu, cores, 50, 0, 0, gpu_percent=gpu)


def test_gpu_bound():
    assert analyze([snap(40, [50, 30], 98)] * 5).verdict == "GPU"


def test_cpu_bound_by_single_core():
    assert analyze([snap(30, [100, 10, 10], 50)] * 5).verdict == "CPU"


def test_balanced():
    assert analyze([snap(40, [50, 40], 60)] * 5).verdict == "Equilibrado"


def test_no_gpu_telemetry():
    assert analyze([snap(20, [20], None)]).verdict == "Indeterminado"
    assert analyze([snap(95, [99], None)]).verdict == "CPU"


def test_empty():
    assert analyze([]).samples == 0
