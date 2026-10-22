# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

## [0.5.1] - 2026-10-22

### Corrigido
- **Janela de CMD no Windows**: o executável da GUI (pasta e arquivo único) agora é *windowed* (sem console); `nvidia-smi`, `rocm-smi`, `smartctl`, PowerShell e PresentMon rodam com `CREATE_NO_WINDOW`. Sem stdout/stderr (`None`), as saídas vão para `os.devnull` e o log para `pc-polimata.log` na pasta de configuração.
- **Lentidão da interface**: leitura de sensores (psutil/WMI/GPU) saiu da thread do Tk para uma thread de fundo (com `CoInitialize` para WMI); a UI só aplica a última leitura via `after()`. Sensores ausentes (sem GPU, sem LibreHardwareMonitor) são reconsultados a cada 30 s em vez de a cada leitura.
- Abas montadas sob demanda (só "Sistema" na abertura); informações estáticas do sistema em cache; tarefas em `run_in_thread` também inicializam COM.

### Alterado
- Release: asset principal `pc-polimata-<tag>-windows-x64.zip` (pasta com `PC Polimata.exe`, abre mais rápido) e arquivo único `pc-polimata-<tag>-windows-x64.exe`; UPX desligado e módulos pesados excluídos.

## [0.5.0] - 2026-10-22

