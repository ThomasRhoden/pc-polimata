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

Saída em `dist\PCPolimata\`: `PC Polimata.exe` (GUI, sem console) e `pc-polimata.exe` (com console, para a CLI:
`pc-polimata.exe --report -o r.html`). Para distribuir, compacte a pasta `dist\PCPolimata`.

Executável único (mais lento para iniciar): `$env:PC_POLIMATA_ONEFILE=1; pyinstaller packaging/pc_polimata.spec`
→ `dist\PC Polimata.exe` (sem console; sem argumentos abre a GUI). UPX fica desligado e módulos pesados
não usados são excluídos para abrir mais rápido. Sem console, logs vão para `%APPDATA%\PCPolimata\pc-polimata.log`.

**Automático:** ao enviar uma tag `v*`, o workflow `.github/workflows/release.yml` faz os dois builds em
`windows-latest`, roda `pc-polimata.exe --version` e `--report` como smoke test e anexa ao release
`pc-polimata-<tag>-windows-x64.zip` (pasta `PC Polimata`, principal), `pc-polimata-<tag>-windows-x64.exe`
(arquivo único) e o relatório do smoke test. O workflow também confere que os exes da GUI são "windowed".

Observações:
- O spec usa modo pasta (inicia mais rápido e gera menos falsos positivos de antivírus que `--onefile`).
- `packaging/launcher.py` chama `multiprocessing.freeze_support()`, obrigatório para o benchmark e o
  stress test funcionarem no executável.
- O executável não é assinado digitalmente; o SmartScreen pode exibir um aviso na primeira execução.
- Temperaturas exigem o LibreHardwareMonitor em execução (ver README).
