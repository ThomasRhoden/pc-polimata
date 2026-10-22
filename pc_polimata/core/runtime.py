"""Infraestrutura de execução: log em arquivo (exe sem console) e leitura de sensores em segundo plano."""

from __future__ import annotations

import contextlib
import logging
import os
import sys
import threading
from collections.abc import Callable, Iterator
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Generic, TypeVar

from pc_polimata.core.settings import config_dir

T = TypeVar("T")
LOG_NAME = "pc-polimata.log"


def ensure_std_streams() -> None:
    """Em exes `--windowed` o sys.stdout/stderr são None; troca por os.devnull para print() não quebrar."""
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))  # noqa: SIM115 - vive o processo todo


def setup_logging(directory: Path | None = None, level: int = logging.INFO) -> Path | None:
    """Envia o log do pacote `pc_polimata` para <config>/pc-polimata.log. Retorna o caminho (ou None)."""
    logger = logging.getLogger("pc_polimata")
    for h in logger.handlers:
        if isinstance(h, RotatingFileHandler):
            return Path(h.baseFilename)
    try:
        folder = directory or config_dir()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / LOG_NAME
        handler: logging.Handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    except OSError:
        logger.addHandler(logging.NullHandler())
        return None
    handler.setFormatter(logging.Formatter("%(asctime)s %(threadName)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level)
    return path


@contextlib.contextmanager
def com_initialized() -> Iterator[None]:
    """WMI em threads secundárias exige CoInitialize no Windows; no-op em outros sistemas."""
    pythoncom: Any = None
    if sys.platform.startswith("win"):
        try:
            import pythoncom  # type: ignore[import-not-found,no-redef]

            pythoncom.CoInitialize()
        except Exception:  # noqa: BLE001 - sem pywin32 o WMI simplesmente fica indisponível
            pythoncom = None
    try:
        yield
    finally:
        if pythoncom is not None:
            with contextlib.suppress(Exception):
                pythoncom.CoUninitialize()


class BackgroundPoller(Generic[T]):
    """Chama `read()` periodicamente numa thread daemon e guarda o último resultado.

    A thread nunca toca na UI: a GUI busca `take()` via `after()` na thread principal.
    """

    def __init__(
        self,
        read: Callable[[], T],
        interval_s: Callable[[], float] | float = 1.0,
        enabled: Callable[[], bool] = lambda: True,
        name: str = "pc-polimata-poller",
    ) -> None:
        self._read = read
        self._interval = interval_s if callable(interval_s) else (lambda: float(interval_s))
        self._enabled = enabled
        self._lock = threading.Lock()
        self._latest: T | None = None
        self._fresh = False
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name=name, daemon=True)
        self.errors = 0

    def start(self) -> BackgroundPoller[T]:
        self._thread.start()
        return self

    def stop(self, timeout: float | None = None) -> None:
        self._stop.set()
        if timeout is not None and self._thread.is_alive():
            self._thread.join(timeout)

    @property
    def running(self) -> bool:
        return self._thread.is_alive()

    def poll_once(self) -> None:
        try:
            value = self._read()
        except Exception:  # noqa: BLE001 - um sensor com falha não pode matar o laço
            self.errors += 1
            logging.getLogger("pc_polimata.poller").exception("falha ao ler sensores")
            return
        with self._lock:
            self._latest, self._fresh = value, True

    def take(self) -> T | None:
        """Devolve a leitura nova desde a última chamada, ou None."""
        with self._lock:
            if not self._fresh:
                return None
            self._fresh = False
            return self._latest

    def _run(self) -> None:
        with com_initialized():
            while not self._stop.is_set():
                if self._enabled():
                    self.poll_once()
                self._stop.wait(max(self._interval(), 0.05))
