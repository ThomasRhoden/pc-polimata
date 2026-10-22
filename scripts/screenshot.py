"""Gera screenshots da GUI em docs/ (Linux: `xvfb-run -s "-screen 0 1440x760x24" python scripts/screenshot.py`).

Uso: python scripts/screenshot.py [--lang en] [--prefix nome] [--gif] [Aba=segundos ...]
ex.: python scripts/screenshot.py Sistema=2 Sensores=20
"""

import os
import sys
import tempfile
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("XDG_CONFIG_HOME", tempfile.mkdtemp())  # não usa as configs do usuário

from PIL import ImageGrab  # noqa: E402

from pc_polimata.core.sensors import SensorSnapshot  # noqa: E402
from pc_polimata.core.settings import Settings  # noqa: E402
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


def _demo_compare(tab) -> None:
    # Arquivos de EXEMPLO (valores ilustrativos) em docs/examples/.
    tab.load("a", "docs/examples/runs_desktop_example.json")
    tab.load("b", "docs/examples/runs_notebook_example.json")


# Ações executadas antes de capturar cada aba (apenas para as imagens do README).
DEMO_ACTIONS = {
    "Rede": lambda tab: tab.run_latency(),
    "Histórico": lambda tab: tab.refresh(),
    "Jogos": _demo_games,
    "Diagnóstico IA": lambda tab: tab.run(),
    "Comparar": _demo_compare,
    "Overlay & FPS": lambda tab: tab.app.toggle_overlay(),
}


def _demo_alert(app: PolimataApp) -> None:
    # Leitura SIMULADA (a VM não tem sensor de temperatura) só para mostrar a faixa de alerta.
    app.on_snapshot(SensorSnapshot(0, 97, [97], 60, 0, 0, cpu_temp_c=91.0))


W, H = 1440, 760


def slug(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return ascii_name.strip().lower().replace(" & ", "_").replace(" ", "_")


def main(argv: list[str]) -> None:
    lang = argv[argv.index("--lang") + 1] if "--lang" in argv else "pt"
    prefix = argv[argv.index("--prefix") + 1] if "--prefix" in argv else "screenshot"
    make_gif = "--gif" in argv
    specs = [a for a in argv if "=" in a] or DEFAULT
    app = PolimataApp(Settings(language=lang))
    app.geometry(f"{W}x{H}+0+0")
    queue = [(name, float(secs)) for name, secs in (s.split("=") for s in specs)]
    frames: list[Path] = []

    def step() -> None:
        if not queue:
            app.destroy()
            return
        name, secs = queue.pop(0)
        if name == "Alerta":
            _demo_alert(app)
            name = "Sensores"
            target = "alerta"
        elif name == "Plugins":  # Configurações rolada até a seção de plugins
            name, target = "Configurações", "plugins"
            app.after(300, lambda: app.tab_objects[name].scroll._parent_canvas.yview_moveto(1.0))
        else:
            target = slug(name)
        if app.overlay is not None and name != "Overlay & FPS":
            app.toggle_overlay()
        app.tabs.set(name if name.startswith("🔌") else tr(name))
        if name in DEMO_ACTIONS and target != "alerta":
            DEMO_ACTIONS[name](app.tab_objects[name])

        def snap() -> None:
            out = Path("docs") / f"{prefix}_{target}.png"
            ImageGrab.grab(bbox=(0, 0, W, H)).save(out)
            frames.append(out)
            print(out)
            step()

        app.after(int(secs * 1000), snap)

    app.after(500, step)
    app.mainloop()
    if make_gif and frames:
        from PIL import Image

        images = [Image.open(f).convert("RGB").resize((W * 2 // 3, H * 2 // 3)) for f in frames]
        palette = [im.quantize(colors=128) for im in images]
        gif = Path("docs") / "demo.gif"
        palette[0].save(gif, save_all=True, append_images=palette[1:], duration=1800, loop=0, optimize=True)
        print(gif)


if __name__ == "__main__":
    main(sys.argv[1:])
