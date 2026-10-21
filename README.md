# PC Polimata

![CI](https://github.com/ThomasRhoden/pc-polimata/actions/workflows/ci.yml/badge.svg)

Aplicativo desktop de **diagnóstico e benchmark de hardware**, escrito do zero em Python.
Inspirado na proposta de ferramentas como AIDA64, CPU-Z, GPU-Z e Cinebench — **nenhum código
dessas ferramentas foi copiado ou descompilado**; todos os algoritmos e scores são próprios.

![Aba Sistema](docs/screenshot_sistema.png)

## Funcionalidades

| Aba | O que faz |
|-----|-----------|
| **Sistema** | SO, CPU (modelo, núcleos, frequência), RAM, discos e GPU |
| **Sensores** | Uso de CPU (total e por núcleo), RAM, disco (MB/s) e GPU em tempo real; temperaturas quando disponíveis |
| **Benchmark** | Score single-core e multi-core (via `multiprocessing`) + leitura/escrita de disco em MB/s num arquivo temporário |
| **Stress test** | Carga de CPU em todos os núcleos com duração configurável, limite de temperatura e botão de parada segura |
| **Gargalo** | Amostra 30/45/60 s durante uma carga real e indica se CPU ou GPU é o recurso limitante |
| **Relatório** | Exporta informações + resultados da sessão para JSON ou HTML |

Também há uma CLI headless:

```bash
python -m pc_polimata --report                       # JSON no stdout
python -m pc_polimata --report -o relatorio.html     # HTML
python -m pc_polimata --benchmark --duration 3 -o r.json
```

![Aba Sensores](docs/screenshot_sensores.png)

## Arquitetura

```
pc_polimata/
├── core/               # lógica pura, sem dependência de GUI (testada com pytest)
│   ├── system_info.py  # coleta estática (psutil, py-cpuinfo)
│   ├── gpu.py          # NVML -> GPUtil -> nada (degradação graciosa)
│   ├── sensors.py      # SensorMonitor: snapshots com taxas de disco
│   ├── benchmark.py    # carga determinística (primos + float), score = iterações/s
│   ├── stress.py       # StressTest com processos, Event de parada e limites
│   ├── bottleneck.py   # heurística CPU x GPU sobre amostras
│   └── report.py       # JSON / HTML (com escape)
├── gui/                # customtkinter, tema escuro verde/marrom
│   ├── app.py          # abas; trabalho pesado em threads, UI via after()
│   └── theme.py
└── cli.py              # argparse; `python -m pc_polimata`
```

Decisões: o `core` não importa nada da GUI, então pode ser reutilizado por CLI, testes ou
outra interface. Trabalho de CPU usa `multiprocessing` (contorna o GIL). Dependências de GPU
são opcionais e qualquer falha resulta em "n/d", nunca em crash.

## Como executar

Requer Python 3.10+ (Windows principal, Linux suportado).

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m pc_polimata           # abre a GUI
```

Testes e lint:

```bash
pip install pytest ruff
ruff check . && pytest
```

No Linux, a GUI precisa do Tk do sistema (`sudo apt install python3-tk`).

## Limitações conhecidas

- **GPU**: uso, VRAM e temperatura apenas em placas **NVIDIA** (via NVML/GPUtil). AMD/Intel aparecem como "n/d".
- **Temperatura da CPU**: disponível no Linux via `psutil.sensors_temperatures`; no Windows o psutil não expõe
  temperaturas, então aparece "n/d" e o limite de temperatura do stress test fica inativo (a duração e o botão de parada continuam valendo).
- **Score de CPU** é próprio do PC Polimata e não é comparável com Cinebench/Geekbench.
- **Leitura de disco** pode ser inflada pelo cache do sistema operacional.
- **Gargalo** é uma heurística baseada em uso médio; não mede FPS nem frametime.

## Desenvolvido com auxílio de IA

Este projeto foi construído com **assistência de IA**. Uso IA como ferramenta para acelerar o
desenvolvimento (estrutura, rascunhos de código e testes), mas revisei, executei e validei o
resultado — e sou responsável pelas decisões de arquitetura e pelo código publicado.

## Roadmap

- [ ] Temperaturas no Windows via LibreHardwareMonitor/WMI
- [ ] Suporte a GPUs AMD (ROCm SMI) e Intel
- [ ] Gráficos históricos na aba Sensores
- [ ] Banco local de resultados para comparar execuções
- [ ] Benchmark de memória (largura de banda / latência)
- [ ] Empacotamento com PyInstaller (executável `.exe`)
- [ ] Assistente de IA que interpreta o relatório e sugere upgrades

---

## English

**PC Polimata** is a from-scratch Python desktop app for hardware diagnostics and benchmarking,
inspired by tools such as AIDA64, CPU-Z, GPU-Z and Cinebench (no code from them was copied or decompiled).

**Features:** system info (OS/CPU/RAM/disks/GPU), live sensors, single/multi-core CPU score using
`multiprocessing`, disk read/write MB/s, CPU stress test with duration + temperature limit and a safe
stop button, CPU-vs-GPU bottleneck heuristic (30–60 s sampling), and JSON/HTML report export.
A headless CLI is available: `python -m pc_polimata --report`.

**Architecture:** GUI-free `pc_polimata/core` (pytest-covered) + `customtkinter` GUI + `argparse` CLI.
Optional GPU backends (NVML, GPUtil) degrade gracefully.

**Run:** `pip install -r requirements.txt && python -m pc_polimata`. Tests: `ruff check . && pytest`.

**Limitations:** GPU telemetry is NVIDIA-only; CPU temperatures are unavailable on Windows through psutil;
scores are PC Polimata-specific.

**AI assistance:** built with AI assistance — I use AI to speed up development, and I reviewed,
ran and validated the code myself.

License: MIT.
