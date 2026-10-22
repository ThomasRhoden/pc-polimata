"""Smoke test da GUI: só roda quando há display (ex.: xvfb-run pytest)."""

import os

import pytest

pytest.importorskip("customtkinter")
if not os.environ.get("DISPLAY") and os.name != "nt":
    pytest.skip("sem display", allow_module_level=True)


@pytest.mark.parametrize("language", ["pt", "en"])
def test_app_builds_all_tabs(tmp_path, monkeypatch, language):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("PC_POLIMATA_NO_TRAY", "1")
    from pc_polimata import i18n
    from pc_polimata.core.sensors import SensorSnapshot
    from pc_polimata.core.settings import Settings
    from pc_polimata.gui.app import TABS, PolimataApp

    app = PolimataApp(Settings(language=language, alert_cpu_temp_c=50))
    try:
        app.update()
        assert set(app.tab_objects) == {name for name, _ in TABS}
        app.on_snapshot(SensorSnapshot(0, 10, [10], 20, 0, 0, cpu_temp_c=70))
        app.update()
        assert app.banner.winfo_ismapped() and app.alert_log
        assert "alerts" in app.build_report()
        assert "uptime" in app.build_report()["plugins"]
        assert any("uptime" in name for name in app.tabs._name_list)  # aba criada pelo plugin
        assert app.tray_active is False
        app.toggle_overlay()
        app.update()
        assert app.overlay is not None and "CPU" in app.overlay.label.cget("text")
        app.toggle_overlay()
        assert app.overlay is None
        app.toggle_monitoring()
        assert app.monitoring is False
        compare = app.tab_objects["Comparar"]
        compare.use_local("a")
        compare.use_local("b")
        assert "A:" in compare.box.get("1.0", "end")
    finally:
        app.destroy()
        i18n.set_language("pt")


def test_tray_helpers(monkeypatch):
    pytest.importorskip("PIL")
    from pc_polimata.gui import tray

    img = tray.make_image(32)
    assert img.size == (32, 32)
    called = []
    icon = tray.TrayIcon({"quit": lambda: called.append("quit")}, lambda: True)
    icon._post("quit")()
    icon._post("unknown")()
    icon.drain()
    assert called == ["quit"]
    monkeypatch.setenv("PC_POLIMATA_NO_TRAY", "1")
    assert not tray.tray_supported() and icon.start() is False
    icon.set_tooltip("x")
    icon.stop()
