import json

import pytest

from pc_polimata import i18n
from pc_polimata.core import settings as st
from pc_polimata.core.units import format_temp


def test_format_temp():
    assert format_temp(None) == "n/d"
    assert format_temp(50) == "50 °C"
    assert format_temp(100, "F") == "212 °F"
    with pytest.raises(ValueError):
        format_temp(1, "K")


def test_settings_roundtrip(tmp_path):
    s = st.Settings(language="en", temperature_unit="F", refresh_ms=500)
    st.save_settings(s, tmp_path)
    assert st.load_settings(tmp_path) == s


def test_settings_defaults_on_missing_or_corrupt(tmp_path):
    assert st.load_settings(tmp_path) == st.Settings()
    (tmp_path / "settings.json").write_text("{not json")
    assert st.load_settings(tmp_path) == st.Settings()


def test_settings_ignores_unknown_and_rejects_invalid(tmp_path):
    (tmp_path / "settings.json").write_text(json.dumps({"language": "en", "api_key": "x"}))
    assert st.load_settings(tmp_path).language == "en"
    (tmp_path / "settings.json").write_text(json.dumps({"refresh_ms": 1}))
    assert st.load_settings(tmp_path) == st.Settings()
    with pytest.raises(ValueError):
        st.save_settings(st.Settings(language="fr"), tmp_path)


def test_config_dir_respects_xdg(monkeypatch, tmp_path):
    monkeypatch.setattr(st.sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert st.config_dir() == tmp_path / "pc-polimata"


def test_tr_switches_language():
    try:
        assert i18n.tr("Rede") == "Rede"
        i18n.set_language("en")
        assert i18n.tr("Rede") == "Network"
        assert i18n.tr("texto sem tradução") == "texto sem tradução"
    finally:
        i18n.set_language("pt")
    with pytest.raises(ValueError):
        i18n.set_language("xx")


def test_cli_tools(tmp_path, monkeypatch, capsys):
    import json as _json

    from pc_polimata import cli
    from pc_polimata.core import exchange

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert cli.main(["--list-plugins"]) == 0 and "uptime" in capsys.readouterr().out
    assert cli.main(["--export-runs", str(tmp_path / "x.json")]) == 1  # histórico vazio
    from pc_polimata.core.history import HistoryStore

    store = HistoryStore()
    store.save_run("cpu", {"single_core_score": 100.0, "multi_core_score": 400.0})
    store.close()
    capsys.readouterr()
    out = tmp_path / "a.json"
    assert cli.main(["--export-runs", str(out)]) == 0
    assert exchange.import_bundle(out).runs
    capsys.readouterr()
    assert cli.main(["--compare", str(out), str(out)]) == 0
    rows = _json.loads(capsys.readouterr().out)["rows"]
    assert rows[0]["winner"] == "tie"
    assert cli.main(["--compare", str(out), str(tmp_path / "missing.json")]) == 2
    csv = tmp_path / "f.csv"
    csv.write_text("Application,MsBetweenPresents\ng.exe,10\ng.exe,20\n")
    capsys.readouterr()
    assert cli.main(["--fps-csv", str(csv), "--process", "g.exe"]) == 0
    assert _json.loads(capsys.readouterr().out)["format"] == "presentmon"
    mango = tmp_path / "m.csv"
    mango.write_text("fps,frametime\n50,20\n")
    assert cli.main(["--fps-csv", str(mango)]) == 0
    assert _json.loads(capsys.readouterr().out)["format"] == "mangohud"
    assert cli.follow_fps(str(mango), None, interval=0, max_polls=2) == 0
    assert capsys.readouterr().out.count("FPS 50") == 2
    assert cli.main(["--fps-csv", str(tmp_path / "nope.csv")]) == 2
    capsys.readouterr()
    assert cli.main(["--plugins"]) == 0
    assert "uptime" in _json.loads(capsys.readouterr().out)["plugins"]
