"""Preferências do usuário persistidas em JSON no diretório de config do SO.

- Windows: %APPDATA%\\PCPolimata\\settings.json
- Linux/macOS: $XDG_CONFIG_HOME/pc-polimata/settings.json (ou ~/.config)
- Em qualquer SO, $PC_POLIMATA_CONFIG_DIR substitui o diretório (testes, uso portátil).
A chave de API nunca é gravada aqui: ela vem de variável de ambiente ou de
um arquivo separado com permissão restrita (ver `secrets`).
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import TYPE_CHECKING

from pc_polimata.core.units import TEMP_UNITS

if TYPE_CHECKING:
    from pc_polimata.core.alerts import AlertThresholds
    from pc_polimata.core.live import OverlayConfig

ACCENTS = ("floresta", "terra")
LANGUAGES = ("pt", "en")


def config_dir() -> Path:
    override = os.environ.get("PC_POLIMATA_CONFIG_DIR")  # testes, instalações portáteis
    if override:
        return Path(override)
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "PCPolimata"
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "pc-polimata"


@dataclass
class Settings:
    language: str = "pt"
    accent: str = "floresta"
    temperature_unit: str = "C"
    refresh_ms: int = 1000
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    check_updates: bool = False  # opt-in: consulta a API de releases do GitHub
    alert_cpu_temp_c: float = 85.0
    alert_gpu_temp_c: float = 85.0
    alert_ram_percent: float = 90.0
    alert_disk_percent: float = 95.0
    desktop_notifications: bool = True  # notificação nativa do SO para alertas, se houver backend
    tray_icon: bool = True  # só tem efeito com pystray + Pillow instalados
    overlay_corner: str = "top-right"
    overlay_opacity: float = 0.8
    overlay_size: str = "medium"
    disabled_plugins: list[str] = field(default_factory=list)

    def validate(self) -> Settings:
        if self.language not in LANGUAGES:
            raise ValueError(f"language must be one of {LANGUAGES}")
        if self.accent not in ACCENTS:
            raise ValueError(f"accent must be one of {ACCENTS}")
        if self.temperature_unit not in TEMP_UNITS:
            raise ValueError(f"temperature_unit must be one of {TEMP_UNITS}")
        if not 250 <= int(self.refresh_ms) <= 10_000:
            raise ValueError("refresh_ms must be between 250 and 10000")
        self.refresh_ms = int(self.refresh_ms)
        self.check_updates = bool(self.check_updates)
        self.tray_icon = bool(self.tray_icon)
        self.desktop_notifications = bool(self.desktop_notifications)
        self.overlay_opacity = float(self.overlay_opacity)
        self.overlay_config()  # valida o overlay
        if not isinstance(self.disabled_plugins, list) or not all(isinstance(n, str) for n in self.disabled_plugins):
            raise ValueError("disabled_plugins must be a list of names")
        self.disabled_plugins = sorted(set(self.disabled_plugins))
        self.alert_thresholds()  # valida os limites
        return self

    def overlay_config(self) -> OverlayConfig:
        from pc_polimata.core.live import OverlayConfig  # import tardio: live importa sensors

        return OverlayConfig(self.overlay_corner, float(self.overlay_opacity), self.overlay_size).validate()

    def alert_thresholds(self) -> AlertThresholds:
        from pc_polimata.core.alerts import AlertThresholds  # import tardio: alerts importa settings

        return AlertThresholds(
            float(self.alert_cpu_temp_c),
            float(self.alert_gpu_temp_c),
            float(self.alert_ram_percent),
            float(self.alert_disk_percent),
        ).validate()


def settings_path(directory: Path | None = None) -> Path:
    return (directory or config_dir()) / "settings.json"


def load_settings(directory: Path | None = None) -> Settings:
    """Carrega as configurações; arquivo ausente/corrompido ou valor inválido => padrões."""
    path = settings_path(directory)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        known = {f.name for f in fields(Settings)}
        return Settings(**{k: v for k, v in raw.items() if k in known}).validate()
    except (OSError, ValueError, TypeError):
        return Settings()


def save_settings(settings: Settings, directory: Path | None = None) -> Path:
    path = settings_path(directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(settings.validate()), indent=2), encoding="utf-8")
    return path
