import json

from pc_polimata.cli import main
from pc_polimata.core import report
from pc_polimata.core.sensors import SensorMonitor
from pc_polimata.core.system_info import get_system_info


def test_system_info_shape():
    info = get_system_info()
    assert set(info) == {"os", "cpu", "memory", "disks", "gpus"}
    assert info["cpu"]["logical_cores"] >= 1
    json.dumps(info)


def test_sensor_snapshot():
    snap = SensorMonitor(include_gpu=False).read()
    assert 0 <= snap.cpu_percent <= 100
    assert snap.disk_read_mb_s >= 0


def test_html_escapes_and_saves(tmp_path):
    data = report.build_report({"os": {"name": "<script>"}}, extra=None)
    assert "extra" not in data
    out = report.save_report(data, tmp_path / "r.html")
    text = out.read_text(encoding="utf-8")
    assert "&lt;script&gt;" in text and "<script>" not in text


def test_cli_report_json(tmp_path):
    out = tmp_path / "r.json"
    assert main(["--report", "-o", str(out)]) == 0
    assert "system" in json.loads(out.read_text(encoding="utf-8"))
