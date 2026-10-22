# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec do PC Polimata (Windows). Uso, na raiz do repositório:
#   pyinstaller packaging/pc_polimata.spec --clean
# Resultado (modo pasta, inicia mais rápido que --onefile), em dist/PCPolimata/:
#   PCPolimata.exe   GUI (sem janela de console)
#   pc-polimata.exe  mesma aplicação com console, para a CLI (--report, --version...)
import os
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
    hiddenimports=["pynvml", "wmi", "cpuinfo", "pystray", "pc_polimata.plugins.uptime", "pc_polimata.plugins.battery"],
    excludes=["pytest", "ruff"],
)
pyz = PYZ(a.pure)

if os.environ.get("PC_POLIMATA_ONEFILE"):
    # Arquivo único dist/pc-polimata.exe (com console; sem argumentos abre a GUI). Mais lento para iniciar.
    EXE(pyz, a.scripts, a.binaries, a.datas, [], name="pc-polimata", console=True, icon=None)
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="PCPolimata",
        console=False,
        icon=None,
    )
    cli = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="pc-polimata",
        console=True,
        icon=None,
    )
    coll = COLLECT(exe, cli, a.binaries, a.datas, name="PCPolimata")
