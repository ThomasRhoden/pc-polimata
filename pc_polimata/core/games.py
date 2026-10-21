"""Estimativa de desempenho em jogos a partir de tiers de CPU/GPU.

ATENÇÃO: é uma ESTIMATIVA baseada numa tabela curada manualmente
(`data/hardware_tiers.json`), não uma medição. Serve para dar uma ideia
rápida do preset gráfico provável em 1080p.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from importlib import resources
from typing import Any

PRESETS = (
    (-99, "Abaixo do mínimo"),
    (-2, "Baixo"),
    (0, "Médio"),
    (1, "Alto"),
    (3, "Ultra"),
)


@dataclass
class GameEstimate:
    game: str
    preset: str
    margin: int | None
    limited_by: str | None  # "CPU", "GPU" ou None

    def to_dict(self) -> dict:
        return asdict(self)


def normalize(name: str) -> str:
    name = re.sub(r"\((r|tm)\)|®|™", " ", name.lower())
    name = re.sub(r"[-_/,@]", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def load_tiers() -> dict[str, Any]:
    text = resources.files("pc_polimata.data").joinpath("hardware_tiers.json").read_text(encoding="utf-8")
    return json.loads(text)


def find_tier(name: str | None, tiers: dict[str, list[str]]) -> int | None:
    """Tier do componente pelo padrão mais longo contido no nome (ex.: '4060 ti' vence '4060')."""
    if not name:
        return None
    target = f" {normalize(name)} "
    best: tuple[int, int] | None = None  # (tamanho do padrão, tier)
    for tier, patterns in tiers.items():
        for pattern in patterns:
            p = normalize(pattern)
            if re.search(rf"(?<![a-z0-9]){re.escape(p)}(?![a-z0-9])", target):
                if best is None or len(p) > best[0]:
                    best = (len(p), int(tier))
    return best[1] if best else None


def preset_for(margin: int) -> str:
    label = PRESETS[0][1]
    for threshold, name in PRESETS:
        if margin >= threshold:
            label = name
    return label


def estimate(cpu_tier: int | None, gpu_tier: int | None, games: list[dict]) -> list[GameEstimate]:
    out = []
    for g in games:
        if cpu_tier is None or gpu_tier is None:
            out.append(GameEstimate(g["name"], "Indeterminado", None, None))
            continue
        cpu_margin, gpu_margin = cpu_tier - g["cpu_tier"], gpu_tier - g["gpu_tier"]
        margin = min(cpu_margin, gpu_margin)
        limited = None if cpu_margin == gpu_margin else ("CPU" if cpu_margin < gpu_margin else "GPU")
        out.append(GameEstimate(g["name"], preset_for(margin), margin, limited))
    return out


def estimate_for_system(system: dict, gpu_override: str | None = None, cpu_override: str | None = None) -> dict:
    data = load_tiers()
    cpu_name = cpu_override or system.get("cpu", {}).get("name")
    gpus = system.get("gpus") or []
    gpu_name = gpu_override or (gpus[0]["name"] if gpus else None)
    cpu_tier = find_tier(cpu_name, data["cpu_tiers"])
    gpu_tier = find_tier(gpu_name, data["gpu_tiers"])
    return {
        "disclaimer": "Estimativa baseada em tiers aproximados, não é medição real.",
        "cpu": cpu_name,
        "cpu_tier": cpu_tier,
        "gpu": gpu_name,
        "gpu_tier": gpu_tier,
        "games": [e.to_dict() for e in estimate(cpu_tier, gpu_tier, data["games"])],
    }


def known_gpus() -> list[str]:
    data = load_tiers()
    return [name for tier in sorted(data["gpu_tiers"], key=int, reverse=True) for name in data["gpu_tiers"][tier]]
