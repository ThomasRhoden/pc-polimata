"""Alertas por limite (temperatura, RAM, disco) com registro em arquivo de log.

`AlertMonitor.evaluate()` recebe um snapshot dos sensores e devolve apenas os
alertas NOVOS (transição de normal para alerta), evitando repetir o mesmo
aviso a cada segundo. Cada alerta novo também vai para `alerts.log` no
diretório de configuração do usuário.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

from pc_polimata.core.settings import config_dir
from pc_polimata.i18n import tr


@dataclass
class AlertThresholds:
    cpu_temp_c: float = 85.0
    gpu_temp_c: float = 85.0
    ram_percent: float = 90.0
    disk_percent: float = 95.0

    def validate(self) -> AlertThresholds:
        for name, value in asdict(self).items():
            if not 1 <= float(value) <= 150:
                raise ValueError(f"{name} must be between 1 and 150")
        return self


@dataclass(frozen=True)
class Alert:
    key: str
    message: str
    value: float
    threshold: float


def _checks(
    t: AlertThresholds,
    cpu_temp: float | None,
    gpu_temp: float | None,
    ram: float | None,
    disks: dict[str, float],
) -> list[tuple[str, float | None, float, str]]:
    items: list[tuple[str, float | None, float, str]] = [
        ("cpu_temp", cpu_temp, t.cpu_temp_c, tr("CPU a {value:.0f} °C (limite {threshold:.0f} °C)")),
        ("gpu_temp", gpu_temp, t.gpu_temp_c, tr("GPU a {value:.0f} °C (limite {threshold:.0f} °C)")),
        ("ram", ram, t.ram_percent, tr("RAM em {value:.0f}% (limite {threshold:.0f}%)")),
    ]
    for mount, used in disks.items():
        items.append(
            (f"disk:{mount}", used, t.disk_percent, tr("Disco {mount} em {value:.0f}% (limite {threshold:.0f}%)"))
        )
    return items


def default_logger(path: Path | None = None) -> logging.Logger:
    logger = logging.getLogger("pc_polimata.alerts")
    if not logger.handlers:
        path = path or config_dir() / "alerts.log"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            handler: logging.Handler = RotatingFileHandler(path, maxBytes=512_000, backupCount=2, encoding="utf-8")
        except OSError:
            handler = logging.NullHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


class AlertMonitor:
    def __init__(self, thresholds: AlertThresholds, logger: logging.Logger | None = None) -> None:
        self.thresholds = thresholds
        self.logger = logger
        self.active: set[str] = set()

    def evaluate(
        self,
        cpu_temp: float | None = None,
        gpu_temp: float | None = None,
        ram_percent: float | None = None,
        disks: dict[str, float] | None = None,
    ) -> list[Alert]:
        new: list[Alert] = []
        for key, value, limit, template in _checks(self.thresholds, cpu_temp, gpu_temp, ram_percent, disks or {}):
            if value is None or value < limit:
                self.active.discard(key)
                continue
            if key in self.active:
                continue
            self.active.add(key)
            mount = key.split(":", 1)[1] if key.startswith("disk:") else ""
            alert = Alert(key, template.format(value=value, threshold=limit, mount=mount), value, limit)
            new.append(alert)
            if self.logger:
                self.logger.warning(alert.message)
        return new
