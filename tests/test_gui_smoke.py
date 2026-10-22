"""Smoke test da GUI: só roda quando há display (ex.: xvfb-run pytest)."""

import os

import pytest

pytest.importorskip("customtkinter")
if not os.environ.get("DISPLAY") and os.name != "nt":
    pytest.skip("sem display", allow_module_level=True)


@pytest.mark.parametrize("language", ["pt", "en"])
def test_app_builds_all_tabs(tmp_path, monkeypatch, language):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
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
    finally:
        app.destroy()
        i18n.set_language("pt")
