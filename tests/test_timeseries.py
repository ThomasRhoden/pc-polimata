import pytest

from pc_polimata.core.timeseries import RollingSeries, to_points


def test_rolling_series_keeps_last_n():
    s = RollingSeries(["cpu", "gpu"], maxlen=3)
    for i in range(5):
        s.append(cpu=i)
    assert s.values("cpu") == [2, 3, 4]
    assert s.values("gpu") == [None, None, None]
    assert len(s) == 3


def test_rolling_series_validation():
    with pytest.raises(ValueError):
        RollingSeries(["a"], maxlen=1)


def test_to_points_right_aligned_and_clamped():
    [seg] = to_points([0, 150], width=100, height=50, maxlen=3)
    assert seg == [(50.0, 50.0), (100.0, 0.0)]


def test_to_points_breaks_on_none():
    segs = to_points([10, None, 20, 30], width=30, height=100, maxlen=4)
    assert len(segs) == 2 and len(segs[1]) == 2


def test_to_points_with_vmin():
    [seg] = to_points([90, 100], width=10, height=100, maxlen=2, vmin=80)
    assert seg == [(0.0, 50.0), (10.0, 0.0)]
    with pytest.raises(ValueError):
        to_points([1], 10, 10, 2, vmax=5, vmin=5)
