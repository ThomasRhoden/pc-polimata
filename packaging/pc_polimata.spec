# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec do PC Polimata (Windows). Uso, na raiz do repositório:
#   pyinstaller packaging/pc_polimata.spec --clean
# Resultado: dist/PCPolimata/PCPolimata.exe (modo pasta, inicia mais rápido que --onefile).
from pathlib import Path

import customtkinter
from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH).parent

datas = collect_data_files("customtkinter")  # temas JSON e fontes do customtkinter
datas += [(str(p), "pc_polimata/data") for p in (ROOT / "pc_polimata" / "data").glob("*.[jc]s*")]

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT)],
    datas=datas,
    hiddenimports=["pynvml", "wmi", "cpuinfo"],
    excludes=["pytest", "ruff"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PCPolimata",
    console=False,
    icon=None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="PCPolimata")
