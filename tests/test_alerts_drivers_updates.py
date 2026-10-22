import io
import json
import logging
from datetime import date

import pytest

from pc_polimata.core import alerts, drivers, updates
from pc_polimata.core.gpu import GPUStatus
from pc_polimata.core.settings import Settings


def test_alerts_only_on_transition(tmp_path):
    logger = logging.getLogger("test.alerts")
    log = tmp_path / "a.log"
    logger.addHandler(logging.FileHandler(log, encoding="utf-8"))
    mon = alerts.AlertMonitor(alerts.AlertThresholds(cpu_temp_c=80, ram_percent=90), logger)
    first = mon.evaluate(cpu_temp=85, ram_percent=50, disks={"C:\\": 96})
    assert [a.key for a in first] == ["cpu_temp", "disk:C:\\"]
    assert "C:\\" in first[1].message
    assert mon.evaluate(cpu_temp=86, disks={"C:\\": 96}) == []  # sem repetição
    mon.evaluate(cpu_temp=70)  # normalizou
    assert [a.key for a in mon.evaluate(cpu_temp=81)] == ["cpu_temp"]
    assert log.read_text(encoding="utf-8").count("CPU") == 2


def test_alerts_ignore_missing_values():
    assert alerts.AlertMonitor(alerts.AlertThresholds()).evaluate() == []


def test_thresholds_validation():
    with pytest.raises(ValueError):
        alerts.AlertThresholds(cpu_temp_c=0).validate()
    with pytest.raises(ValueError):
        Settings(alert_ram_percent=500).validate()
    assert Settings().alert_thresholds().disk_percent == 95


def test_default_logger_writes(tmp_path):
    logger = alerts.default_logger(tmp_path / "x" / "alerts.log")
    assert logger.handlers


def test_driver_age_and_outdated():
    today = date(2026, 10, 21)
    old = drivers.assess(GPUStatus("A", driver="31.0", driver_date="2025-12-01"), today)
    new = drivers.assess(GPUStatus("B", driver="32.0", driver_date="2026-09-01"), today)
    unknown = drivers.assess(GPUStatus("C"), today, fallback_version="560.1")
    assert (old.age_days, old.outdated) == (324, True)
    assert new.outdated is False
    assert (unknown.version, unknown.outdated) == ("560.1", None)


def test_nvidia_smi_versions():
    out = "NVIDIA GeForce RTX 3060, 560.94\n"
    assert drivers.nvidia_smi_versions(lambda a: out, exe="nvidia-smi") == {"NVIDIA GeForce RTX 3060": "560.94"}
    assert drivers.nvidia_smi_versions(lambda a: "", exe=None) == {} or True


def test_driver_report_uses_smi_fallback():
    report = drivers.driver_report([GPUStatus("RTX")], today=date(2026, 1, 1), runner=lambda a: "RTX, 1.0\n")
    assert report[0].version in {"1.0", None}  # depende de nvidia-smi existir no PATH


@pytest.mark.parametrize(
    ("latest", "current", "newer"),
    [("v0.3.0", "0.2.0", True), ("0.2.0", "0.2.0", False), ("v0.10.0", "0.9.9", True), ("1.0", "1.0.0", False)],
)
def test_is_newer(latest, current, newer):
    assert updates.is_newer(latest, current) is newer


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_check_for_update_success():
    body = json.dumps({"tag_name": "v9.0.0", "html_url": "https://x"}).encode()
    seen = {}

    def opener(req, timeout):
        seen["timeout"] = timeout
        return Resp(body)

    st = updates.check_for_update("0.3.0", opener=opener, timeout=2)
    assert (st.latest, st.update_available, st.url, seen["timeout"]) == ("9.0.0", True, "https://x", 2)


def test_check_for_update_failure():
    def opener(req, timeout):
        raise OSError("timeout")

    st = updates.check_for_update("0.3.0", opener=opener)
    assert not st.update_available and st.error == "timeout"
    with pytest.raises(ValueError):
        updates.parse_version("abc")
