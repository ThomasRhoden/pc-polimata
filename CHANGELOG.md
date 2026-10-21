# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento [SemVer](https://semver.org/lang/pt-BR/).

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
