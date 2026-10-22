"""Janela principal do PC Polimata.

Cada aba vive em `gui/tabs/`. Trabalho pesado roda em threads (que usam
multiprocessing quando necessário); a UI só é tocada na thread principal.
"""

from __future__ import annotations

import time
from typing import Any

import customtkinter as ctk
import psutil

from pc_polimata.core import fpslog, live, plugins, report, updates
from pc_polimata.core.alerts import AlertMonitor, default_logger
from pc_polimata.core.history import HistoryStore
from pc_polimata.core.notify import Notifier
from pc_polimata.core.sensors import SensorSnapshot
from pc_polimata.core.settings import Settings, load_settings
from pc_polimata.core.system_info import get_system_info
from pc_polimata.gui import theme as t
from pc_polimata.gui.banner import AlertBanner
from pc_polimata.gui.overlay import Overlay
from pc_polimata.gui.tabs.benchmark import BenchmarkTab
from pc_polimata.gui.tabs.bottleneck import BottleneckTab
from pc_polimata.gui.tabs.compare import CompareTab
from pc_polimata.gui.tabs.diagnosis import DiagnosisTab
from pc_polimata.gui.tabs.fps import FpsTab
from pc_polimata.gui.tabs.games import GamesTab
from pc_polimata.gui.tabs.history import HistoryTab
from pc_polimata.gui.tabs.network import NetworkTab
from pc_polimata.gui.tabs.report import ReportTab
from pc_polimata.gui.tabs.sensors import SensorsTab
from pc_polimata.gui.tabs.settings import SettingsTab
from pc_polimata.gui.tabs.stress import StressTab
from pc_polimata.gui.tabs.system import SystemTab
from pc_polimata.gui.tray import TrayIcon
from pc_polimata.gui.widgets import run_in_thread
from pc_polimata.i18n import N_, set_language, tr

TABS = (
    (N_("Sistema"), SystemTab),
    (N_("Sensores"), SensorsTab),
    (N_("Benchmark"), BenchmarkTab),
    (N_("Stress test"), StressTab),
    (N_("Gargalo"), BottleneckTab),
    (N_("Rede"), NetworkTab),
    (N_("Histórico"), HistoryTab),
    (N_("Comparar"), CompareTab),
    (N_("Jogos"), GamesTab),
    (N_("Overlay & FPS"), FpsTab),
    (N_("Diagnóstico IA"), DiagnosisTab),
    (N_("Relatório"), ReportTab),
    (N_("Configurações"), SettingsTab),
)


