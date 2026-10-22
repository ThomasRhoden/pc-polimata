import json

import pytest

from pc_polimata.core import exchange
from pc_polimata.core.history import HistoryStore

SYSTEM = {
    "cpu": {"name": "Ryzen 5 5600", "physical_cores": 6, "logical_cores": 12},
    "gpus": [{"name": "RX 6600"}],
    "memory": {"total_gb": 16.0},
    "os": {"system": "Linux", "release": "6.8"},
}


def _bundle(label, cpu_single, mem_lat, extra_runs=()):
    runs = [
        {
            "kind": "cpu",
            "created_at": "2026-01-01T00:00:00+00:00",
            "metrics": {"single_core_score": 1, "multi_core_score": 1},
        },
        {
            "kind": "cpu",
            "created_at": "2026-02-01T00:00:00+00:00",
            "metrics": {"single_core_score": cpu_single, "multi_core_score": 1000},
        },
        {"kind": "memory", "created_at": "2026-02-01", "metrics": {"bandwidth_gb_s": 20.0, "latency_ns": mem_lat}},
        *extra_runs,
    ]
    return exchange.RunBundle(label, exchange.machine_summary(SYSTEM), runs)


def test_machine_summary_has_no_hostname():
    m = exchange.machine_summary(SYSTEM)
    assert m == {
        "cpu": "Ryzen 5 5600",
        "cores": 6,
        "threads": 12,
        "gpus": ["RX 6600"],
        "ram_gb": 16.0,
        "os": "Linux 6.8",
    }
    assert exchange.machine_summary({})["os"] is None


def test_export_import_roundtrip_from_history(tmp_path):
    store = HistoryStore(":memory:")
    store.save_run("cpu", {"single_core_score": 500.0, "multi_core_score": 3000.0}, note="x")
    runs = store.list_runs("cpu")
    store.close()
    path = exchange.export_bundle(exchange.make_bundle("Sala", SYSTEM, runs), tmp_path / "a.json")
    raw = json.loads(path.read_text())
    assert raw["format"] == exchange.FORMAT and raw["format_version"] == 1 and raw["app_version"]
    loaded = exchange.import_bundle(path)
    assert loaded.label == "Sala" and loaded.runs[0]["metrics"]["single_core_score"] == 500.0
    assert loaded.latest("cpu") is not None and loaded.latest("disk") is None


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ([], "not a PC Polimata"),
        ({"format": "other"}, "not a PC Polimata"),
        ({"format": exchange.FORMAT, "format_version": 99, "runs": []}, "format_version"),
        ({"format": exchange.FORMAT, "format_version": 1, "runs": {}}, "must be a list"),
        ({"format": exchange.FORMAT, "format_version": 1, "runs": [{"kind": "gpu", "metrics": {}}, "x"]}, "no valid"),
        ({"format": exchange.FORMAT, "format_version": 1, "runs": [{"kind": "cpu", "metrics": 3}]}, "no valid"),
    ],
)
def test_bundle_validation(data, message):
    with pytest.raises(ValueError, match=message):
        exchange.bundle_from_dict(data)


def test_import_filters_non_numeric_and_defaults_label(tmp_path):
    data = {
        "format": exchange.FORMAT,
        "format_version": 1,
        "machine": "bad",
        "runs": [{"kind": "disk", "metrics": {"read_mb_s": 100, "evil": "<script>", "flag": True}}],
    }
    b = exchange.bundle_from_dict(data)
    assert b.runs[0]["metrics"] == {"read_mb_s": 100} and b.machine == {} and b.label == "?"
    bad = tmp_path / "bad.json"
    bad.write_text("{nope")
    with pytest.raises(ValueError, match="invalid JSON"):
        exchange.import_bundle(bad)
    big = tmp_path / "big.json"
    big.write_bytes(b" " * (exchange.MAX_FILE_BYTES + 1))
    with pytest.raises(ValueError, match="too large"):
        exchange.import_bundle(big)


def test_compare_bundles_uses_latest_and_direction():
    a = _bundle("A", 1000, 80.0)
    b = _bundle("B", 1200, 100.0, [{"kind": "disk", "created_at": "x", "metrics": {"read_mb_s": 500}}])
    rows = {(r.kind, r.metric): r for r in exchange.compare_bundles(a, b)}
    single = rows[("cpu", "single_core_score")]
    assert single.diff_percent == 20.0 and single.winner == "b"
    assert rows[("cpu", "multi_core_score")].winner == "tie"
    latency = rows[("memory", "latency_ns")]
    assert latency.diff_percent == -25.0 and latency.winner == "a"  # menor latência = melhor
    disk = rows[("disk", "read_mb_s")]
    assert disk.a is None and disk.b == 500 and disk.winner is None
    assert disk.to_dict()["winner"] is None
