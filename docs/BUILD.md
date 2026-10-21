# Build e instalação

## pipx (recomendado para uso como ferramenta)

```bash
pipx install git+https://github.com/ThomasRhoden/pc-polimata.git
pc-polimata                 # GUI
pc-polimata --report -o r.html
```

Extras opcionais: `pipx install "pc-polimata[gpu,windows] @ git+https://github.com/ThomasRhoden/pc-polimata.git"`
(`gpu` = nvidia-ml-py, `windows` = wmi; `memory` = numpy para o benchmark de memória).

No Linux, a GUI precisa do Tk do sistema: `sudo apt install python3-tk`.

## Executável Windows (.exe) com PyInstaller

Em um Windows com Python 3.10+:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[gpu,windows,memory]" pyinstaller
pyinstaller packaging/pc_polimata.spec --clean
```

Saída: `dist\PCPolimata\PCPolimata.exe`. Para distribuir, compacte a pasta `dist\PCPolimata`.

Observações:
- O spec usa modo pasta (inicia mais rápido e gera menos falsos positivos de antivírus que `--onefile`).
- `packaging/launcher.py` chama `multiprocessing.freeze_support()`, obrigatório para o benchmark e o
  stress test funcionarem no executável.
- O executável não é assinado digitalmente; o SmartScreen pode exibir um aviso na primeira execução.
- Temperaturas exigem o LibreHardwareMonitor em execução (ver README).
