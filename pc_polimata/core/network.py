"""Diagnóstico de rede sem privilégios de administrador.

A latência é medida pelo tempo de um `connect()` TCP (não ICMP), então
funciona sem root/admin. Rede e relógio são injetáveis para testes.
"""

from __future__ import annotations

import socket
import statistics
import time
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass

import psutil

DEFAULT_TARGETS = (("1.1.1.1", 443), ("8.8.8.8", 443))
DEFAULT_DOWNLOAD_URL = "https://speed.cloudflare.com/__down?bytes=25000000"


@dataclass
class LatencyResult:
    host: str
    port: int
    samples_ms: list[float]
    failures: int

    @property
    def avg_ms(self) -> float | None:
        return round(statistics.fmean(self.samples_ms), 1) if self.samples_ms else None

    @property
    def min_ms(self) -> float | None:
        return round(min(self.samples_ms), 1) if self.samples_ms else None

    @property
    def jitter_ms(self) -> float | None:
        if len(self.samples_ms) < 2:
            return None
        return round(statistics.pstdev(self.samples_ms), 1)

    def to_dict(self) -> dict:
        return {**asdict(self), "avg_ms": self.avg_ms, "min_ms": self.min_ms, "jitter_ms": self.jitter_ms}


@dataclass
class ThroughputResult:
    url: str
    bytes_received: int
    seconds: float
    timed_out: bool
    error: str | None = None

    @property
    def mbps(self) -> float:
        """Megabits por segundo."""
        return round(self.bytes_received * 8 / 1e6 / self.seconds, 2) if self.seconds > 0 else 0.0

    def to_dict(self) -> dict:
        return {**asdict(self), "mbps": self.mbps}


def tcp_latency(
    host: str,
    port: int = 443,
    count: int = 4,
    timeout: float = 2.0,
    connect: Callable[..., socket.socket] = socket.create_connection,
    clock: Callable[[], float] = time.perf_counter,
) -> LatencyResult:
    samples, failures = [], 0
    for _ in range(count):
        start = clock()
        try:
            sock = connect((host, port), timeout=timeout)
        except OSError:
            failures += 1
            continue
        samples.append((clock() - start) * 1000)
        sock.close()
    return LatencyResult(host, port, samples, failures)


def measure_latencies(targets=DEFAULT_TARGETS, **kwargs) -> list[LatencyResult]:
    return [tcp_latency(h, p, **kwargs) for h, p in targets]


def list_interfaces() -> list[dict]:
    stats = psutil.net_if_stats()
    out = []
    for name, addrs in psutil.net_if_addrs().items():
        st = stats.get(name)
        out.append(
            {
                "name": name,
                "is_up": bool(st and st.isup),
                "speed_mbps": st.speed if st else None,
                "ipv4": [a.address for a in addrs if a.family == socket.AF_INET],
                "ipv6": [a.address for a in addrs if a.family == socket.AF_INET6],
            }
        )
    return out


def download_throughput(
    url: str = DEFAULT_DOWNLOAD_URL,
    timeout: float = 10.0,
    max_bytes: int = 25_000_000,
    opener: Callable[..., object] = urllib.request.urlopen,
    clock: Callable[[], float] = time.perf_counter,
    chunk_size: int = 64 * 1024,
) -> ThroughputResult:
    """Baixa até `max_bytes` ou até `timeout` segundos e mede a taxa."""
    received, start = 0, clock()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "pc-polimata"})
        with opener(req, timeout=timeout) as resp:
            while received < max_bytes:
                if clock() - start >= timeout:
                    return ThroughputResult(url, received, clock() - start, timed_out=True)
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                received += len(chunk)
    except OSError as exc:
        return ThroughputResult(url, received, clock() - start, timed_out=False, error=str(exc))
    return ThroughputResult(url, received, clock() - start, timed_out=False)
