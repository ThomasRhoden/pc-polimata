"""FPS e frametime a partir do PresentMon (Windows, opcional).

O PC Polimata não injeta nada em jogos. Para FPS real usamos o PresentMon
(ferramenta open source da Intel, baseada em ETW), que grava um CSV com uma
linha por frame apresentado. Aqui só (1) localizamos o executável, (2) o
rodamos por alguns segundos para um processo e (3) lemos o CSV.

Colunas aceitas para o intervalo entre frames (ms):
- PresentMon 1.x: ``MsBetweenPresents``
- PresentMon 2.x: ``MsBetweenPresents`` ou ``FrameTime``
"""

from __future__ import annotations

import csv
import io
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

FRAMETIME_COLUMNS = ("MsBetweenPresents", "FrameTime", "msBetweenPresents")
PROCESS_COLUMNS = ("Application", "ProcessName")
EXECUTABLE_NAMES = ("PresentMon.exe", "PresentMon64.exe", "PresentMon-x64.exe", "PresentMon")


@dataclass
class FrameStats:
    frames: int
    avg_fps: float
    low_1_percent_fps: float
    avg_frametime_ms: float
    p99_frametime_ms: float
    max_frametime_ms: float
    process: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _pick(header: Sequence[str], candidates: Iterable[str]) -> str | None:
    return next((c for c in candidates if c in header), None)


def frame_stats(frametimes_ms: list[float], process: str | None = None) -> FrameStats:
    """Médias e 1% low. "1% low" = FPS médio do 1% de frames mais lentos (definição usual em reviews)."""
    times = [t for t in frametimes_ms if t > 0]
    if not times:
        raise ValueError("no frames")
    ordered = sorted(times, reverse=True)
    worst = ordered[: max(1, len(ordered) // 100)]
    avg = sum(times) / len(times)
    p99_index = min(len(ordered) - 1, max(0, int(round(len(ordered) * 0.01)) - 1))
    return FrameStats(
        frames=len(times),
        avg_fps=round(1000 / avg, 1),
        low_1_percent_fps=round(1000 / (sum(worst) / len(worst)), 1),
        avg_frametime_ms=round(avg, 2),
        p99_frametime_ms=round(ordered[p99_index], 2),
        max_frametime_ms=round(ordered[0], 2),
        process=process,
    )


def parse_csv(text: str, process: str | None = None) -> FrameStats:
    """Lê o CSV do PresentMon. Com `process`, filtra pelo nome do executável (sem diferenciar caixa)."""
    reader = csv.DictReader(io.StringIO(text))
    header: Sequence[str] = reader.fieldnames or []
    column = _pick(header, FRAMETIME_COLUMNS)
    if column is None:
        raise ValueError(f"no frametime column (expected one of {FRAMETIME_COLUMNS})")
    proc_col = _pick(header, PROCESS_COLUMNS)
    times: list[float] = []
    seen: dict[str, int] = {}
    for row in reader:
        name = (row.get(proc_col) or "") if proc_col else ""
        if process and proc_col and name.lower() != process.lower():
            continue
        try:
            value = float(row.get(column) or "")
        except ValueError:
            continue  # "NA" e linhas truncadas
        times.append(value)
        seen[name] = seen.get(name, 0) + 1
    chosen = process or (max(seen, key=lambda k: seen[k]) if seen and any(seen) else None)
    return frame_stats(times, chosen or None)


def find_presentmon(which: Callable[[str], str | None] = shutil.which, env: dict[str, str] | None = None) -> str | None:
    """Procura em $PRESENTMON_PATH, no PATH e na pasta padrão do instalador da Intel."""
    env = dict(os.environ) if env is None else env
    explicit = env.get("PRESENTMON_PATH")
    if explicit and Path(explicit).is_file():
        return explicit
    for name in EXECUTABLE_NAMES:
        found = which(name)
        if found:
            return found
    program_files = env.get("ProgramFiles")
    if program_files:
        for candidate in sorted(Path(program_files, "Intel", "PresentMon").glob("**/PresentMon*.exe")):
            return str(candidate)
    return None


def capture_command(exe: str, process: str, seconds: int, output: Path) -> list[str]:
    """Linha de comando do PresentMon 2.x (a 1.x usa os mesmos nomes com um hífen só)."""
    return [
        exe,
        "--process_name",
        process,
        "--output_file",
        str(output),
        "--timed",
        str(seconds),
        "--terminate_after_timed",
        "--stop_existing_session",
    ]


def capture(
    process: str,
    seconds: int = 10,
    exe: str | None = None,
    runner: Callable[..., Any] = subprocess.run,
) -> FrameStats:
    """Roda o PresentMon por `seconds` no processo e devolve as estatísticas. Requer admin no Windows."""
    exe = exe or find_presentmon()
    if not exe:
        raise FileNotFoundError("PresentMon not found (see docs/OVERLAY.md)")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "frames.csv"
        runner(
            capture_command(exe, process, seconds, out),
            check=True,
            timeout=seconds + 30,
            capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return parse_csv(out.read_text(encoding="utf-8", errors="replace"), process)


def live_command(exe: str, process: str, output: Path) -> list[str]:
    """Captura contínua (sem --timed) para acompanhar ao vivo com `fpslog.FrameLogTail`."""
    cmd = capture_command(exe, process, 0, output)
    return cmd[:5] + ["--stop_existing_session"]