### Adicionado
- **Notificações nativas** para alertas (#16): toast do Windows (`winotify`), `notify-send`/libnotify no Linux, `osascript` no macOS e `plyer` como alternativa; limite de 1 notificação por alerta a cada 5 min e 3 por minuto no total; opção em Configurações (mostra o backend detectado).
- **FPS no Linux via MangoHud** (#14): leitura dos logs CSV do MangoHud; `--fps-csv` detecta automaticamente PresentMon ou MangoHud.
- **FPS ao vivo no overlay** (#15): leitura incremental do CSV (PresentMon ou MangoHud, ou o mais novo de uma pasta), atualizada a cada 1 s com FPS/1% low/frametime dos últimos 5 s; PresentMon ao vivo no Windows; `--fps-csv ... --follow` na CLI.
- **CI no GitHub Actions** (#10): ruff, mypy e pytest + cobertura em Ubuntu e Windows (Python 3.10 e 3.12), smoke test da GUI sob xvfb no Linux.
- **Release automatizado**: ao criar uma tag `v*`, o workflow gera o `.exe` do Windows com PyInstaller (arquivo único e pasta), faz um smoke test (`--version` e `--report`) e anexa os arquivos ao release.

### Alterado
- O spec do PyInstaller gera também `pc-polimata.exe` com console para a CLI e aceita `PC_POLIMATA_ONEFILE=1` para um executável único.

## [0.4.0] - 2026-10-22

### Adicionado
- **Sistema de plugins** (#13): protocolo tipado `Plugin` (`name`, `version`, `collect()`, `create_tab()` opcional), descoberta por entry points (`pc_polimata.plugins`) e pela pasta local `<config>/plugins`, `PluginHost` que isola falhas (um plugin com erro não derruba o app), seção **Plugins** em Configurações para habilitar/desabilitar, plugins de exemplo **uptime** (com aba) e **battery** (carga e saúde via sysfs), `--plugins`/`--list-plugins` na CLI e `docs/PLUGINS.md`.
- **Ícone na bandeja** (#12) via `pystray` + Pillow (extra `[tray]`): mostrar/ocultar janela, tooltip com CPU/temperatura, pausar/retomar monitoramento, overlay e sair. Fechar a janela minimiza para a bandeja. Desativado automaticamente sem as dependências, sem display ou sem gerenciador de bandeja (X11).
- **Overlay** sempre visível e semitransparente com CPU/GPU/RAM/temperaturas (canto, tamanho e opacidade configuráveis; arrastável) e **FPS via PresentMon** no Windows: FPS médio, 1% low, frametime médio/p99/máximo; `--fps-csv` analisa um CSV existente (#11). Limitações em `docs/OVERLAY.md`.
- Aba **Comparar**: exporta as últimas execuções deste PC em JSON (formato versionado, sem hostname) e compara dois PCs/execuções lado a lado, com vencedor por métrica e empate abaixo de 2 %; `--export-runs` e `--compare A B` na CLI; arquivos de exemplo em `docs/examples/`.

### Alterado
- Janela padrão maior (1440×760) para caber as novas abas.
- Salvar em Configurações preserva campos que não estão no formulário.

### Qualidade
- 373 testes; cobertura de 93 % (núcleo + CLI); `mypy --strict` também em `pc_polimata/plugins`.

## [0.3.0] - 2026-10-21

### Adicionado
- Uso de GPU de **qualquer fabricante no Windows** via contadores WMI `GPUEngine` (soma do motor 3D por adaptador, como o Gerenciador de Tarefas) (#9).
- **Tradução EN completa**: toda string de interface, CLI, diagnóstico e relatório passa por `tr()`; teste que varre o código (AST) e falha se faltar chave EN, se sobrar tradução sem uso ou se os placeholders divergirem. CLI com `--lang`.
- **Alertas** configuráveis (temperatura de CPU/GPU, RAM %, disco %) com faixa não bloqueante na GUI, sem repetição enquanto o valor continua alto, registrados em `alerts.log` (rotativo).
- **Drivers de vídeo**: versão e data (WMI / `nvidia-smi`), com aviso para drivers com mais de ~6 meses; seção na aba Sistema e `--drivers` na CLI.
- **Verificação de atualização** do PC Polimata via API de releases do GitHub (opt-in nas Configurações, timeout de 5 s; `--check-update` na CLI).
- **Exportação em PDF** (reportlab, opcional) com instruções para imprimir o HTML quando ausente; **novo template HTML** escuro verde/marrom com cards de resumo, tabelas e estilo de impressão.
- GIF de demonstração e capturas novas (incluindo interface em inglês e faixa de alerta).

### Qualidade
- `mypy --strict` sem erros em `pc_polimata/core` e `i18n`; dependências de dev incluem mypy, pytest-cov e types-psutil.
- Cobertura de testes de 91 % (núcleo + CLI; a GUI é coberta por smoke test sob xvfb e excluída da medição).
- Conexões SQLite fechadas ao sair da GUI e nos testes.

## [0.2.0] - 2026-10-21

### Adicionado
- Aba **Histórico**: cada benchmark (CPU, disco, memória) é salvo em SQLite; comparação entre a última execução e a anterior e gráfico da evolução (#1).
- Aba **Diagnóstico IA**: regras offline (temperatura, RAM, disco cheio, SMART, gargalo, latência) com nota de saúde 0–100 e análise opcional por LLM via API compatível com OpenAI; o hostname é removido antes do envio (#2).
- **Benchmark de memória**: largura de banda (cópia de buffer) e latência (pointer chasing), com numpy quando disponível e fallback em Python puro (#3).
- **Saúde dos discos (SMART)** via `smartctl -j`, na aba Sistema e na CLI (#4).
- Aba **Jogos**: estimativa do preset provável em 19 jogos a partir de uma tabela local de tiers de CPU/GPU, com seleção manual de CPU/GPU, claramente rotulada como estimativa (#5).
- Aba **Configurações**: idioma PT/EN, acento do tema, unidade de temperatura, intervalo de atualização, endpoint/modelo do LLM e chave de API (#6).
- Empacotamento: spec do PyInstaller, `docs/BUILD.md` e instalação via `pipx` (comando `pc-polimata`) (#7).
- `docs/ARCHITECTURE.md` com diagramas mermaid e `CONTRIBUTING.md` (#8).
- CLI: `--memory`, `--smart`, `--games`, `--diagnose [--llm]`, `--no-history`, `--version`.

### Alterado
- O pool do benchmark de CPU usa o método `spawn` em todas as plataformas (evita deadlock de `fork` com threads da GUI).
- Gráficos aceitam eixo ajustável e legenda com espaçamento automático.

### Segurança
- A chave de API nunca vai para o `settings.json` nem para relatórios: vem de `PC_POLIMATA_API_KEY`/`OPENAI_API_KEY` ou de um arquivo `api_key` com permissão 0600 no diretório de configuração do usuário.

## [0.1.0] - 2026-10-21

Primeira versão pública.

### Adicionado
- Abas **Sistema**, **Sensores**, **Benchmark**, **Stress test**, **Gargalo**, **Rede** e **Relatório** (GUI customtkinter, tema escuro verde/marrom).
- Benchmark de CPU single/multi-core (multiprocessing) e de disco (leitura/escrita MB/s).
- Stress test com duração, limite de temperatura e parada segura.
- Análise heurística de gargalo CPU x GPU (30/45/60 s).
- Gráficos ao vivo (Canvas do tkinter) de CPU, RAM e GPU nos últimos 60 s.
- Aba **Rede**: latência por conexão TCP a 1.1.1.1 e 8.8.8.8 (sem admin), interfaces locais e teste de download com timeout.
- Temperaturas no **Windows** via LibreHardwareMonitor/OpenHardwareMonitor (WMI), com dica na GUI quando indisponível.
- GPUs **AMD** no Linux (sysfs amdgpu e `rocm-smi`) e detecção de GPUs Intel/AMD no Windows (`Win32_VideoController`).
- Configurações persistidas (idioma, acento, unidade de temperatura, intervalo) e i18n PT/EN no núcleo.
- CLI headless `python -m pc_polimata --report [--benchmark] [-o arquivo.json|.html]`.
- Exportação JSON/HTML, testes pytest, ruff, licença MIT.

[Não lançado]: https://github.com/ThomasRhoden/pc-polimata/compare/v0.5.0...HEAD
[0.5.1]: https://github.com/ThomasRhoden/pc-polimata/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/ThomasRhoden/pc-polimata/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/ThomasRhoden/pc-polimata/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/ThomasRhoden/pc-polimata/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/ThomasRhoden/pc-polimata/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ThomasRhoden/pc-polimata/releases/tag/v0.1.0
