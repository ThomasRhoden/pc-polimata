# PC Polimata

Aplicativo desktop de **diagnóstico e benchmark de hardware**, escrito do zero em Python.
Inspirado na proposta de ferramentas como AIDA64, CPU-Z, GPU-Z e Cinebench — **nenhum código
dessas ferramentas foi copiado ou descompilado**; todos os algoritmos e scores são próprios.

![Aba Sistema](docs/screenshot_sistema.png)

## Funcionalidades

| Aba | O que faz |
|-----|-----------|
| **Sistema** | SO, CPU (modelo, núcleos, frequência), RAM, discos e GPUs (NVIDIA, AMD, Intel) |
| **Sensores** | Uso de CPU (total e por núcleo), RAM, disco (MB/s) e GPU em tempo real, temperaturas quando disponíveis e **gráfico dos últimos 60 s** |
| **Benchmark** | Score single-core e multi-core (via `multiprocessing`) + leitura/escrita de disco em MB/s num arquivo temporário |
| **Stress test** | Carga de CPU em todos os núcleos com duração configurável, limite de temperatura e botão de parada segura |
| **Gargalo** | Amostra 30/45/60 s durante uma carga real e indica se CPU ou GPU é o recurso limitante |
| **Rede** | Latência TCP para 1.1.1.1 e 8.8.8.8 (sem admin), interfaces locais e teste de download com timeout |
| **Relatório** | Exporta informações + resultados da sessão para JSON ou HTML |

### Suporte de hardware

| Recurso | Windows | Linux |
|---------|---------|-------|
| Temperatura CPU | LibreHardwareMonitor/OpenHardwareMonitor em execução (WMI) | `psutil` (coretemp, k10temp...) |
| GPU NVIDIA (uso, VRAM, temp.) | NVML / GPUtil | NVML / GPUtil |
| GPU AMD | nome + VRAM (WMI); temp. via LibreHardwareMonitor | sysfs `amdgpu` ou `rocm-smi` (uso, VRAM, temp.) |
| GPU Intel | nome (WMI) | — |

Também há uma CLI headless:

```bash
python -m pc_polimata --report                       # JSON no stdout
python -m pc_polimata --report -o relatorio.html     # HTML
python -m pc_polimata --benchmark --duration 3 -o r.json
```

![Aba Sensores](docs/screenshot_sensores.png)

![Aba Rede](docs/screenshot_rede.png)

## Arquitetura

```
pc_polimata/
├── core/                 # lógica pura, sem dependência de GUI (testada com pytest)
│   ├── system_info.py    # coleta estática (psutil, py-cpuinfo)
│   ├── gpu.py            # NVML -> GPUtil -> sysfs AMD -> rocm-smi -> WMI
│   ├── windows_temps.py  # LibreHardwareMonitor/OpenHardwareMonitor via WMI
│   ├── sensors.py        # SensorMonitor: snapshots com taxas de disco
│   ├── timeseries.py     # janela deslizante + conversão para coordenadas do gráfico
│   ├── benchmark.py      # carga determinística (primos + float), score = iterações/s
│   ├── stress.py         # StressTest com processos, Event de parada e limites
│   ├── bottleneck.py     # heurística CPU x GPU sobre amostras
│   ├── network.py        # latência TCP, interfaces, throughput (rede injetável)
│   ├── settings.py       # preferências em JSON no diretório de config do SO
│   ├── units.py          # °C / °F
│   └── report.py         # JSON / HTML (com escape)
├── gui/                  # customtkinter, tema escuro verde/marrom
│   ├── app.py            # janela + registro de abas
│   ├── widgets.py        # LineChart (Canvas), helpers de thread
│   └── tabs/             # uma aba por módulo
├── i18n.py               # PT (padrão) / EN
└── cli.py                # argparse; `python -m pc_polimata`
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
xvfb-run -a pytest tests/test_gui_smoke.py   # smoke test da GUI no Linux sem monitor
```

Temperaturas no Windows: instale e abra o [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor)
como administrador e `pip install wmi`. O PC Polimata lê os sensores que ele publica no WMI.

No Linux, a GUI precisa do Tk do sistema (`sudo apt install python3-tk`).

## Limitações conhecidas

- **GPU**: telemetria completa em NVIDIA (NVML/GPUtil) e AMD no Linux (sysfs/rocm-smi). No Windows, GPUs AMD/Intel mostram nome e VRAM; uso fica "n/d".
- **Temperatura no Windows** depende do LibreHardwareMonitor/OpenHardwareMonitor aberto; sem ele aparece "n/d" (com uma dica) e o limite de temperatura do stress test fica inativo.
- **Latência** é o tempo de `connect()` TCP, não ICMP; proxies/VPNs transparentes podem distorcer o valor.
- **Score de CPU** é próprio do PC Polimata e não é comparável com Cinebench/Geekbench.
- **Leitura de disco** pode ser inflada pelo cache do sistema operacional.
- **Gargalo** é uma heurística baseada em uso médio; não mede FPS nem frametime.

## Desenvolvido com auxílio de IA

Este projeto foi construído com **assistência de IA**. Uso IA como ferramenta para acelerar o
desenvolvimento (estrutura, rascunhos de código e testes), mas revisei, executei e validei o
resultado — e sou responsável pelas decisões de arquitetura e pelo código publicado.

## Roadmap

Itens abertos são acompanhados nas [issues](https://github.com/ThomasRhoden/pc-polimata/issues).
Histórico de versões no [CHANGELOG](CHANGELOG.md).

---

## English

**PC Polimata** is a from-scratch Python desktop app for hardware diagnostics and benchmarking,
inspired by tools such as AIDA64, CPU-Z, GPU-Z and Cinebench (no code from them was copied or decompiled).

**Features:** system info (OS/CPU/RAM/disks/GPU), live sensors, single/multi-core CPU score using
`multiprocessing`, disk read/write MB/s, CPU stress test with duration + temperature limit and a safe
stop button, CPU-vs-GPU bottleneck heuristic (30–60 s sampling), live 60 s charts, a network tab
(TCP latency, interfaces, download test) and JSON/HTML report export.
A headless CLI is available: `python -m pc_polimata --report`.

**Architecture:** GUI-free `pc_polimata/core` (pytest-covered) + `customtkinter` GUI + `argparse` CLI.
Optional GPU backends (NVML, GPUtil) degrade gracefully.

**Run:** `pip install -r requirements.txt && python -m pc_polimata`. Tests: `ruff check . && pytest`.

**Hardware support:** NVIDIA via NVML/GPUtil, AMD on Linux via sysfs/rocm-smi, any GPU name on Windows via WMI;
Windows temperatures require LibreHardwareMonitor running.

**Limitations:** latency is TCP-connect time;
scores are PC Polimata-specific.

**AI assistance:** built with AI assistance — I use AI to speed up development, and I reviewed,
ran and validated the code myself.

License: MIT.
