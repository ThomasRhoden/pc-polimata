"""Smoke test da GUI: só roda quando há display (ex.: xvfb-run pytest)."""

import os

import pytest

pytest.importorskip("customtkinter")
if not os.environ.get("DISPLAY") and os.name != "nt":
    pytest.skip("sem display", allow_module_level=True)


def test_app_builds_all_tabs(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from pc_polimata.gui.app import TABS, PolimataApp

    app = PolimataApp()
    try:
        app.update()
        assert set(app.tab_objects) == {name for name, _ in TABS}
    finally:
        app.destroy()
