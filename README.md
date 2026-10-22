# PC Polimata

[![Release](https://img.shields.io/github/v/release/ThomasRhoden/pc-polimata)](https://github.com/ThomasRhoden/pc-polimata/releases)
[![CI](https://github.com/ThomasRhoden/pc-polimata/actions/workflows/ci.yml/badge.svg)](https://github.com/ThomasRhoden/pc-polimata/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-3f6b3a)
![License](https://img.shields.io/badge/license-MIT-7a5a3a)
![Coverage](https://img.shields.io/badge/coverage-94%25-3f6b3a)
![mypy](https://img.shields.io/badge/mypy-strict%20(core)-7a5a3a)
![i18n](https://img.shields.io/badge/i18n-PT%20%7C%20EN-3f6b3a)

Aplicativo desktop de **diagnóstico, monitoramento e benchmark de hardware**, escrito do zero em Python.
Inspirado na proposta de ferramentas como AIDA64, CPU-Z, GPU-Z e Cinebench — **nenhum código dessas
ferramentas foi copiado ou descompilado**; todos os algoritmos e scores são próprios.

![Demonstração](docs/demo.gif)

## Funcionalidades

| Aba | O que faz |
|-----|-----------|
| **Sistema** | SO, CPU, RAM, discos e GPUs (NVIDIA, AMD, Intel), **drivers de vídeo** (versão/data, aviso se > 6 meses) e **saúde SMART** |
| **Sensores** | Uso de CPU (total e por núcleo), RAM, disco (MB/s) e GPU em tempo real, temperaturas e **gráfico dos últimos 60 s** |
| **Benchmark** | Score single/multi-core (`multiprocessing`), disco (leitura/escrita MB/s) e **memória** (largura de banda e latência) |
| **Stress test** | Carga em todos os núcleos com duração, limite de temperatura e botão de parada segura |
| **Gargalo** | Amostra 30/45/60 s durante uma carga real e indica se CPU ou GPU é o limitante |
| **Rede** | Latência TCP a 1.1.1.1 e 8.8.8.8 (sem admin), interfaces locais e teste de download com timeout |
| **Comparar** | Exporta as execuções deste PC em JSON e compara **dois PCs/execuções lado a lado** (vencedor por métrica) |
| **Histórico** | Toda execução de benchmark salva em **SQLite**; comparação com a anterior e gráfico de evolução |
| **Jogos** | **Estimativa** do preset provável em 19 jogos populares a partir de tiers de CPU/GPU (não é medição) |
| **Overlay & FPS** | **Overlay** sempre visível (CPU/GPU/RAM/temps; canto, tamanho e opacidade) com **FPS ao vivo**; **FPS / 1% low / frametime** via PresentMon (Windows) ou MangoHud (Linux) |
| **Diagnóstico IA** | Regras offline com nota de saúde 0–100 e dicas; análise opcional por **LLM** (API compatível com OpenAI) |
| **Relatório** | Exporta tudo para JSON, HTML (tema verde/marrom) ou **PDF** |
| **Configurações** | Idioma PT/EN, tema, °C/°F, intervalo, **limites de alerta**, verificação de atualização (opt-in), overlay, bandeja, **plugins** e LLM |
| **🔌 Plugins** | Abas e dados extras de plugins (entry points ou pasta local); exemplos: uptime e bateria — ver [docs/PLUGINS.md](docs/PLUGINS.md) |

**Bandeja do sistema** (opcional, `pip install "pc-polimata[tray]"`): mostrar/ocultar janela, tooltip com CPU e
temperatura, pausar o monitoramento, ligar o overlay e sair. Sem pystray/Pillow ou sem bandeja, o app segue normal.

**Alertas:** quando CPU/GPU, RAM ou disco passam do limite configurado, uma faixa não bloqueante aparece no topo
(sem repetir enquanto o valor continua alto), o evento vai para `alerts.log` e, se houver suporte, sai uma
**notificação nativa do SO** (toast no Windows, `notify-send` no Linux), limitada a 1 por alerta a cada 5 min.

![Alerta (leitura simulada)](docs/screenshot_alerta.png)

<table>
<tr><td><img src="docs/screenshot_overlay_fps.png" alt="Overlay e FPS"></td><td><img src="docs/screenshot_comparar.png" alt="Comparar"></td></tr>
<tr><td><img src="docs/screenshot_plugins.png" alt="Plugins em Configurações"></td><td><img src="docs/screenshot_uptime.png" alt="Aba de plugin"></td></tr>
<tr><td><img src="docs/screenshot_historico.png" alt="Histórico"></td><td><img src="docs/screenshot_jogos.png" alt="Jogos"></td></tr>
<tr><td><img src="docs/screenshot_sistema.png" alt="Sistema"></td><td><img src="docs/screenshot_rede.png" alt="Rede"></td></tr>
<tr><td><img src="docs/screenshot_diagnostico_ia.png" alt="Diagnóstico"></td><td><img src="docs/screenshot_configuracoes.png" alt="Configurações"></td></tr>
<tr><td><img src="docs/en_comparar.png" alt="Interface em inglês"></td><td><img src="docs/report_html.png" alt="Relatório HTML"></td></tr>
</table>

### Suporte de hardware

| Recurso | Windows | Linux |
|---------|---------|-------|
| Temperatura CPU | LibreHardwareMonitor/OpenHardwareMonitor em execução (WMI) | `psutil` (coretemp, k10temp...) |
| GPU NVIDIA (uso, VRAM, temp.) | NVML / GPUtil | NVML / GPUtil |
| GPU AMD | nome, VRAM e **uso** (WMI); temp. via LibreHardwareMonitor | sysfs `amdgpu` ou `rocm-smi` (uso, VRAM, temp.) |
| GPU Intel | nome, VRAM e **uso** (WMI) | — |
| Driver de vídeo | versão + data (WMI) | versão (NVML / `nvidia-smi`); data indisponível |
| SMART | `smartctl` (smartmontools) como administrador | `smartctl` como root |

### CLI (headless)

```bash
pc-polimata --report                                   # JSON no stdout
pc-polimata --report -o relatorio.html                 # HTML
pc-polimata --benchmark --memory --duration 3          # benchmarks (salvos no histórico)
pc-polimata --smart --games --diagnose -o r.json       # SMART, jogos e diagnóstico por regras
pc-polimata --diagnose --llm                           # + análise por LLM (requer chave)
pc-polimata --drivers --report -o relatorio.pdf        # PDF (requer reportlab)
pc-polimata --lang en --check-update                   # em inglês; verifica nova versão
pc-polimata --list-plugins                             # plugins encontrados
pc-polimata --plugins -o r.json                        # inclui dados dos plugins
pc-polimata --export-runs meu_pc.json                  # exporta as últimas execuções
pc-polimata --compare meu_pc.json outro_pc.json        # compara dois PCs (JSON)
pc-polimata --fps-csv captura.csv --process game.exe   # FPS/1% low (PresentMon ou MangoHud, detectado)
pc-polimata --fps-csv ~/mangohud_logs/jogo.csv --follow # FPS ao vivo enquanto o log é gravado
```

`python -m pc_polimata ...` funciona igual, sem instalar.

## Arquitetura

O núcleo (`pc_polimata/core`) não depende da GUI: é testado sem display e reutilizado pela CLI.
Diagramas completos em [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

```
pc_polimata/
├── core/                 # lógica pura, testada com pytest
│   ├── system_info.py    # coleta estática (psutil, py-cpuinfo)
│   ├── gpu.py            # NVML -> GPUtil -> sysfs AMD -> rocm-smi -> WMI
│   ├── windows_temps.py  # LibreHardwareMonitor/OpenHardwareMonitor via WMI
│   ├── sensors.py        # snapshots de uso/temperatura
│   ├── timeseries.py     # janela deslizante + coordenadas de gráfico
│   ├── benchmark.py      # CPU (primos + float, Pool spawn) e disco
│   ├── memory_bench.py   # largura de banda e latência da RAM
│   ├── stress.py         # stress test com limites e parada segura
│   ├── bottleneck.py     # heurística CPU x GPU
│   ├── network.py        # latência TCP, interfaces, throughput
│   ├── smart.py          # smartctl -j
│   ├── history.py        # SQLite + comparação de execuções
│   ├── games.py          # tiers de CPU/GPU -> preset estimado
│   ├── diagnosis.py      # regras + LLM opcional
│   ├── settings.py       # preferências em JSON no diretório de config do SO
│   ├── secrets.py        # chave de API (env var ou arquivo 0600)
│   ├── alerts.py         # limites + log rotativo
│   ├── drivers.py        # versão/idade do driver de vídeo
│   ├── updates.py        # nova versão via API do GitHub (opt-in)
│   ├── plugins.py        # descoberta (entry points + pasta) e PluginHost com isolamento de falhas
│   ├── presentmon.py     # FPS/1% low/frametime a partir do CSV do PresentMon
│   ├── fpslog.py         # MangoHud, detecção de formato e leitura ao vivo do CSV
│   ├── notify.py         # notificações nativas com limite de frequência
│   ├── exchange.py       # exportar/importar execuções e comparar máquinas
│   ├── live.py           # texto/geometria do overlay e tooltip da bandeja
│   └── report.py         # JSON / HTML / PDF
├── plugins/              # plugins de exemplo: uptime, battery
├── data/hardware_tiers.json
├── gui/                  # customtkinter: app.py, overlay.py, tray.py, widgets.py, tabs/
├── i18n.py               # PT (padrão) / EN
└── cli.py
```

Princípios: **degradação graciosa** (todo backend opcional vira "n/d" se faltar), **injeção de
dependências** para testar rede, WMI, sysfs, smartctl e LLM sem hardware real, e **multiprocessing**
para carga de CPU (contorna o GIL).

## Como executar

Requer Python 3.10+ (Windows principal, Linux suportado).

```bash
# como ferramenta
pipx install git+https://github.com/ThomasRhoden/pc-polimata.git
pc-polimata

# ou a partir do código
git clone https://github.com/ThomasRhoden/pc-polimata.git && cd pc-polimata
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m pc_polimata
```

- Linux: a GUI precisa do Tk do sistema (`sudo apt install python3-tk`).
- Temperaturas no Windows: abra o [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor)
  como administrador e `pip install wmi`.
- LLM: defina `PC_POLIMATA_API_KEY` (ou `OPENAI_API_KEY`) ou informe a chave na aba Configurações. Qualquer
  endpoint compatível com OpenAI funciona (ex.: Ollama em `http://localhost:11434/v1`).
- **Executável Windows pronto**: baixe `pc-polimata-<versão>-windows-x64.exe` na página de
  [releases](https://github.com/ThomasRhoden/pc-polimata/releases) (gerado e testado pelo GitHub Actions). Build manual: [docs/BUILD.md](docs/BUILD.md).

Testes e lint:

```bash
pip install -e ".[dev,pdf,memory,tray]"
ruff check .
mypy                       # modo strict em core, plugins e i18n
pytest --cov               # cobertura (núcleo + CLI): 94 %
xvfb-run -a pytest tests/test_gui_smoke.py   # smoke test da GUI (PT e EN) no Linux sem monitor
```

Qualidade atual (v0.5.0): **401 testes** passando (incluindo a checagem de tradução EN que varre o código),
**94 % de cobertura** no núcleo e na CLI e **mypy strict** sem erros no núcleo e nos plugins.

## Privacidade

Tudo roda localmente. Só há tráfego de rede quando você usa a aba Rede (conexões TCP e download de
teste da Cloudflare), o diagnóstico por LLM (o relatório, sem hostname, vai ao endpoint configurado) ou a
verificação de atualização (desligada por padrão; consulta a API pública do GitHub).
Configurações, histórico e chave ficam no diretório de configuração do usuário
(`%APPDATA%\PCPolimata` ou `~/.config/pc-polimata`).

## Limitações conhecidas

- **GPU**: telemetria completa em NVIDIA e AMD no Linux. No Windows, AMD/Intel têm uso e VRAM via WMI; com várias GPUs, a associação entre contador e placa é aproximada (o WMI não liga o LUID ao adaptador).
- **Data do driver** só é conhecida no Windows; no Linux o aviso de driver antigo não aparece.
- **Temperatura no Windows** depende do LibreHardwareMonitor aberto; sem ele aparece "n/d" (com uma dica) e o limite de temperatura do stress test fica inativo.
- **Scores** de CPU/memória são próprios do PC Polimata e não comparáveis a Cinebench/AIDA64. A latência de memória medida em Python inclui overhead do interpretador (é um teto).
- **Leitura de disco** pode ser inflada pelo cache do SO.
- **Gargalo** e **Jogos** são heurísticas/estimativas. FPS real vem do PresentMon (Windows, admin) ou do MangoHud (Linux); o FPS ao vivo tem o atraso de gravação do log (~1–2 s no MangoHud).
- **Notificações** dependem de um backend do SO (winotify/plyer no Windows, `notify-send` no Linux).
- **Overlay** é uma janela comum por cima das outras: funciona com jogos em janela/sem borda, **não** em tela cheia exclusiva. Detalhes em [docs/OVERLAY.md](docs/OVERLAY.md).
- **Bandeja**: no Linux exige um gerenciador de bandeja (X11) ou AppIndicator; não há bandeja no macOS.
- **Plugins** são isolados contra falhas, não contra código malicioso: rodam com as permissões do app.
- **Latência** é o tempo de `connect()` TCP, não ICMP; proxies/VPNs transparentes podem distorcer o valor.
- **SMART** exige smartmontools e privilégios de administrador/root.

## Desenvolvido com auxílio de IA

Este projeto foi construído com **assistência de IA**. Uso IA como ferramenta para acelerar o
desenvolvimento (estrutura, rascunhos de código e testes), mas revisei, executei e validei o
resultado — e sou responsável pelas decisões de arquitetura e pelo código publicado.

## Roadmap

Itens abertos nas [issues](https://github.com/ThomasRhoden/pc-polimata/issues); histórico no
[CHANGELOG](CHANGELOG.md). Contribuições: [CONTRIBUTING.md](CONTRIBUTING.md).

---

## English

**PC Polimata** is a from-scratch Python desktop app for hardware diagnostics, monitoring and benchmarking,
inspired by tools such as AIDA64, CPU-Z, GPU-Z and Cinebench (no code from them was copied or decompiled).

**Features:** system info with SMART disk health and graphics driver age; live sensors with 60 s charts; CPU (single/multi-core),
disk and memory benchmarks; stress test with temperature limit and safe stop; CPU-vs-GPU bottleneck
heuristic; network tab (TCP latency, interfaces, download test); SQLite benchmark history with run
comparison; game performance **estimates** from CPU/GPU tiers; health diagnosis with offline rules and an
optional LLM (any OpenAI-compatible API); configurable alerts (non-blocking banner + log file); opt-in update
check; JSON/HTML/PDF reports; fully translated PT/EN UI; **plugin system** (entry points + local folder,
failure-isolated, enable/disable in Settings, example uptime/battery plugins — [docs/PLUGINS.md](docs/PLUGINS.md));
optional **system tray icon**; always-on-top **overlay** with live CPU/GPU/RAM/temps and **FPS / 1% low /
frametime via PresentMon** on Windows or **MangoHud** on Linux, with **live FPS** in the overlay; native
desktop **notifications** for alerts (throttled) ([docs/OVERLAY.md](docs/OVERLAY.md)); **Compare** tab to export runs as JSON
and compare two machines side by side. Headless CLI included
(`pc-polimata --report`, `--benchmark`, `--memory`, `--smart`, `--games`, `--diagnose [--llm]`, `--plugins`,
`--export-runs`, `--compare A B`, `--fps-csv [--follow]`). CI on GitHub Actions (Ubuntu + Windows) and a
ready-to-run Windows `.exe` built and smoke-tested by the release workflow.

**Architecture:** GUI-free `pc_polimata/core` (pytest-covered, dependency-injected for hardware/network
fakes) + `customtkinter` GUI + `argparse` CLI. Every optional backend degrades gracefully to "n/a".
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

**Quality:** 401 tests (including an AST-based EN translation check), 94 % coverage on core + CLI, strict mypy on
the core and plugins.

**Run:** `pipx install git+https://github.com/ThomasRhoden/pc-polimata.git && pc-polimata`, or
`pip install -r requirements.txt && python -m pc_polimata`. Tests: `ruff check . && pytest`.
Windows .exe build: [docs/BUILD.md](docs/BUILD.md).

**Hardware support:** NVIDIA via NVML/GPUtil, AMD on Linux via sysfs/rocm-smi, any GPU's usage on Windows via WMI
performance counters;
Windows temperatures require LibreHardwareMonitor running; SMART requires smartctl with admin/root.

**Limitations:** scores are PC Polimata-specific; game estimates and bottleneck analysis are heuristics;
latency is TCP-connect time; the overlay is a normal topmost window (windowed/borderless games only, not
exclusive fullscreen); FPS capture needs PresentMon + admin on Windows; plugins are failure-isolated, not
security-sandboxed.

**AI assistance:** built with AI assistance — I use AI to speed up development, and I reviewed,
ran and validated the code myself.

License: MIT.
