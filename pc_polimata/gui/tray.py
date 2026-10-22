"""Ícone na bandeja do sistema (pystray + Pillow, opcionais).

Sem as dependências, sem display ou se o backend do SO falhar, `TrayIcon.start`
devolve False e o app segue normalmente. Os cliques do pystray chegam em outra
thread; por isso só enfileiramos ações e a janela as executa via `after()`.
"""

from __future__ import annotations

import os
import queue
import sys
import threading
from collections.abc import Callable
from typing import Any

from pc_polimata.i18n import tr


def _x11_tray_manager_running() -> bool:
    """No X11, só há bandeja se algum programa for dono da seleção _NET_SYSTEM_TRAY_S<n>.

    Sem isso o backend xorg do pystray falha numa thread de fundo e trava ao sair
    (ex.: xvfb, gerenciadores de janela mínimos). Com PYSTRAY_BACKEND definido, confiamos no usuário.
    """
    if os.environ.get("PYSTRAY_BACKEND"):
        return True
    try:
        from Xlib import X, display

        d = display.Display()
        try:
            atom = d.intern_atom(f"_NET_SYSTEM_TRAY_S{d.get_default_screen()}")
            return bool(d.get_selection_owner(atom) != X.NONE)
        finally:
            d.close()
    except Exception:  # noqa: BLE001 - sem python-xlib/sem X: deixa o pystray decidir
        return True


def tray_supported() -> bool:
    if os.environ.get("PC_POLIMATA_NO_TRAY") or sys.platform == "darwin":  # macOS exige a thread principal
        return False
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        return False
    try:
        import PIL  # noqa: F401
        import pystray  # noqa: F401
    except Exception:  # noqa: BLE001 - ImportError ou backend sem suporte
        return False
    if sys.platform.startswith("linux") and os.environ.get("DISPLAY") and not _x11_tray_manager_running():
        return False
    return True


def make_image(size: int = 64) -> Any:
    """Ícone desenhado em código: placa verde com um "P" marrom (sem arquivo binário no repo)."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((2, 2, size - 2, size - 2), radius=size // 6, fill="#3f6b3a")
    s = size / 64
    d.rectangle((20 * s, 14 * s, 28 * s, 50 * s), fill="#c79a64")
    d.ellipse((20 * s, 14 * s, 46 * s, 36 * s), fill="#c79a64")
    d.ellipse((28 * s, 21 * s, 38 * s, 29 * s), fill="#3f6b3a")
    return img


class TrayIcon:
    def __init__(self, actions: dict[str, Callable[[], None]], is_monitoring: Callable[[], bool]) -> None:
        self.actions = actions
        self.is_monitoring = is_monitoring
        self.queue: queue.Queue[str] = queue.Queue()
        self.icon: Any = None

    def _post(self, name: str) -> Callable[..., None]:
        return lambda *_args: self.queue.put(name)

    def start(self) -> bool:
        if not tray_supported():
            return False
        try:
            import pystray

            menu = pystray.Menu(
                pystray.MenuItem(tr("Mostrar/ocultar janela"), self._post("toggle_window"), default=True),
                pystray.MenuItem(
                    tr("Monitoramento ativo"), self._post("toggle_monitoring"), checked=lambda _i: self.is_monitoring()
                ),
                pystray.MenuItem(tr("Overlay"), self._post("toggle_overlay")),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(tr("Sair"), self._post("quit")),
            )
            self.icon = pystray.Icon("pc-polimata", make_image(), "PC Polimata", menu)
            # Thread daemon própria: não segura o processo ao sair (run_detached do xorg usa thread comum).
            threading.Thread(target=self.icon.run, name="pc-polimata-tray", daemon=True).start()
        except Exception:  # noqa: BLE001 - ex.: sem StatusNotifier/AppIndicator no Linux
            self.icon = None
            return False
        return True

    def drain(self) -> None:
        """Executa na thread da GUI as ações clicadas no menu."""
        while True:
            try:
                name = self.queue.get_nowait()
            except queue.Empty:
                return
            action = self.actions.get(name)
            if action:
                action()

    def set_tooltip(self, text: str) -> None:
        if self.icon is not None:
            try:
                self.icon.title = text
            except Exception:  # noqa: BLE001
                pass

    def stop(self) -> None:
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:  # noqa: BLE001
                pass
            self.icon = None
