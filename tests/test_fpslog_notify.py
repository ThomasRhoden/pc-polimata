from pathlib import Path

import pytest

from pc_polimata.core import fpslog, notify

FIX = Path(__file__).parent / "fixtures"
MANGO = (FIX / "mangohud.csv").read_text()
PM = (FIX / "presentmon_v1.csv").read_text()


def test_detect_format():
    assert fpslog.detect_format(MANGO) == "mangohud"
    assert fpslog.detect_format(PM) == "presentmon"
    assert fpslog.detect_format("fps,frametime,elapsed\n60,16.6,1\n") == "mangohud"  # MangoHud antigo
    with pytest.raises(ValueError):
        fpslog.detect_format("a,b\n1,2\n")


def test_parse_mangohud_and_specs():
    kind, s = fpslog.parse_log(MANGO, label="game")
    assert kind == "mangohud" and s.frames == 3 and s.process == "game"
    assert s.avg_frametime_ms == pytest.approx(13.33, abs=0.01) and s.max_frametime_ms == 20.0
    assert fpslog.mangohud_system(MANGO)["gpu"] == "AMD Radeon RX 6800 XT"
    assert fpslog.mangohud_system(PM) == {}
    with pytest.raises(ValueError):
        fpslog.parse_mangohud("os,cpu\nx,y\n")


def test_mangohud_microseconds_are_converted():
    s = fpslog.parse_mangohud("fps,frametime\n60,16666\n60,16666\n")
    assert s.avg_frametime_ms == pytest.approx(16.67, abs=0.01)


def test_parse_log_presentmon_process_filter():
    kind, s = fpslog.parse_log(PM, "game.exe")
    assert kind == "presentmon" and s.frames == 3


def test_newest_csv(tmp_path):
    assert fpslog.newest_csv(tmp_path) is None
    import os

    old, new = tmp_path / "a.csv", tmp_path / "b.csv"
    old.write_text("x")
    new.write_text("y")
    (tmp_path / "b_summary.csv").write_text("z")
    os.utime(old, (1, 1))
    assert fpslog.newest_csv(tmp_path) == new


def test_tail_reads_incrementally_with_partial_lines(tmp_path):
    path = tmp_path / "live.csv"
    tail = fpslog.FrameLogTail(path, window_s=0.05)
    assert tail.poll() is None  # ainda não existe
    head = MANGO.split("100.0,10.0")[0]
    path.write_text(head + "100.0,10.0,1\n100.0,10.")
    s = tail.poll()
    assert tail.kind == "mangohud" and s is not None and s.frames == 1  # linha incompleta aguardando
    with path.open("a") as fh:
        fh.write("0,1\n50,20.0,1\n" + "100,10.0,1\n" * 10)
    s = tail.poll()
    assert tail.total_frames == 13
    assert s is not None and s.frames <= 6 and sum([10.0] * 5) <= 50  # janela de 50 ms
    path.write_text("Application,MsBetweenPresents\r\ng.exe,5\r\nother.exe,99\r\n")  # truncado -> reinicia
    tail.process = "g.exe"
    s = tail.poll()
    assert tail.kind == "presentmon" and s is not None and s.frames == 1 and s.avg_frametime_ms == 5


def test_tail_ignores_bad_rows(tmp_path):
    path = tmp_path / "x.csv"
    path.write_text("junk\nApplication,Other\nx,1\n")
    tail = fpslog.FrameLogTail(path)
    assert tail.poll() is None
    path.write_text("fps,frametime\n\n1\nNaN?,x\n0,-1\n")
    assert fpslog.FrameLogTail(path).poll() is None


def test_folder_tail_switches_to_newest(tmp_path):
    import os

    ft = fpslog.FolderTail(tmp_path / "missing")
    assert ft.poll() is None and ft.kind is None
    ft = fpslog.FolderTail(tmp_path)
    a = tmp_path / "a.csv"
    a.write_text("fps,frametime\n100,10\n")
    os.utime(a, (1, 1))
    assert ft.poll().frames == 1 and ft.kind == "mangohud"
    b = tmp_path / "b.csv"
    b.write_text("fps,frametime\n50,20\n50,20\n")
    s = ft.poll()
    assert ft.current.path == b and s.avg_frametime_ms == 20


