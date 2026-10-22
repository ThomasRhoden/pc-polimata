"""Logs de frametime: MangoHud (Linux), detecção automática e leitura ao vivo.

MangoHud (``MANGOHUD_CONFIG=output_folder=~/mangohud_logs`` e Shift+F2 no jogo)
grava um CSV assim::

    os,cpu,gpu,ram,kernel,driver,cpuscheduler
    Arch Linux,AMD Ryzen 7 5800X,...
    --------------------FRAME METRICS--------------------
    fps,frametime,cpu_load,gpu_load,...,elapsed
    143.9,6.95,...

A linha separadora não existe em versões antigas; em ambas procuramos o
cabeçalho que começa com ``fps,frametime``. ``frametime`` está em ms.

`FrameLogTail` acompanha um CSV que ainda está sendo escrito (PresentMon ou
MangoHud), lendo só os bytes novos a cada chamada.
"""

from __future__ import annotations

import csv
import io
from collections import deque
from collections.abc import Sequence
from pathlib import Path

from pc_polimata.core import presentmon
from pc_polimata.core.presentmon import FrameStats, frame_stats

MANGOHUD_HEADER_PREFIX = "fps,frametime"
FORMATS = ("presentmon", "mangohud")


def detect_format(text: str) -> str:
    """'presentmon' ou 'mangohud' pelo cabeçalho; ValueError se nenhum."""
    for line in text.splitlines()[:50]:
        low = line.strip().lower()
        if low.startswith(MANGOHUD_HEADER_PREFIX):
            return "mangohud"
        cols = [c.strip() for c in line.split(",")]
        if any(c in cols for c in presentmon.FRAMETIME_COLUMNS):
            return "presentmon"
    raise ValueError("unknown frametime log format (expected PresentMon or MangoHud CSV)")


def _mangohud_rows(text: str) -> tuple[list[str], list[list[str]]]:
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.strip().lower().startswith(MANGOHUD_HEADER_PREFIX)), None)
    if start is None:
        raise ValueError("MangoHud header 'fps,frametime,...' not found")
    rows = list(csv.reader(io.StringIO("\n".join(lines[start:]))))
    return [c.strip().lower() for c in rows[0]], rows[1:]


