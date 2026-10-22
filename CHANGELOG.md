# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

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

[Não lançado]: https://github.com/ThomasRhoden/pc-polimata/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/ThomasRhoden/pc-polimata/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/ThomasRhoden/pc-polimata/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ThomasRhoden/pc-polimata/releases/tag/v0.1.0
