import json

import pytest

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


def test_cli_full_headless(tmp_path, monkeypatch):
    monkeypatch.setenv("PC_POLIMATA_CONFIG_DIR", str(tmp_path / "pc-polimata"))
    for var in ("PC_POLIMATA_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    out = tmp_path / "r.json"
    argv = ["--benchmark", "--duration", "0.2", "--memory", "--games", "--smart", "--diagnose", "-o", str(out)]
    assert main(argv) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert {"cpu_benchmark", "memory_benchmark", "games_estimate", "diagnosis", "disk_health"} <= set(data)
    from pc_polimata.core.history import HistoryStore

    store = HistoryStore(tmp_path / "pc-polimata" / "history.sqlite3")
    assert {r.kind for r in store.list_runs()} == {"cpu", "disk", "memory"}
    store.close()


def test_html_template_tables_and_summary():
    data = report.build_report(
        {"cpu": {"name": "Ryzen"}, "memory": {"total_gb": 16}, "gpus": []},
        disk_health=[{"device": "/dev/sda", "status": "OK"}],
        diagnosis={"score": 90},
    )
    text = report.to_html(data)
    assert "<table class='grid'>" in text and "Saúde dos discos (SMART)" in text and "90/100" in text


def test_pdf_export(tmp_path):
    pytest.importorskip("reportlab")
    out = report.save_report(report.build_report({"cpu": {"name": "X"}}, extra=[{"a": 1}]), tmp_path / "r.pdf")
    assert out.read_bytes().startswith(b"%PDF")


def test_pdf_without_reportlab(tmp_path, monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("reportlab"):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(report.PdfUnavailableError, match="HTML"):
        report.save_report(report.build_report({}), tmp_path / "r.pdf")
