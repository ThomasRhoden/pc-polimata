"""Gera screenshots da GUI (ex.: xvfb-run python scripts/screenshot.py)."""

from PIL import ImageGrab

from pc_polimata.gui.app import PolimataApp

app = PolimataApp()
app.geometry("980x640+0+0")


def grab(name, tab, nxt):
    app.tabs.set(tab)

    def snap():
        ImageGrab.grab(bbox=(0, 0, 980, 640)).save(f"docs/{name}.png")
        nxt()

    app.after(2500, snap)


grab("screenshot_sistema", "Sistema", lambda: grab("screenshot_sensores", "Sensores", app.destroy))
app.mainloop()