def test_overlay_text():
    assert fpslog.overlay_text(None) is None
    s = fpslog.parse_mangohud(MANGO)
    assert fpslog.overlay_text(s) == "FPS 75  1% 50  13.3 ms"


def test_live_command():
    from pc_polimata.core import presentmon

    cmd = presentmon.live_command("pm.exe", "g.exe", Path("o.csv"))
    assert "--timed" not in cmd and cmd[-1] == "--stop_existing_session" and "g.exe" in cmd


# ---------- notificações ----------
class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_throttle_per_key_and_global():
    clock = Clock()
    th = notify.Throttle(per_key_s=300, max_per_minute=2, clock=clock)
    assert th.allow("cpu") and not th.allow("cpu")
    assert th.allow("ram") and not th.allow("gpu")  # limite global de 2/min
    clock.t = 61
    assert th.allow("gpu") and not th.allow("cpu")
    clock.t = 301
    assert th.allow("cpu")


def test_notifier_sends_throttles_and_survives_errors():
    sent = []
    n = notify.Notifier(("fake", lambda t, m: sent.append((t, m))), notify.Throttle(clock=Clock()))
    assert n.available and n.backend_name == "fake"
    assert n.notify("cpu", "T", "hot") and not n.notify("cpu", "T", "hot")
    assert sent == [("T", "hot")]

    def boom(t, m):
        raise OSError("dbus down")

    bad = notify.Notifier(("bad", boom))
    assert not bad.notify("k", "t", "m") and "dbus down" in (bad.last_error or "")
    assert not notify.Notifier(None).notify("k", "t", "m")
    assert not notify.Notifier(("fake", lambda t, m: None), enabled=False).notify("k", "t", "m")


def test_find_backend_linux_notify_send():
    calls = []
    name, send = notify.find_backend("linux", lambda n: "/usr/bin/notify-send", lambda *a, **k: calls.append(a[0]))
    assert name == "notify-send"
    send("Title", "msg")
    assert calls[0][0] == "/usr/bin/notify-send" and calls[0][-2:] == ["Title", "msg"]


def test_find_backend_fallbacks(monkeypatch):
    monkeypatch.setattr(notify, "_plyer_backend", lambda: None)
    monkeypatch.setattr(notify, "_winotify_backend", lambda: None)
    assert notify.find_backend("linux", lambda n: None) is None
    assert notify.find_backend("win32", lambda n: None) is None
    marker = lambda t, m: None  # noqa: E731
    monkeypatch.setattr(notify, "_winotify_backend", lambda: marker)
    assert notify.find_backend("win32") == ("winotify", marker)
    assert notify.find_backend("linux", loaders=(lambda: None, lambda: marker)) == ("custom1", marker)


def test_find_backend_macos():
    calls = []
    name, send = notify.find_backend("darwin", lambda n: "/usr/bin/osascript", lambda *a, **k: calls.append(a[0]))
    send('Say "hi"', "back\\slash")
    assert name == "osascript" and '\\"hi\\"' in calls[0][2] and "back\\\\slash" in calls[0][2]


def test_optional_backends_import(monkeypatch):
    import sys
    import types

    shown = []
    win = types.ModuleType("winotify")

    class Notification:
        def __init__(self, **kw):
            self.kw = kw

        def show(self):
            shown.append(self.kw)

    win.Notification = Notification
    ply = types.ModuleType("plyer")
    ply.notification = types.SimpleNamespace(notify=lambda **kw: shown.append(kw))
    monkeypatch.setitem(sys.modules, "winotify", win)
    monkeypatch.setitem(sys.modules, "plyer", ply)
    notify._winotify_backend()("a", "b")
    notify._plyer_backend()("c", "d")
    assert shown[0]["title"] == "a" and shown[1]["message"] == "d"
    monkeypatch.setitem(sys.modules, "plyer", None)
    assert notify._plyer_backend() is None
    assert notify.Notifier.auto(enabled=False).backend is None
