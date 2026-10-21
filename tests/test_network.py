import io
from itertools import count

import pytest

from pc_polimata.core import network


class FakeSock:
    def close(self):
        pass


def fake_clock(step=0.010):
    ticks = count()
    return lambda: next(ticks) * step


def test_tcp_latency_success():
    r = network.tcp_latency("1.1.1.1", count=3, connect=lambda *a, **k: FakeSock(), clock=fake_clock())
    assert r.samples_ms == pytest.approx([10.0, 10.0, 10.0])
    assert (r.avg_ms, r.min_ms, r.jitter_ms, r.failures) == (10.0, 10.0, 0.0, 0)


def test_tcp_latency_all_fail():
    def refuse(*a, **k):
        raise OSError("unreachable")

    r = network.tcp_latency("8.8.8.8", count=2, connect=refuse)
    assert r.failures == 2 and r.avg_ms is None and r.to_dict()["avg_ms"] is None


class FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_download_full():
    opener = lambda req, timeout: FakeResp(b"x" * 1_000_000)  # noqa: E731
    r = network.download_throughput(opener=opener, clock=fake_clock(0.1), max_bytes=10**9)
    assert r.bytes_received == 1_000_000 and not r.timed_out and r.mbps > 0


def test_download_timeout():
    opener = lambda req, timeout: FakeResp(b"x" * 10**7)  # noqa: E731
    r = network.download_throughput(opener=opener, timeout=0.5, clock=fake_clock(0.1), chunk_size=1000)
    assert r.timed_out and r.bytes_received < 10**7


def test_download_error():
    def fail(req, timeout):
        raise OSError("dns")

    r = network.download_throughput(opener=fail, clock=fake_clock())
    assert r.error == "dns" and r.mbps == 0.0


def test_list_interfaces_shape():
    ifaces = network.list_interfaces()
    assert all({"name", "is_up", "ipv4"} <= set(i) for i in ifaces)
