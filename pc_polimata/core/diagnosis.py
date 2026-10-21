"""Diagnóstico do sistema: regras determinísticas + LLM opcional.

As regras funcionam offline e são a base sempre exibida. Se houver chave
de API, o relatório (sem hostname) é enviado a um endpoint compatível com
OpenAI (`/chat/completions`) para uma análise em linguagem natural. Qualquer
falha do LLM cai de volta nas regras, com o erro informado.
"""

from __future__ import annotations

import copy
import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

SEVERITY_ORDER = {"crítico": 0, "atenção": 1, "info": 2}
Transport = Callable[[str, dict, dict, float], dict]


@dataclass
class Finding:
    severity: str  # crítico | atenção | info
    title: str
    detail: str


@dataclass
class Diagnosis:
    findings: list[Finding]
    score: int  # 0-100
    llm_analysis: str | None = None
    llm_error: str | None = None
    source: str = "regras"
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _rules_temperature(report: dict) -> list[Finding]:
    out = []
    sensors = report.get("sensors") or {}
    stress = report.get("stress_test") or {}
    temps = {"CPU": [sensors.get("cpu_temp_c"), stress.get("max_temp_c")], "GPU": [sensors.get("gpu_temp_c")]}
    temps["GPU"] += [g.get("temperature_c") for g in report.get("system", {}).get("gpus", [])]
    for comp, values in temps.items():
        values = [v for v in values if v is not None]
        if not values:
            continue
        t = max(values)
        if t >= 90:
            out.append(
                Finding(
                    "crítico",
                    f"{comp} muito quente ({t:.0f} °C)",
                    "Verifique ventilação, poeira e pasta térmica; há risco de throttling.",
                )
            )
        elif t >= 80:
            out.append(
                Finding(
                    "atenção",
                    f"{comp} quente ({t:.0f} °C)",
                    "Temperatura alta sob carga; melhore o fluxo de ar do gabinete.",
                )
            )
    return out


def _rules_memory(report: dict) -> list[Finding]:
    mem = report.get("system", {}).get("memory", {})
    out = []
    used, total = mem.get("used_percent"), mem.get("total_gb")
    if used is not None and used >= 90:
        out.append(
            Finding(
                "crítico",
                f"RAM quase esgotada ({used:.0f}%)",
                "Feche programas ou considere mais memória; o sistema pode usar swap e travar.",
            )
        )
    elif used is not None and used >= 80:
        out.append(Finding("atenção", f"Uso de RAM alto ({used:.0f}%)", "Monitore programas em segundo plano."))
    if total is not None and total < 8:
        out.append(
            Finding(
                "atenção",
                f"Pouca RAM instalada ({total} GB)",
                "8 GB é o mínimo confortável hoje; 16 GB para jogos e desenvolvimento.",
            )
        )
    return out


def _rules_disks(report: dict) -> list[Finding]:
    out = []
    for d in report.get("system", {}).get("disks", []):
        used = d.get("used_percent", 0)
        if used >= 95:
            out.append(
                Finding(
                    "crítico",
                    f"Disco {d['mountpoint']} cheio ({used:.0f}%)",
                    "Libere espaço: pouco espaço livre degrada desempenho e atualizações.",
                )
            )
        elif used >= 85:
            out.append(
                Finding(
                    "atenção",
                    f"Disco {d['mountpoint']} quase cheio ({used:.0f}%)",
                    "Considere limpar arquivos temporários ou mover dados.",
                )
            )
    for h in report.get("disk_health", []):
        if h.get("status") == "FALHA":
            out.append(Finding("crítico", f"SMART reprovado em {h['device']}", "Faça backup imediatamente."))
        elif h.get("status") == "ATENÇÃO":
            out.append(
                Finding(
                    "atenção",
                    f"SMART com alertas em {h['device']}",
                    "Setores realocados ou desgaste alto: planeje a troca e mantenha backup.",
                )
            )
    return out


def _rules_bottleneck(report: dict) -> list[Finding]:
    verdict = (report.get("bottleneck") or {}).get("verdict")
    if verdict == "CPU":
        return [Finding("info", "Gargalo na CPU", "A GPU está ociosa; um upgrade de CPU traria mais ganho.")]
    if verdict == "GPU":
        return [
            Finding(
                "info",
                "GPU é o limitante",
                "Normal em jogos; reduza a resolução/qualidade ou considere upgrade de GPU.",
            )
        ]
    return []


def _rules_network(report: dict) -> list[Finding]:
    out = []
    for r in report.get("network_latency") or []:
        if r.get("avg_ms") is None:
            out.append(Finding("atenção", f"Sem conexão com {r['host']}", "Verifique firewall/conexão."))
        elif r["avg_ms"] > 100:
            out.append(
                Finding(
                    "atenção",
                    f"Latência alta para {r['host']} ({r['avg_ms']} ms)",
                    "Prefira cabo a Wi-Fi e verifique downloads em segundo plano.",
                )
            )
    return out


RULES = (_rules_temperature, _rules_memory, _rules_disks, _rules_bottleneck, _rules_network)


def rule_based(report: dict) -> Diagnosis:
    findings = [f for rule in RULES for f in rule(report)]
    findings.sort(key=lambda f: SEVERITY_ORDER[f.severity])
    penalty = sum({"crítico": 25, "atenção": 10, "info": 0}[f.severity] for f in findings)
    if not findings:
        findings = [Finding("info", "Nenhum problema detectado", "Os indicadores estão dentro do esperado.")]
    return Diagnosis(findings, max(0, 100 - penalty))


def redact(report: dict) -> dict:
    """Remove dados pessoais antes de enviar a um serviço externo."""
    clean = copy.deepcopy(report)
    clean.get("system", {}).get("os", {}).pop("hostname", None)
    return clean


SYSTEM_PROMPT = (
    "Você é um técnico de hardware experiente. Analise o relatório JSON de um PC e responda em "
    "{lang}, em até 10 tópicos curtos: saúde geral, problemas, gargalos e upgrades com melhor "
    "custo-benefício. Não invente dados que não estão no relatório."
)


def _urllib_transport(url: str, headers: dict, payload: dict, timeout: float) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def llm_analysis(
    report: dict,
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o-mini",
    language: str = "pt",
    timeout: float = 60.0,
    transport: Transport = _urllib_transport,
) -> str:
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT.format(lang="português" if language == "pt" else "English")},
            {"role": "user", "content": json.dumps(redact(report), ensure_ascii=False, default=str)[:30_000]},
        ],
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = transport(base_url.rstrip("/") + "/chat/completions", headers, payload, timeout)
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("resposta inesperada do LLM") from exc


def diagnose(report: dict, api_key: str | None = None, **llm_kwargs: Any) -> Diagnosis:
    result = rule_based(report)
    if not api_key:
        return result
    try:
        result.llm_analysis = llm_analysis(report, api_key, **llm_kwargs)
        result.source = "regras + LLM"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        result.llm_error = str(exc)
    return result
