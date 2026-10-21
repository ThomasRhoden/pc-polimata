import json

from pc_polimata.core import smart

SCAN = json.dumps({"devices": [{"name": "/dev/sda"}, {"name": "/dev/nvme0"}]})
SATA = json.dumps(
    {
        "model_name": "Samsung SSD 860",
        "smart_status": {"passed": True},
        "temperature": {"current": 34},
        "power_on_time": {"hours": 12000},
        "ata_smart_attributes": {"table": [{"id": 5, "raw": {"value": 8}}]},
    }
)
NVME = json.dumps(
    {
        "model_name": "WD SN770",
        "smart_status": {"passed": True},
        "nvme_smart_health_information_log": {"percentage_used": 3},
    }
)


def fake_runner(args):
    if "--scan" in args:
        return SCAN
    return SATA if args[-1] == "/dev/sda" else NVME


def test_check_disks():
    sda, nvme = smart.check_disks(fake_runner, exe="smartctl")
    assert (sda.model, sda.reallocated_sectors, sda.status) == ("Samsung SSD 860", 8, "ATENÇÃO")
    assert (nvme.percentage_used, nvme.status) == (3, "OK")
    assert nvme.to_dict()["status"] == "OK"


def test_failed_and_permission():
    failed = smart.parse_smartctl("/dev/sdb", json.dumps({"smart_status": {"passed": False}}))
    assert failed.status == "FALHA"
    denied = smart.parse_smartctl(
        "/dev/sdc",
        json.dumps({"smartctl": {"messages": [{"severity": "error", "string": "Permission denied"}]}}),
    )
    assert denied.status == "n/d" and "Permission" in denied.error
    assert smart.parse_smartctl("/dev/x", "garbage").error


def test_no_smartctl(monkeypatch):
    monkeypatch.setattr(smart, "find_smartctl", lambda: None)
    assert smart.check_disks() == []
