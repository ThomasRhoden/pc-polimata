"""Gera screenshots da GUI em docs/ (Linux: `xvfb-run -s "-screen 0 1180x720x24" python scripts/screenshot.py`).

Uso: python scripts/screenshot.py [Aba=segundos ...]   ex.: Sistema=2 Sensores=20
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("XDG_CONFIG_HOME", tempfile.mkdtemp())  # não usa as configs do usuário

from PIL import ImageGrab  # noqa: E402

from pc_polimata.gui.app import PolimataApp  # noqa: E402
from pc_polimata.i18n import tr  # noqa: E402

DEFAULT = ["Sistema=2", "Sensores=20", "Rede=2"]
W, H = 1180, 720


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
        prepare = getattr(app.tab_objects[name], "screenshot_prepare", None)
        if prepare:
            prepare()

        def snap() -> None:
            out = Path("docs") / f"screenshot_{name.lower().replace(' ', '_')}.png"
            ImageGrab.grab(bbox=(0, 0, W, H)).save(out)
            print(out)
            step()

        app.after(int(secs * 1000), snap)

    app.after(500, step)
    app.mainloop()


if __name__ == "__main__":
    main(sys.argv[1:] or DEFAULT)
