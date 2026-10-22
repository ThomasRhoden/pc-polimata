from pathlib import Path
from types import SimpleNamespace

import pytest

from pc_polimata.core import plugins
from pc_polimata.core.settings import Settings, load_settings, save_settings
from pc_polimata.plugins import battery, uptime


class Good:
    name = "good"
    version = "1.2"

    def collect(self):
        return {"x": 1, "obj": object(), "nested": {"t": (1, 2)}}


class Boom:
    name = "boom"
    version = "0.1"

    def collect(self):
        raise RuntimeError("kaboom")

    def create_tab(self, master, app):
        raise ValueError("no gui")


class NotDict:
    name = "notdict"
    version = "0"

    def collect(self):
        return [1, 2]


def ep(name, obj=None, error=None):
    def load():
        if error:
            raise error
        return obj

    return SimpleNamespace(name=name, load=load, dist=SimpleNamespace(name="dist-" + name))


def test_discover_all_sources(tmp_path):
    (tmp_path / "local_ok.py").write_text(
        "class P:\n    name='local'\n    version='3'\n    def collect(self):\n        return {'v': 3}\nplugin = P()\n"
    )
    (tmp_path / "syntax.py").write_text("def broken(:\n")
    (tmp_path / "empty.py").write_text("x = 1\n")
    (tmp_path / "_private.py").write_text("raise SystemExit")
    eps = [ep("good", Good), ep("missing", error=ImportError("nope")), ep("dup", lambda: Good())]
    records = {r.name: r for r in plugins.discover(tmp_path, lambda: eps)}
    assert records["uptime"].source == "builtin" and records["battery"].plugin is not None
    assert records["good"].source == "entry_point:dist-good" and records["good"].version == "1.2"
    assert "ImportError" in (records["missing"].load_error or "")
    assert records["local"].plugin is not None
    assert "SyntaxError" in (records["syntax"].load_error or "")
    assert "neither" in (records["empty"].load_error or "")
    assert "_private" not in records
    assert list(records).count("good") == 1  # nome duplicado: o primeiro vence


def test_discover_survives_broken_metadata_and_builtin(tmp_path):
    def broken():
        raise OSError("metadata")

    records = plugins.discover(tmp_path / "nope", broken, builtin=["pc_polimata.does_not_exist"])
    assert len(records) == 1 and "ModuleNotFoundError" in (records[0].load_error or "")


def test_resolve_rejects_bad_objects():
    bad = SimpleNamespace(name="", version="1", collect=lambda: {})
    rec = plugins._record(bad, "x", "fallback")
    assert rec.load_error and rec.name == "fallback"
    assert "protocol" in (plugins._record(42, "x", "n").load_error or "")
    mod = SimpleNamespace()
    import types

    m = types.ModuleType("m")
    m.get_plugin = lambda: Good()
    assert plugins._record(m, "x", "m").name == "good"
    del mod


def test_host_isolates_failures_and_disabling():
    records = [plugins._record(o, "test", "?") for o in (Good(), Boom(), NotDict())]
    records.append(plugins.PluginRecord("broken", "?", "x", load_error="E"))
    host = plugins.PluginHost(records, disabled=["notdict"])
    assert [r.name for r in host.enabled()] == ["good", "boom"]
    results = host.collect_all()
    assert results["good"].ok and results["good"].data["nested"] == {"t": [1, 2]}
    assert isinstance(results["good"].data["obj"], str)
    assert not results["boom"].ok and "kaboom" in (results["boom"].error or "")
    assert host.last_errors == {"boom": "RuntimeError: kaboom"}
    assert "TypeError" in (host.collect(records[2]).error or "")
    assert "E" in (host.collect(records[3]).error or "")
    assert results["good"].to_dict()["ok"] is True


def test_host_create_tab():
    host = plugins.PluginHost([])
    boom = plugins._record(Boom(), "t", "?")
    assert boom.has_tab and "no gui" in (host.create_tab(boom, None, None) or "")
    good = plugins._record(Good(), "t", "?")
    assert not good.has_tab and host.create_tab(good, None, None) is None
    seen = []
    ok = SimpleNamespace(name="ok", version="1", collect=dict, create_tab=lambda m, a: seen.append((m, a)))
    assert host.create_tab(plugins.PluginRecord("ok", "1", "t", ok), "M", "A") is None and seen == [("M", "A")]
    assert good.to_dict()["has_tab"] is False


def test_uptime_plugin():
    data = uptime.UptimePlugin(boot_time=0, now=90061).collect()
    assert data["uptime"] == "1d 01h 01m" and data["uptime_seconds"] == 90061
    assert data["boot_time_utc"].startswith("1970-01-01T00:00:00")
    assert uptime.format_duration(3700) == "01h 01m" and uptime.format_duration(-5) == "00h 00m"
    assert uptime.plugin.collect()["uptime_seconds"] >= 0
    assert isinstance(uptime.plugin, plugins.Plugin) and callable(uptime.UptimePlugin.create_tab)


def _bat(root: Path, prefix: str, full: str, design: str):
    d = root / "BAT0"
    d.mkdir(parents=True)
    (d / f"{prefix}_full").write_text(full)
    (d / f"{prefix}_full_design").write_text(design)
    (d / "cycle_count").write_text("321\n")


def test_battery_sysfs_health(tmp_path):
    _bat(tmp_path / "a", "energy", "40000000", "50000000")
    assert battery.sysfs_health(tmp_path / "a") == {"device": "BAT0", "health_percent": 80.0, "cycle_count": 321}
    _bat(tmp_path / "b", "charge", "x", "100")
    assert battery.sysfs_health(tmp_path / "b") is None
    assert battery.sysfs_health(tmp_path / "missing") is None


def test_battery_plugin(monkeypatch, tmp_path):
    monkeypatch.setattr(battery.psutil, "sensors_battery", lambda: None)
    assert battery.BatteryPlugin(tmp_path).collect() == {"present": False}
    fake = SimpleNamespace(percent=55.55, power_plugged=False, secsleft=3600)
    monkeypatch.setattr(battery.psutil, "sensors_battery", lambda: fake)
    _bat(tmp_path, "energy", "45", "50")
    data = battery.BatteryPlugin(tmp_path).collect()
    assert data["percent"] == 55.5 or data["percent"] == 55.6
    assert data["minutes_left"] == 60 and data["health_percent"] == 90.0
    fake.secsleft = battery.psutil.POWER_TIME_UNLIMITED
    assert battery.BatteryPlugin(tmp_path / "none").collect()["minutes_left"] is None


def test_settings_new_fields_roundtrip(tmp_path):
    s = Settings(disabled_plugins=["b", "a", "a"], overlay_corner="bottom-left")
    save_settings(s, tmp_path)
    loaded = load_settings(tmp_path)
    assert loaded.disabled_plugins == ["a", "b"] and loaded.overlay_corner == "bottom-left"
    assert loaded.overlay_config().size == "medium"
    for bad in ({"overlay_opacity": 3}, {"overlay_corner": "x"}, {"disabled_plugins": "abc"}):
        with pytest.raises(ValueError):
            Settings(**bad).validate()  # type: ignore[arg-type]
