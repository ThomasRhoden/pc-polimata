# Arquitetura

O PC Polimata separa **lógica de domínio** (`pc_polimata/core`), **interface gráfica**
(`pc_polimata/gui`) e **CLI** (`pc_polimata/cli.py`). O `core` não importa nada da GUI, então é
testado com pytest sem display e reutilizado pela CLI.

```mermaid
flowchart LR
    subgraph Entradas
        GUI["GUI customtkinter<br/>gui/app.py + gui/tabs/*"]
        CLI["CLI argparse<br/>cli.py"]
    end

    subgraph Core["pc_polimata/core (sem GUI)"]
        SI[system_info]
        SE[sensors]
        GPU[gpu]
        WT[windows_temps]
        BM[benchmark]
        MB[memory_bench]
        ST[stress]
        BN[bottleneck]
        NET[network]
        SM[smart]
        GA[games]
        DG[diagnosis]
        HI[history]
        RP[report]
        CFG[settings / secrets / units]
        PL[plugins]
        PM[presentmon]
        EX[exchange]
        LV[live]
    end

    subgraph Plugins["Plugins (isolados por PluginHost)"]
        BI[embutidos: uptime, battery]
        EP[(entry points<br/>pc_polimata.plugins)]
        LF[(pasta local<br/>config/plugins/*.py)]
    end

    subgraph Externos["Fontes externas (opcionais)"]
        PS[(psutil / py-cpuinfo)]
        NV[(NVML / GPUtil)]
        SYS[(sysfs amdgpu / rocm-smi)]
        WMI[(WMI: LibreHardwareMonitor,<br/>Win32_VideoController)]
        SC[(smartctl)]
        LLM[(API compatível OpenAI)]
        DB[(SQLite)]
        TIERS[(data/hardware_tiers.json)]
        PMX[(PresentMon.exe)]
        TRAY[(pystray + Pillow)]
    end

    GUI --> Core
    CLI --> Core
    SI --> PS & GPU
    SE --> PS & GPU & WT
    GPU --> NV & SYS & WMI
    WT --> WMI
    SM --> SC
    DG --> LLM
    HI --> DB
    GA --> TIERS
    BN --> SE
    ST --> SE
    PL --> BI & EP & LF
    PM --> PMX
    EX --> HI
    GUI -.bandeja.-> TRAY
    LV --> SE
```

## Princípios

- **Degradação graciosa**: todo backend opcional (NVML, WMI, rocm-smi, smartctl, numpy, LLM) é
  tentado dentro de `try` e, se falhar, o valor vira `None`/"n/d". O app nunca quebra por falta de hardware
  ou dependência.
- **Injeção de dependências para testes**: rede (`opener`, `connect`), relógio, `wmi`, `smartctl`
  (`runner`), transporte HTTP do LLM e raiz do sysfs são parâmetros, então os testes usam fakes e fixtures.
- **Concorrência**: carga de CPU usa `multiprocessing` com `spawn` (contorna o GIL e é seguro com threads).
  A GUI executa trabalho em threads e só atualiza widgets na thread principal via `after()`.
- **Dados do usuário** ficam fora do repositório, no diretório de config do SO: `settings.json`,
  `history.sqlite3` e `api_key` (permissão 0600).

## Fluxo de um benchmark na GUI

```mermaid
sequenceDiagram
    participant U as Usuário
    participant T as BenchmarkTab
    participant W as Thread worker
    participant C as core.benchmark
    participant A as PolimataApp
    participant H as HistoryStore (SQLite)
    U->>T: clica "Executar"
    T->>W: run_in_thread(work)
    W->>C: run_cpu_benchmark() (Pool spawn)
    C-->>W: CPUBenchmarkResult
    W-->>T: after(0, done)
    T->>A: record("cpu_benchmark", history_kind="cpu")
    A->>H: save_run()
    A->>T: atualiza aba Histórico
```
