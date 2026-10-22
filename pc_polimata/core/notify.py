"""Notificações nativas do SO para alertas (opcional).

Backends tentados em ordem:
- Windows: ``winotify`` (toast nativo) e depois ``plyer``;
- Linux: ``notify-send`` (libnotify) e depois ``plyer``;
- macOS: ``osascript``.
Sem backend, `Notifier.notify` só devolve False. Um `Throttle` evita
spam: no máximo uma notificação por chave a cada `per_key_s` segundos e
`max_per_minute` no total.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from collections import deque
from collections.abc import Callable
from typing import Any

APP_NAME = "PC Polimata"
Backend = Callable[[str, str], None]


class Throttle:
    def __init__(
        self, per_key_s: float = 300.0, max_per_minute: int = 3, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.per_key_s = per_key_s
        self.max_per_minute = max_per_minute
        self.clock = clock
        self._last: dict[str, float] = {}
        self._recent: deque[float] = deque()

    def allow(self, key: str) -> bool:
        now = self.clock()
        while self._recent and now - self._recent[0] >= 60:
            self._recent.popleft()
        last = self._last.get(key)
        if last is not None and now - last < self.per_key_s:
            return False
        if len(self._recent) >= self.max_per_minute:
            return False
        self._last[key] = now
        self._recent.append(now)
        return True


def _winotify_backend() -> Backend | None:
    try:
        from winotify import Notification  # type: ignore[import-not-found]
    except Exception:  # noqa: BLE001
        return None

    def send(title: str, message: str) -> None:
        Notification(app_id=APP_NAME, title=title, msg=message).show()

    return send


def _plyer_backend() -> Backend | None:
    try:
        from plyer import notification  # type: ignore[import-not-found]
    except Exception:  # noqa: BLE001
        return None

    def send(title: str, message: str) -> None:
        notification.notify(title=title, message=message, app_name=APP_NAME, timeout=8)

    return send


def _command_backend(cmd: list[str], runner: Callable[..., Any]) -> Backend:
    def send(title: str, message: str) -> None:
        runner([*cmd, title, message], check=False, timeout=5, capture_output=True)

    return send


def find_backend(
    platform: str = sys.platform,
    which: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., Any] = subprocess.run,
    loaders: tuple[Callable[[], Backend | None], ...] | None = None,
) -> tuple[str, Backend] | None:
    """(nome, função) do primeiro backend disponível, ou None."""
    candidates: list[tuple[str, Callable[[], Backend | None]]] = []
    if platform.startswith("win"):
        candidates.append(("winotify", _winotify_backend))
    elif platform.startswith("linux"):
        exe = which("notify-send")
        if exe:
            send = _command_backend([exe, "--app-name", APP_NAME, "--urgency", "critical"], runner)
            candidates.append(("notify-send", lambda: send))
    elif platform == "darwin" and which("osascript"):

        def mac(title: str, message: str) -> None:
            script = f"display notification {_applescript(message)} with title {_applescript(title)}"
            runner(["osascript", "-e", script], check=False, timeout=5, capture_output=True)

        candidates.append(("osascript", lambda: mac))
    candidates.append(("plyer", _plyer_backend))
    if loaders is not None:
        candidates = [(f"custom{i}", f) for i, f in enumerate(loaders)]
    for name, loader in candidates:
        backend = loader()
        if backend is not None:
            return name, backend
    return None


def _applescript(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


class Notifier:
    def __init__(
        self, backend: tuple[str, Backend] | None = None, throttle: Throttle | None = None, enabled: bool = True
    ) -> None:
        self.backend = backend
        self.throttle = throttle or Throttle()
        self.enabled = enabled
        self.last_error: str | None = None

    @classmethod
    def auto(cls, enabled: bool = True) -> Notifier:
        return cls(find_backend() if enabled else None, enabled=enabled)

    @property
    def available(self) -> bool:
        return self.backend is not None

    @property
    def backend_name(self) -> str | None:
        return self.backend[0] if self.backend else None

    def notify(self, key: str, title: str, message: str) -> bool:
        """True se a notificação foi enviada; nunca levanta exceção."""
        if not self.enabled or self.backend is None or not self.throttle.allow(key):
            return False
        try:
            self.backend[1](title, message)
        except Exception as exc:  # noqa: BLE001 - falha de notificação não pode afetar o app
            self.last_error = f"{type(exc).__name__}: {exc}"
            return False
        return True
