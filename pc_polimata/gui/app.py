"""Janela principal do PC Polimata.

Cada aba vive em `gui/tabs/`. Trabalho pesado roda em threads (que usam
multiprocessing quando necessário); a UI só é tocada na thread principal.
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from pc_polimata.core import report
from pc_polimata.core.settings import Settings, load_settings
from pc_polimata.core.system_info import get_system_info
from pc_polimata.gui import theme as t
from pc_polimata.gui.tabs.benchmark import BenchmarkTab
from pc_polimata.gui.tabs.bottleneck import BottleneckTab
from pc_polimata.gui.tabs.network import NetworkTab
from pc_polimata.gui.tabs.report import ReportTab
from pc_polimata.gui.tabs.sensors import SensorsTab
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
    ("Relatório", ReportTab),
)


class PolimataApp(ctk.CTk):
    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__()
        self.settings = settings or load_settings()
        set_language(self.settings.language)
        t.apply_accent(self.settings.accent)
        ctk.set_appearance_mode("dark")
        self.title("PC Polimata")
        self.geometry("1040x680")
        self.configure(fg_color=t.BG)
        self.results: dict[str, Any] = {}
        self.system = get_system_info()

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

    def record(self, key: str, value: Any) -> None:
        """Guarda um resultado da sessão para o relatório."""
        self.results[key] = value

    def build_report(self) -> dict[str, Any]:
        return report.build_report(self.system, **self.results)


def run_gui() -> None:
    PolimataApp().mainloop()