def _float(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def mangohud_frametimes(header: Sequence[str], rows: list[list[str]]) -> list[float]:
    idx = list(header).index("frametime")
    times = [v for r in rows if len(r) > idx and (v := _float(r[idx])) is not None]
    # Algumas versões antigas gravavam µs; frametimes medianos > 1000 ms não são plausíveis.
    if times and sorted(times)[len(times) // 2] > 1000:
        times = [t / 1000 for t in times]
    return times


def mangohud_system(text: str) -> dict[str, str]:
    """Linha de especificações do topo do log (os, cpu, gpu...), se existir."""
    lines = text.splitlines()
    if len(lines) >= 2 and lines[0].lower().startswith("os,"):
        keys = next(csv.reader([lines[0]]))
        values = next(csv.reader([lines[1]]))
        return {k.strip(): v.strip() for k, v in zip(keys, values, strict=False) if v.strip()}
    return {}


def parse_mangohud(text: str, label: str | None = None) -> FrameStats:
    header, rows = _mangohud_rows(text)
    return frame_stats(mangohud_frametimes(header, rows), label)


def parse_log(text: str, process: str | None = None, label: str | None = None) -> tuple[str, FrameStats]:
    """Detecta o formato e devolve (formato, estatísticas). `process` só se aplica ao PresentMon."""
    kind = detect_format(text)
    if kind == "mangohud":
        return kind, parse_mangohud(text, process or label)
    return kind, presentmon.parse_csv(text, process)


def newest_csv(folder: Path) -> Path | None:
    """O CSV mais recente de uma pasta (o MangoHud cria um arquivo novo por sessão)."""
    files = [p for p in folder.glob("*.csv") if not p.name.endswith("_summary.csv")]
    return max(files, key=lambda p: p.stat().st_mtime, default=None)


class FrameLogTail:
    """Lê incrementalmente um CSV em gravação e mantém os últimos `window_s` segundos de frames."""

    def __init__(self, path: str | Path, window_s: float = 5.0, process: str | None = None) -> None:
        self.path = Path(path)
        self.window_ms = window_s * 1000
        self.process = process.lower() if process else None
        self._reset()

    def _reset(self) -> None:
        self.kind: str | None = None
        self._pos = 0
        self._partial = ""
        self._header: list[str] | None = None
        self._column: int | None = None
        self._proc_col: int | None = None
        self._frames: deque[float] = deque()
        self._sum = 0.0
        self.total_frames = 0

    def _set_header(self, cols: list[str]) -> None:
        self._header = cols
        if self.kind == "mangohud":
            self._column = cols.index("frametime") if "frametime" in cols else None
            self._proc_col = None
        else:
            name = next((c for c in presentmon.FRAMETIME_COLUMNS if c in cols), None)
            self._column = cols.index(name) if name else None
            proc = next((c for c in presentmon.PROCESS_COLUMNS if c in cols), None)
            self._proc_col = cols.index(proc) if proc else None

    def _feed_line(self, line: str) -> None:
        if not line.strip():
            return
        if self._header is None:
            low = line.strip().lower()
            if low.startswith(MANGOHUD_HEADER_PREFIX):
                self.kind = "mangohud"
                self._set_header([c.strip().lower() for c in next(csv.reader([line]))])
            elif any(c in line.split(",") for c in presentmon.FRAMETIME_COLUMNS):
                self.kind = "presentmon"
                self._set_header([c.strip() for c in next(csv.reader([line]))])
            return  # linhas de especificação do MangoHud antes do cabeçalho
        if self._column is None:
            return
        row = next(csv.reader([line]))
        if self._proc_col is not None and self.process and len(row) > self._proc_col:
            if row[self._proc_col].strip().lower() != self.process:
                return
        if len(row) <= self._column:
            return
        value = _float(row[self._column])
        if value is None or value <= 0:
            return
        self._frames.append(value)
        self._sum += value
        self.total_frames += 1
        while len(self._frames) > 1 and self._sum - self._frames[0] >= self.window_ms:
            self._sum -= self._frames.popleft()

    def poll(self) -> FrameStats | None:
        """Lê o que foi escrito desde a última chamada; None se ainda não há frames."""
        try:
            size = self.path.stat().st_size
            if size < self._pos:  # arquivo truncado/recriado
                self._reset()
            with self.path.open("rb") as fh:
                fh.seek(self._pos)
                chunk = fh.read()
                self._pos = fh.tell()
        except OSError:
            return None
        text = self._partial + chunk.decode("utf-8", errors="replace")
        lines = text.split("\n")
        self._partial = lines.pop()  # última linha pode estar incompleta
        for line in lines:
            self._feed_line(line.rstrip("\r"))
        if not self._frames:
            return None
        return frame_stats(list(self._frames), self.process)


def overlay_text(stats: FrameStats | None) -> str | None:
    if stats is None:
        return None
    return f"FPS {stats.avg_fps:.0f}  1% {stats.low_1_percent_fps:.0f}  {stats.avg_frametime_ms:.1f} ms"


class FolderTail:
    """Acompanha o CSV mais novo de uma pasta (MangoHud cria um arquivo por sessão de log)."""

    def __init__(self, folder: str | Path, window_s: float = 5.0) -> None:
        self.folder = Path(folder)
        self.window_s = window_s
        self.current: FrameLogTail | None = None

    @property
    def kind(self) -> str | None:
        return self.current.kind if self.current else None

    def poll(self) -> FrameStats | None:
        newest = newest_csv(self.folder) if self.folder.is_dir() else None
        if newest is None:
            return None
        if self.current is None or self.current.path != newest:
            self.current = FrameLogTail(newest, self.window_s)
        return self.current.poll()
