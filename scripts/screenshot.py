"""Gera screenshots da GUI em docs/ (Linux: `xvfb-run -s "-screen 0 1180x720x24" python scripts/screenshot.py`).

Uso: python scripts/screenshot.py [Aba=segundos ...]   ex.: Sistema=2 Sensores=20
"""

import os
import sys
import tempfile
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("XDG_CONFIG_HOME", tempfile.mkdtemp())  # não usa as configs do usuário

from PIL import ImageGrab  # noqa: E402

from pc_polimata.gui.app import PolimataApp  # noqa: E402
from pc_polimata.i18n import tr  # noqa: E402

DEFAULT = [
    "Sistema=2",
    "Sensores=20",
    "Rede=3",
    "Histórico=2",
    "Jogos=2",
    "Diagnóstico IA=3",
    "Configurações=1",
]


def _demo_games(tab) -> None:
    # A VM de captura não tem GPU; mostra um exemplo com hardware comum.
    tab.cpu.set("Ryzen 5 5600X")
    tab.gpu.set("RTX 3060")
    tab.refresh()


# Ações executadas antes de capturar cada aba (apenas para as imagens do README).
DEMO_ACTIONS = {
    "Rede": lambda tab: tab.run_latency(),
    "Histórico": lambda tab: tab.refresh(),
    "Jogos": _demo_games,
    "Diagnóstico IA": lambda tab: tab.run(),
}
W, H = 1180, 720


def slug(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return ascii_name.lower().replace(" ", "_")


def main(specs: list[str]) -> None:
    app = PolimataApp()
    app.geometry(f"{W}x{H}+0+0")
    queue = [(name, float(secs)) for name, secs in (s.split("=") for s in specs)]

    def step() -> None:
        if not queue:
            app.destroy()
            return
        name, secs = queue.pop(0)
        app.tabs.set(tr(name))
        if name in DEMO_ACTIONS:
            DEMO_ACTIONS[name](app.tab_objects[name])

        def snap() -> None:
            out = Path("docs") / f"screenshot_{slug(name)}.png"
            ImageGrab.grab(bbox=(0, 0, W, H)).save(out)
            print(out)
            step()

        app.after(int(secs * 1000), snap)

    app.after(500, step)
    app.mainloop()


if __name__ == "__main__":
    main(sys.argv[1:] or DEFAULT)
