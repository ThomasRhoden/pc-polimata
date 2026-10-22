"""Thread de sensores, log em arquivo e streams ausentes (exe --windowed)."""

import logging
import sys
import threading
import time

from pc_polimata.core import runtime, sensors, system_info


def test_poller_delivers_latest_once():
    calls = []
    poller = runtime.BackgroundPoller(lambda: calls.append(1) or len(calls), interval_s=0.01)
    assert poller.take() is None
    poller.poll_once()
    poller.poll_once()
    assert poller.take() == 2
    assert poller.take() is None


def test_poller_thread_runs_off_main_and_stops():
    seen: list[str] = []
    done = threading.Event()

    def read():
        seen.append(threading.current_thread().name)
        done.set()
        return 1

    poller = runtime.BackgroundPoller(read, interval_s=lambda: 0.01, name="t-poll").start()
    assert done.wait(2)
    poller.stop(timeout=2)
    assert not poller.running
    assert seen[0] == "t-poll"


def test_poller_respects_enabled_and_survives_errors():
    flag = {"on": False}
    count = {"n": 0}

    def read():
        count["n"] += 1
        raise RuntimeError("boom")

    poller = runtime.BackgroundPoller(read, interval_s=0.01, enabled=lambda: flag["on"]).start()
    time.sleep(0.05)
    assert count["n"] == 0
    flag["on"] = True
    deadline = time.time() + 2
    while poller.errors < 2 and time.time() < deadline:
        time.sleep(0.01)
    poller.stop(timeout=2)
    assert poller.errors >= 2 and poller.take() is None


def test_ensure_std_streams(monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    runtime.ensure_std_streams()
    print("ok")  # não pode quebrar
    print("ok", file=sys.stderr)
    assert sys.stdout is not None and sys.stderr is not None


def test_setup_logging_writes_file(tmp_path):
    logger = logging.getLogger("pc_polimata")
    old = list(logger.handlers)
    logger.handlers.clear()
    try:
        path = runtime.setup_logging(tmp_path)
        assert path == tmp_path / runtime.LOG_NAME
        assert runtime.setup_logging(tmp_path / "other") == path  # idempotente
        logging.getLogger("pc_polimata.test").info("hello")
        for h in logger.handlers:
            h.flush()
        assert "hello" in path.read_text(encoding="utf-8")
    finally:
        for h in logger.handlers:
            h.close()
        logger.handlers[:] = old


def test_setup_logging_unwritable(tmp_path):
    logger = logging.getLogger("pc_polimata")
    old = list(logger.handlers)
    logger.handlers.clear()
    blocker = tmp_path / "file"
    blocker.write_text("x")
    try:
        assert runtime.setup_logging(blocker / "sub") is None
    finally:
        logger.handlers[:] = old


def test_com_initialized_noop_off_windows():
    with runtime.com_initialized():
        pass


def test_com_initialized_windows(monkeypatch):
    import types

    events = []
    fake = types.SimpleNamespace(CoInitialize=lambda: events.append("in"), CoUninitialize=lambda: events.append("out"))
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "pythoncom", fake)
    with runtime.com_initialized():
        events.append("body")
    assert events == ["in", "body", "out"]


def test_system_info_cached(monkeypatch):
    calls = []
    monkeypatch.setattr(system_info, "get_system_info", lambda: calls.append(1) or {"n": len(calls)})
    system_info._CACHE.clear()
    assert system_info.get_system_info_cached() is system_info.get_system_info_cached()
    assert system_info.get_system_info_cached(refresh=True) == {"n": 2}
    system_info._CACHE.clear()


def test_sensor_monitor_backs_off_missing_sensors(monkeypatch):
    gpu_calls, temp_calls = [], []
    monkeypatch.setattr(sensors, "get_gpus", lambda: gpu_calls.append(1) or [])
    monkeypatch.setattr(sensors, "read_cpu_temperature", lambda: temp_calls.append(1))
    mon = sensors.SensorMonitor()
    for _ in range(3):
        snap = mon.read()
    assert snap.gpu_percent is None and snap.cpu_temp_c is None
    assert gpu_calls == [1] and temp_calls == [1]
    mon._gpu_missing_until = mon._temp_missing_until = 0.0
    mon.read()
    assert len(gpu_calls) == 2 and len(temp_calls) == 2
