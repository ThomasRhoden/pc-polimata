"""Internacionalização mínima (PT padrão, EN opcional).

O texto em português é a própria chave, no estilo gettext: código legível
e fallback automático para PT quando falta tradução.
"""

from __future__ import annotations

SUPPORTED = ("pt", "en")

EN: dict[str, str] = {
    "Sistema": "System",
    "Sensores": "Sensors",
    "Benchmark": "Benchmark",
    "Stress test": "Stress test",
    "Gargalo": "Bottleneck",
    "Rede": "Network",
    "Relatório": "Report",
    "Histórico": "History",
    "Diagnóstico IA": "AI diagnosis",
    "Jogos": "Games",
    "Configurações": "Settings",
    "SISTEMA OPERACIONAL": "OPERATING SYSTEM",
    "PROCESSADOR": "PROCESSOR",
    "MEMÓRIA": "MEMORY",
    "DISCOS": "DISKS",
    "Núcleos": "Cores",
    "físicos": "physical",
    "lógicos": "logical",
    "Frequência máx.": "Max frequency",
    "Total": "Total",
    "Em uso": "In use",
    "usado": "used",
    "Nenhuma GPU detectada.": "No GPU detected.",
    "Temperatura CPU": "CPU temperature",
    "Temperatura GPU": "GPU temperature",
    "Disco leitura": "Disk read",
    "escrita": "write",
    "Por núcleo": "Per core",
    "Histórico dos últimos 60 s": "Last 60 s history",
    "Executar benchmark CPU + disco": "Run CPU + disk benchmark",
    "Executar benchmark de memória": "Run memory benchmark",
    "Executando...": "Running...",
    "Score próprio do PC Polimata (não comparável ao Cinebench).": "PC Polimata's own score (not comparable to Cinebench).",
    "Duração (s):": "Duration (s):",
    "Limite temp. (°C):": "Temp. limit (°C):",
    "Iniciar": "Start",
    "PARAR": "STOP",
    "Configuração inválida": "Invalid settings",
    "Fim": "Finished",
    "Tempo": "Time",
    "Temp. máx.": "Max temp.",
    "Abra o jogo/aplicação que deseja analisar e inicie a amostragem.": "Open the game/app you want to analyze and start sampling.",
    "Analisar gargalo": "Analyze bottleneck",
    "Veredito": "Verdict",
    "amostras": "samples",
    "Medir latência": "Measure latency",
    "Teste de download": "Download test",
    "Interfaces locais": "Local interfaces",
    "falhas": "failures",
    "Exporta informações do sistema e os resultados desta sessão.": "Exports system information and this session's results.",
    "Exportar JSON": "Export JSON",
    "Exportar HTML": "Export HTML",
    "Salvo em": "Saved to",
    "Analisar": "Analyze",
    "Usar LLM (requer chave de API)": "Use LLM (requires API key)",
    "Estimativa de desempenho — não é medição real.": "Performance estimate — not a real measurement.",
    "Idioma": "Language",
    "Tema": "Theme",
    "Unidade de temperatura": "Temperature unit",
    "Intervalo de atualização (ms)": "Refresh interval (ms)",
    "Salvar": "Save",
    "Reinicie o app para aplicar idioma e tema.": "Restart the app to apply language and theme.",
    "Chave de API (opcional)": "API key (optional)",
    "Saúde dos discos (SMART)": "Disk health (SMART)",
    "Comparar execuções": "Compare runs",
    "Nenhuma execução salva ainda.": "No saved runs yet.",
}

_language = "pt"


def set_language(lang: str) -> None:
    global _language
    if lang not in SUPPORTED:
        raise ValueError(f"unsupported language: {lang}")
    _language = lang


def get_language() -> str:
    return _language


def tr(text: str) -> str:
    """Traduz `text` (em PT) para o idioma atual; sem tradução, retorna o original."""
    if _language == "en":
        return EN.get(text, text)
    return text
