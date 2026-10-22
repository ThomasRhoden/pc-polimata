from pathlib import Path

import pytest

from pc_polimata.core import live, presentmon
from pc_polimata.core.sensors import SensorSnapshot

FIXTURE = Path(__file__).parent / "fixtures" / "presentmon_v1.csv"


def test_frame_stats_basic_and_one_percent_low():
    times = [10.0] * 99 + [100.0]
    s = presentmon.frame_stats(times)
    assert s.frames == 100
    assert s.avg_fps == pytest.approx(1000 / 10.9, abs=0.1)
    assert s.low_1_percent_fps == 10.0  # o pior 1% = 1 frame de 100 ms
    assert s.max_frametime_ms == 100.0 and s.p99_frametime_ms == 100.0


def test_frame_stats_rejects_empty():
    with pytest.raises(ValueError):
        presentmon.frame_stats([0, -1])


def test_parse_v1_filters_process_and_skips_na():
    s = presentmon.parse_csv(FIXTURE.read_text(), "GAME.EXE")
    assert s.frames == 3 and s.process == "GAME.EXE"
    assert s.max_frametime_ms == 50.0


def test_parse_without_filter_picks_busiest_process():
    s = presentmon.parse_csv(FIXTURE.read_text())
    assert s.frames == 4 and s.process == "game.exe"


def test_parse_v2_frametime_column():
    csv = "Application,FrameTime\nx.exe,10\nx.exe,20\n"
    assert presentmon.parse_csv(csv).avg_frametime_ms == 15.0


def test_parse_without_known_column():
    with pytest.raises(ValueError, match="frametime"):
        presentmon.parse_csv("a,b\n1,2\n")


def test_find_presentmon(tmp_path):
    exe = tmp_path / "pm.exe"
    exe.write_text("")
    assert presentmon.find_presentmon(lambda _n: None, {"PRESENTMON_PATH": str(exe)}) == str(exe)
    assert presentmon.find_presentmon(lambda n: "/x/" + n if n == "PresentMon" else None, {}) == "/x/PresentMon"
    pf = tmp_path / "pf"
    (pf / "Intel" / "PresentMon" / "2.3").mkdir(parents=True)
    (pf / "Intel" / "PresentMon" / "2.3" / "PresentMon-2.3.0-x64.exe").write_text("")
    assert presentmon.find_presentmon(lambda _n: None, {"ProgramFiles": str(pf)}).endswith("x64.exe")
    assert presentmon.find_presentmon(lambda _n: None, {}) is None


def test_capture_runs_command_and_parses(tmp_path):
    calls = []

    def runner(cmd, **kw):
        calls.append((cmd, kw))
        out = Path(cmd[cmd.index("--output_file") + 1])
        out.write_text(FIXTURE.read_text())

    s = presentmon.capture("game.exe", 5, exe="pm.exe", runner=runner)
    cmd, kw = calls[0]
    assert cmd[:3] == ["pm.exe", "--process_name", "game.exe"] and "--terminate_after_timed" in cmd
    assert kw["timeout"] == 35 and s.frames == 3


def test_capture_without_presentmon(monkeypatch):
    monkeypatch.setattr(presentmon, "find_presentmon", lambda: None)
    with pytest.raises(FileNotFoundError):
        presentmon.capture("game.exe")


SNAP = SensorSnapshot(0, 42.4, [42], 61.0, 0, 0, cpu_temp_c=70.2, gpu_percent=None, gpu_temp_c=None)


@pytest.mark.parametrize(
    ("corner", "expected"),
    [
        ("top-left", "280x120+16+16"),
        ("top-right", "280x120+1624+16"),
        ("bottom-left", "280x120+16+944"),
        ("bottom-right", "280x120+1624+944"),
    ],
)
def test_overlay_geometry(corner, expected):
    assert live.overlay_geometry(live.OverlayConfig(corner), 1920, 1080) == expected


def test_overlay_config_validation():
    with pytest.raises(ValueError):
        live.OverlayConfig(corner="middle").validate()
    with pytest.raises(ValueError):
        live.OverlayConfig(size="huge").validate()
    with pytest.raises(ValueError):
        live.OverlayConfig(opacity=0.05).validate()


def test_overlay_lines_and_fps():
    lines = live.overlay_lines(SNAP, "C", fps="FPS 144")
    assert lines[0].startswith("CPU   42%") and "70 °C" in lines[0]
    assert lines[1] == "GPU     —  n/d" and lines[-1] == "FPS 144"
    assert "158 °F" in live.overlay_lines(SNAP, "F")[0]


def test_tray_tooltip():
    assert live.tray_tooltip(None) == "PC Polimata"
    tip = live.tray_tooltip(SNAP)
    assert tip == "PC Polimata — CPU 42% 70 °C" and "GPU" not in tip
    paused = live.tray_tooltip(SensorSnapshot(0, 5, [5], 5, 0, 0, gpu_percent=30, gpu_temp_c=55), monitoring=False)
    assert "(II)" in paused and "GPU 30% 55 °C" in paused and len(paused) <= 127
