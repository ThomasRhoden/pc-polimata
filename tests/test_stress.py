import pytest

from pc_polimata.core.stress import StressConfig, StressTest, check_limits


def test_config_validation():
    with pytest.raises(ValueError):
        StressConfig(duration_s=0)
    with pytest.raises(ValueError):
        StressConfig(workers=0)


def test_check_limits():
    cfg = StressConfig(duration_s=1, max_temp_c=80)
    assert check_limits(None, cfg) is None
    assert check_limits(70, cfg) is None
    assert "limite" in check_limits(85, cfg)


def test_stops_on_temperature_limit():
    cfg = StressConfig(duration_s=30, max_temp_c=80, workers=1, poll_interval_s=0.1)
    result = StressTest(cfg, temp_reader=lambda: 85.0).run()
    assert "limite" in result.stop_reason
    assert result.elapsed_s < 10


def test_runs_for_duration():
    cfg = StressConfig(duration_s=0.5, max_temp_c=None, workers=1, poll_interval_s=0.1)
    result = StressTest(cfg, temp_reader=lambda: None).run()
    assert result.stop_reason == "duração concluída"
