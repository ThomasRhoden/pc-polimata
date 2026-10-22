# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec do PC Polimata (Windows). Uso, na raiz do repositório:
#   pyinstaller packaging/pc_polimata.spec --clean
# Modo pasta (padrão, inicia rápido), em dist/PCPolimata/:
#   PC Polimata.exe  GUI (sem janela de console)
#   pc-polimata.exe  mesma aplicação com console, para a CLI (--report, --version...)
# Com PC_POLIMATA_ONEFILE=1: arquivo único dist/PC Polimata.exe (sem console; mais lento para abrir,
# pois extrai tudo para uma pasta temporária a cada execução).
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH).parent

datas = collect_data_files("customtkinter")  # temas JSON e fontes do customtkinter
datas += [(str(p), "pc_polimata/data") for p in (ROOT / "pc_polimata" / "data").glob("*.[jc]s*")]

# Módulos pesados que o app não usa (encolhem o pacote e aceleram a extração do onefile).
EXCLUDES = [
    "pytest", "ruff", "mypy", "IPython", "jupyter", "notebook", "matplotlib", "numpy", "pandas", "scipy",
    "PyQt5", "PyQt6", "PySide2", "PySide6", "wx", "gi", "tkinter.test", "pydoc_data",
    "lib2to3", "test",
]

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT)],
    datas=datas,
    hiddenimports=["pynvml", "wmi", "pythoncom", "cpuinfo", "pystray", "pc_polimata.plugins.uptime", "pc_polimata.plugins.battery"],
    excludes=EXCLUDES,
)
pyz = PYZ(a.pure)

if os.environ.get("PC_POLIMATA_ONEFILE"):
    EXE(pyz, a.scripts, a.binaries, a.datas, [], name="PC Polimata", console=False, upx=False, icon=None)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="PC Polimata", console=False, upx=False, icon=None)
    cli = EXE(pyz, a.scripts, [], exclude_binaries=True, name="pc-polimata", console=True, upx=False, icon=None)
    coll = COLLECT(exe, cli, a.binaries, a.datas, upx=False, name="PCPolimata")
