import os
import stat
import urllib.error

from pc_polimata.core import diagnosis, secrets


def base_report(**overrides):
    report = {
        "system": {
            "os": {"hostname": "meu-pc"},
            "memory": {"used_percent": 40, "total_gb": 16},
            "disks": [{"mountpoint": "C:\\", "used_percent": 50}],
            "gpus": [],
        }
    }
    report.update(overrides)
    return report


def titles(d):
    return [f.title for f in d.findings]


def test_healthy_system():
    d = diagnosis.rule_based(base_report())
    assert d.score == 100 and titles(d) == ["Nenhum problema detectado"]


def test_problems_sorted_by_severity():
    r = base_report(sensors={"cpu_temp_c": 93}, bottleneck={"verdict": "CPU"})
    r["system"]["memory"] = {"used_percent": 85, "total_gb": 4}
    r["system"]["disks"][0]["used_percent"] = 97
    d = diagnosis.rule_based(r)
    assert [f.severity for f in d.findings][:2] == ["crítico", "crítico"]
    assert any("Gargalo na CPU" in t for t in titles(d))
    assert d.score == 100 - 25 - 25 - 10 - 10


def test_smart_and_network_rules():
    r = base_report(
        disk_health=[{"device": "/dev/sda", "status": "FALHA"}],
        network_latency=[{"host": "1.1.1.1", "avg_ms": None}, {"host": "8.8.8.8", "avg_ms": 150}],
    )
    t = titles(diagnosis.rule_based(r))
    assert "SMART reprovado em /dev/sda" in t and len(t) == 3


def test_llm_success_redacts_hostname():
    captured = {}

    def transport(url, headers, payload, timeout):
        captured.update(url=url, headers=headers, payload=payload)
        return {"choices": [{"message": {"content": " Tudo certo. "}}]}

    d = diagnosis.diagnose(base_report(), api_key="sk-test", base_url="http://x/v1/", transport=transport)
    assert d.llm_analysis == "Tudo certo." and d.source == "regras + LLM"
    assert captured["url"] == "http://x/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer sk-test"
    assert "meu-pc" not in captured["payload"]["messages"][1]["content"]


def test_llm_failure_falls_back():
    def transport(*a):
        raise urllib.error.URLError("offline")

    d = diagnosis.diagnose(base_report(), api_key="k", transport=transport)
    assert d.llm_analysis is None and "offline" in d.llm_error and d.findings


def test_no_key_skips_llm():
    assert diagnosis.diagnose(base_report()).source == "regras"


def test_api_key_sources(tmp_path, monkeypatch):
    for var in secrets.ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    assert secrets.get_api_key(tmp_path) is None
    path = secrets.save_api_key("sk-file-123456", tmp_path)
    assert secrets.get_api_key(tmp_path) == "sk-file-123456"
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    assert secrets.get_api_key(tmp_path) == "sk-env"
    secrets.save_api_key("", tmp_path)
    assert not path.exists()
    assert secrets.mask("sk-file-123456") == "sk-…3456"
