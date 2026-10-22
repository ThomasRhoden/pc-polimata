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

from pc_polimata.i18n import N_, tr

SEVERITY_ORDER = {N_("crítico"): 0, N_("atenção"): 1, N_("info"): 2}
Transport = Callable[[str, dict[str, Any], dict[str, Any], float], dict[str, Any]]


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
    source: str = N_("regras")
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _rules_temperature(report: dict[str, Any]) -> list[Finding]:
    out = []
    sensors = report.get("sensors") or {}
    stress = report.get("stress_test") or {}
    temps = {"CPU": [sensors.get("cpu_temp_c"), stress.get("max_temp_c")], "GPU": [sensors.get("gpu_temp_c")]}
    temps["GPU"] += [g.get("temperature_c") for g in report.get("system", {}).get("gpus", [])]
    for comp, raw in temps.items():
        values = [float(v) for v in raw if v is not None]
        if not values:
            continue
        t = max(values)
        if t >= 90:
            out.append(
                Finding(
                    "crítico",
                    tr("{comp} muito quente ({t:.0f} °C)", comp=comp, t=t),
                    tr("Verifique ventilação, poeira e pasta térmica; há risco de throttling."),
                )
            )
        elif t >= 80:
            out.append(
                Finding(
                    "atenção",
                    tr("{comp} quente ({t:.0f} °C)", comp=comp, t=t),
                    tr("Temperatura alta sob carga; melhore o fluxo de ar do gabinete."),
                )
            )
    return out


def _rules_memory(report: dict[str, Any]) -> list[Finding]:
    mem = report.get("system", {}).get("memory", {})
    out = []
    used, total = mem.get("used_percent"), mem.get("total_gb")
    if used is not None and used >= 90:
        out.append(
            Finding(
                "crítico",
                tr("RAM quase esgotada ({used:.0f}%)", used=used),
                tr("Feche programas ou considere mais memória; o sistema pode usar swap e travar."),
            )
        )
    elif used is not None and used >= 80:
        out.append(
            Finding(
                "atenção", tr("Uso de RAM alto ({used:.0f}%)", used=used), tr("Monitore programas em segundo plano.")
            )
        )
    if total is not None and total < 8:
        out.append(
            Finding(
                "atenção",
                tr("Pouca RAM instalada ({total} GB)", total=total),
                tr("8 GB é o mínimo confortável hoje; 16 GB para jogos e desenvolvimento."),
            )
        )
    return out


def _rules_disks(report: dict[str, Any]) -> list[Finding]:
    out = []
    for d in report.get("system", {}).get("disks", []):
        used = d.get("used_percent", 0)
        if used >= 95:
            out.append(
                Finding(
                    "crítico",
                    tr("Disco {mount} cheio ({used:.0f}%)", mount=d["mountpoint"], used=used),
                    tr("Libere espaço: pouco espaço livre degrada desempenho e atualizações."),
                )
            )
        elif used >= 85:
            out.append(
                Finding(
                    "atenção",
                    tr("Disco {mount} quase cheio ({used:.0f}%)", mount=d["mountpoint"], used=used),
                    tr("Considere limpar arquivos temporários ou mover dados."),
                )
            )
    for h in report.get("disk_health", []):
        if h.get("status") == "FALHA":
            out.append(
                Finding(
                    "crítico", tr("SMART reprovado em {device}", device=h["device"]), tr("Faça backup imediatamente.")
                )
            )
        elif h.get("status") == "ATENÇÃO":
            out.append(
                Finding(
                    "atenção",
                    tr("SMART com alertas em {device}", device=h["device"]),
                    tr("Setores realocados ou desgaste alto: planeje a troca e mantenha backup."),
                )
            )
    return out


def _rules_bottleneck(report: dict[str, Any]) -> list[Finding]:
    verdict = (report.get("bottleneck") or {}).get("verdict")
    if verdict == "CPU":
        return [Finding("info", tr("Gargalo na CPU"), tr("A GPU está ociosa; um upgrade de CPU traria mais ganho."))]
    if verdict == "GPU":
        return [
            Finding(
                "info",
                tr("GPU é o limitante"),
                tr("Normal em jogos; reduza a resolução/qualidade ou considere upgrade de GPU."),
            )
        ]
    return []


def _rules_network(report: dict[str, Any]) -> list[Finding]:
    out = []
    for r in report.get("network_latency") or []:
        if r.get("avg_ms") is None:
            out.append(
                Finding("atenção", tr("Sem conexão com {host}", host=r["host"]), tr("Verifique firewall/conexão."))
            )
        elif r["avg_ms"] > 100:
            out.append(
                Finding(
                    "atenção",
                    tr("Latência alta para {host} ({ms} ms)", host=r["host"], ms=r["avg_ms"]),
                    tr("Prefira cabo a Wi-Fi e verifique downloads em segundo plano."),
                )
            )
    return out


RULES = (_rules_temperature, _rules_memory, _rules_disks, _rules_bottleneck, _rules_network)


def rule_based(report: dict[str, Any]) -> Diagnosis:
    findings = [f for rule in RULES for f in rule(report)]
    findings.sort(key=lambda f: SEVERITY_ORDER[f.severity])
    penalty = sum({"crítico": 25, "atenção": 10, "info": 0}[f.severity] for f in findings)
    if not findings:
        findings = [Finding("info", tr("Nenhum problema detectado"), tr("Os indicadores estão dentro do esperado."))]
    return Diagnosis(findings, max(0, 100 - penalty))


def redact(report: dict[str, Any]) -> dict[str, Any]:
    """Remove dados pessoais antes de enviar a um serviço externo."""
    clean = copy.deepcopy(report)
    clean.get("system", {}).get("os", {}).pop("hostname", None)
    return clean


SYSTEM_PROMPT = (  # instrução ao modelo (não é texto de interface); o idioma vai em {lang}
    "Você é um técnico de hardware experiente. Analise o relatório JSON de um PC e responda em "
    "{lang}, em até 10 tópicos curtos: saúde geral, problemas, gargalos e upgrades com melhor "
    "custo-benefício. Não invente dados que não estão no relatório."
)


def _urllib_transport(url: str, headers: dict[str, Any], payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data: dict[str, Any] = json.loads(resp.read().decode())
    return data


def llm_analysis(
    report: dict[str, Any],
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
        return str(data["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(tr("resposta inesperada do LLM")) from exc


def diagnose(report: dict[str, Any], api_key: str | None = None, **llm_kwargs: Any) -> Diagnosis:
    result = rule_based(report)
    if not api_key:
        return result
    try:
        result.llm_analysis = llm_analysis(report, api_key, **llm_kwargs)
        result.source = N_("regras + LLM")
    except (urllib.error.URLError, OSError, ValueError) as exc:
        result.llm_error = str(exc)
    return result