class PolimataApp(ctk.CTk):
    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__()
        self.settings = settings or load_settings()
        set_language(self.settings.language)
        t.apply_accent(self.settings.accent)
        ctk.set_appearance_mode("dark")
        self.title("PC Polimata")
        self.geometry("1440x760")
        self.configure(fg_color=t.BG)
        self.results: dict[str, Any] = {}
        self.system = get_system_info()
        try:
            self.history: HistoryStore | None = HistoryStore()
        except Exception:  # noqa: BLE001 - sem histórico o resto do app continua funcionando
            self.history = None

        self.alerts = AlertMonitor(self.settings.alert_thresholds(), default_logger())
        self.alert_log: list[str] = []
        self.notifier = Notifier.auto(self.settings.desktop_notifications)
        self.fps_tail: fpslog.FrameLogTail | fpslog.FolderTail | None = None
        self._last_disk_check = 0.0
        self.monitoring = True
        self.overlay: Overlay | None = None
        self.last_fps: str | None = None
        self.last_snapshot: SensorSnapshot | None = None
        self.plugins = plugins.PluginHost(plugins.discover(), self.settings.disabled_plugins)

        ctk.CTkLabel(self, text="PC Polimata", font=t.FONT_TITLE, text_color=t.GREEN_LIGHT).pack(
            anchor="w", padx=16, pady=(12, 0)
        )
        self.banner = AlertBanner(self)
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
        self._add_plugin_tabs()
        self.banner.attach_before(self.tabs)
        self.tray = TrayIcon(
            {
                "toggle_window": self.toggle_window,
                "toggle_monitoring": self.toggle_monitoring,
                "toggle_overlay": self.toggle_overlay,
                "quit": self.destroy,
            },
            lambda: self.monitoring,
        )
        self.tray_active = self.settings.tray_icon and self.tray.start()
        if self.tray_active:
            self.protocol("WM_DELETE_WINDOW", self.withdraw)  # fechar = minimizar para a bandeja
            self.after(200, self._poll_tray)
        if self.settings.check_updates:
            self.after(1500, self.check_updates)

    # ---------- plugins ----------
    def _add_plugin_tabs(self) -> None:
        for record in self.plugins.enabled():
            if not record.has_tab:
                continue
            label = f"🔌 {record.name}"
            self.tabs.add(label)
            error = self.plugins.create_tab(record, self.tabs.tab(label), self)
            if error:
                ctk.CTkLabel(
                    self.tabs.tab(label),
                    text=tr("O plugin falhou ao montar a aba: {error}", error=error),
                    text_color=t.DANGER,
                ).pack(padx=16, pady=16)

    # ---------- bandeja / overlay ----------
    def _poll_tray(self) -> None:
        self.tray.drain()
        self.after(200, self._poll_tray)

    def toggle_window(self) -> None:
        if self.state() == "withdrawn":
            self.deiconify()
            self.lift()
        else:
            self.withdraw()

    def toggle_monitoring(self) -> None:
        self.monitoring = not self.monitoring

    def toggle_overlay(self) -> None:
        if self.overlay is not None:
            self.overlay.destroy()
            self.overlay = None
            return
        self.overlay = Overlay(self)
        if self.last_snapshot is not None:
            self.overlay.update_snapshot(self.last_snapshot, self.last_fps)

    # ---------- FPS ao vivo ----------
    def start_fps_tail(self, tail: fpslog.FrameLogTail | fpslog.FolderTail) -> None:
        first = self.fps_tail is None
        self.fps_tail = tail
        if first:
            self.after(1000, self._poll_fps)

    def stop_fps_tail(self) -> None:
        self.fps_tail = None
        self.last_fps = None

    def _poll_fps(self) -> None:
        if self.fps_tail is None:
            return
        stats = self.fps_tail.poll()
        if stats is not None:
            self.last_fps = fpslog.overlay_text(stats)
            self.results["fps_live"] = {**stats.to_dict(), "format": self.fps_tail.kind}
            if self.overlay is not None and self.last_snapshot is not None:
                self.overlay.update_snapshot(self.last_snapshot, self.last_fps)
        listener = getattr(self.tab_objects.get("Overlay & FPS"), "on_live_stats", None)
        if listener:
            listener(stats)
        self.after(1000, self._poll_fps)

    # ---------- alertas ----------
    def on_snapshot(self, snap: SensorSnapshot) -> None:
        """Chamado pela aba Sensores a cada leitura; dispara alertas e atualiza overlay/bandeja."""
        self.last_snapshot = snap
        if self.overlay is not None:
            self.overlay.update_snapshot(snap, self.last_fps)
        if self.tray_active:
            self.tray.set_tooltip(live.tray_tooltip(snap, self.settings.temperature_unit, self.monitoring))
        disks: dict[str, float] = {}
        if time.monotonic() - self._last_disk_check > 60:  # uso de disco muda devagar
            self._last_disk_check = time.monotonic()
            for d in self.system["disks"]:
                try:
                    disks[d["mountpoint"]] = psutil.disk_usage(d["mountpoint"]).percent
                except OSError:
                    continue
        for alert in self.alerts.evaluate(snap.cpu_temp_c, snap.gpu_temp_c, snap.ram_percent, disks):
            self.alert_log.append(alert.message)
            self.banner.show(alert.message)
            self.notifier.notify(alert.key, tr("PC Polimata — alerta"), alert.message)

    def apply_thresholds(self) -> None:
        self.alerts.thresholds = self.settings.alert_thresholds()
        self.alerts.active.clear()

    # ---------- atualização ----------
    def check_updates(self, show_current: bool = False) -> None:
        def done(status: object) -> None:
            if not isinstance(status, updates.UpdateStatus):
                return
            if status.update_available:
                self.banner.show(
                    tr("Nova versão disponível: {latest} — {url}", latest=status.latest, url=status.url), color=t.GREEN
                )
            elif show_current:
                msg = (
                    tr("Não foi possível verificar atualizações: {error}", error=status.error)
                    if status.error
                    else tr("Você já está na versão mais recente ({current}).", current=status.current)
                )
                self.banner.show(msg, color=t.BROWN)

        run_in_thread(self, updates.check_for_update, done)

    def record(self, key: str, value: Any, history_kind: str | None = None) -> None:
        """Guarda um resultado da sessão para o relatório e, se pedido, no histórico SQLite."""
        self.results[key] = value
        if history_kind and self.history is not None:
            hardware = {"cpu": self.system["cpu"]["name"], "gpus": [g["name"] for g in self.system["gpus"]]}
            self.history.save_run(history_kind, value, hardware)
            history_tab = self.tab_objects.get("Histórico")
            if history_tab is not None:
                history_tab.refresh()

    def destroy(self) -> None:
        self.tray.stop()
        if self.history is not None:
            self.history.close()
        super().destroy()

    def build_report(self) -> dict[str, Any]:
        sensors = getattr(self.tab_objects.get("Sensores"), "last", None)
        return report.build_report(
            self.system,
            sensors=sensors.to_dict() if sensors else None,
            alerts=self.alert_log or None,
            plugins={n: r.to_dict() for n, r in self.plugins.collect_all().items()} or None,
            **self.results,
        )


def run_gui() -> None:
    PolimataApp().mainloop()
