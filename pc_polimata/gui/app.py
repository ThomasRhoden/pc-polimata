"""Janela principal do PC Polimata.

Cada aba vive em `gui/tabs/`. Trabalho pesado roda em threads (que usam
multiprocessing quando necessário); a UI só é tocada na thread principal.
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from pc_polimata.core import report
from pc_polimata.core.history import HistoryStore
from pc_polimata.core.settings import Settings, load_settings
from pc_polimata.core.system_info import get_system_info
from pc_polimata.gui import theme as t
from pc_polimata.gui.tabs.benchmark import BenchmarkTab
from pc_polimata.gui.tabs.bottleneck import BottleneckTab
from pc_polimata.gui.tabs.diagnosis import DiagnosisTab
from pc_polimata.gui.tabs.games import GamesTab
from pc_polimata.gui.tabs.history import HistoryTab
from pc_polimata.gui.tabs.network import NetworkTab
from pc_polimata.gui.tabs.report import ReportTab
from pc_polimata.gui.tabs.sensors import SensorsTab
from pc_polimata.gui.tabs.settings import SettingsTab
from pc_polimata.gui.tabs.stress import StressTab
from pc_polimata.gui.tabs.system import SystemTab
from pc_polimata.i18n import set_language, tr

TABS = (
    ("Sistema", SystemTab),
    ("Sensores", SensorsTab),
    ("Benchmark", BenchmarkTab),
    ("Stress test", StressTab),
    ("Gargalo", BottleneckTab),
    ("Rede", NetworkTab),
    ("Histórico", HistoryTab),
    ("Jogos", GamesTab),
    ("Diagnóstico IA", DiagnosisTab),
    ("Relatório", ReportTab),
    ("Configurações", SettingsTab),
)


class PolimataApp(ctk.CTk):
    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__()
        self.settings = settings or load_settings()
        set_language(self.settings.language)
        t.apply_accent(self.settings.accent)
        ctk.set_appearance_mode("dark")
        self.title("PC Polimata")
        self.geometry("1180x720")
        self.configure(fg_color=t.BG)
        self.results: dict[str, Any] = {}
        self.system = get_system_info()
        try:
            self.history: HistoryStore | None = HistoryStore()
        except Exception:  # noqa: BLE001 - sem histórico o resto do app continua funcionando
            self.history = None

        ctk.CTkLabel(self, text="PC Polimata", font=t.FONT_TITLE, text_color=t.GREEN_LIGHT).pack(
            anchor="w", padx=16, pady=(12, 0)
        )
        self.tabs = ctk.CTkTabview(
            self,
            fg_color=t.PANEL,
            segmented_button_selected_color=t.BROWN,
            segmented_button_selected_hover_color=t.BROWN_HOVER,
        )
        self.tabs.pack(fill="both", expand=True, padx=12, pady=12)
        self.tab_objects: dict[str, object] = {}
        for name, cls in TABS:
            label = tr(name)
            self.tabs.add(label)
            self.tab_objects[name] = cls(self.tabs.tab(label), self)

    def record(self, key: str, value: Any, history_kind: str | None = None) -> None:
        """Guarda um resultado da sessão para o relatório e, se pedido, no histórico SQLite."""
        self.results[key] = value
        if history_kind and self.history is not None:
            hardware = {"cpu": self.system["cpu"]["name"], "gpus": [g["name"] for g in self.system["gpus"]]}
            self.history.save_run(history_kind, value, hardware)
            history_tab = self.tab_objects.get("Histórico")
            if history_tab is not None:
                history_tab.refresh()

    def build_report(self) -> dict[str, Any]:
        sensors = getattr(self.tab_objects.get("Sensores"), "last", None)
        return report.build_report(self.system, sensors=sensors.to_dict() if sensors else None, **self.results)


def run_gui() -> None:
    PolimataApp().mainloop()
