from __future__ import annotations

from dataclasses import asdict

import customtkinter as ctk

from pc_polimata.core import secrets
from pc_polimata.core.live import CORNERS, SIZES
from pc_polimata.core.settings import ACCENTS, LANGUAGES, Settings, save_settings
from pc_polimata.core.units import TEMP_UNITS
from pc_polimata.gui import theme as t
from pc_polimata.gui.widgets import button
from pc_polimata.i18n import tr

NUMERIC = {
    "refresh_ms": int,
    "alert_cpu_temp_c": float,
    "alert_gpu_temp_c": float,
    "alert_ram_percent": float,
    "alert_disk_percent": float,
    "overlay_opacity": float,
}
BOOLEAN = ("check_updates", "tray_icon")


class SettingsTab:
    def __init__(self, master: ctk.CTkFrame, app) -> None:
        self.app = app
        s = app.settings
        scroll = self.scroll = ctk.CTkScrollableFrame(master, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=4, pady=4)
        form = ctk.CTkFrame(scroll, fg_color="transparent")
        form.pack(anchor="w", padx=8, pady=8)
        self.fields: dict[str, ctk.CTkBaseClass] = {}

        def row(label: str, widget: ctk.CTkBaseClass, key: str) -> None:
            r = len(self.fields)
            ctk.CTkLabel(form, text=label, anchor="w", width=300).grid(row=r, column=0, sticky="w", pady=4)
            widget.grid(row=r, column=1, sticky="w", pady=4)
            self.fields[key] = widget

        def menu(values, current):
            m = ctk.CTkOptionMenu(form, values=list(values), fg_color=t.GREEN, button_color=t.GREEN_HOVER)
            m.set(current)
            return m

        def entry(value, width=320, **kw):
            e = ctk.CTkEntry(form, width=width, **kw)
            e.insert(0, str(value))
            return e

        row(tr("Idioma"), menu(LANGUAGES, s.language), "language")
        row(tr("Tema"), menu(ACCENTS, s.accent), "accent")
        row(tr("Unidade de temperatura"), menu(TEMP_UNITS, s.temperature_unit), "temperature_unit")
        row(tr("Intervalo de atualização (ms)"), entry(s.refresh_ms, 100), "refresh_ms")
        row(tr("Alerta: temperatura da CPU (°C)"), entry(s.alert_cpu_temp_c, 100), "alert_cpu_temp_c")
        row(tr("Alerta: temperatura da GPU (°C)"), entry(s.alert_gpu_temp_c, 100), "alert_gpu_temp_c")
        row(tr("Alerta: uso de RAM (%)"), entry(s.alert_ram_percent, 100), "alert_ram_percent")
        row(tr("Alerta: uso de disco (%)"), entry(s.alert_disk_percent, 100), "alert_disk_percent")
        updates_box = ctk.CTkCheckBox(form, text="", fg_color=t.GREEN, hover_color=t.GREEN_HOVER)
        if s.check_updates:
            updates_box.select()
        row(tr("Verificar novas versões ao iniciar (GitHub)"), updates_box, "check_updates")
        tray_box = ctk.CTkCheckBox(form, text="", fg_color=t.GREEN, hover_color=t.GREEN_HOVER)
        if s.tray_icon:
            tray_box.select()
        row(tr("Ícone na bandeja (requer pystray + Pillow; reinicie)"), tray_box, "tray_icon")
        row(tr("Overlay: canto"), menu(CORNERS, s.overlay_corner), "overlay_corner")
        row(tr("Overlay: tamanho"), menu(SIZES, s.overlay_size), "overlay_size")
        row(tr("Overlay: opacidade (0.2–1.0)"), entry(s.overlay_opacity, 100), "overlay_opacity")
        row(tr("URL base do LLM (compatível com OpenAI)"), entry(s.llm_base_url), "llm_base_url")
        row(tr("Modelo do LLM"), entry(s.llm_model), "llm_model")
        placeholder = tr(secrets.mask(secrets.get_api_key()))
        row(tr("Chave de API (opcional)"), entry("", show="•", placeholder_text=placeholder), "api_key")

        ctk.CTkLabel(scroll, text=tr("Plugins"), font=t.FONT_TITLE, text_color=t.GREEN_LIGHT).pack(
            anchor="w", padx=8, pady=(12, 2)
        )
        ctk.CTkLabel(
            scroll,
            text=tr("Plugins rodam com as mesmas permissões do app: instale só os que você confia."),
            text_color=t.MUTED,
        ).pack(anchor="w", padx=8)
        plug = ctk.CTkFrame(scroll, fg_color="transparent")
        plug.pack(anchor="w", padx=8, pady=4)
        self.plugin_boxes: dict[str, ctk.CTkCheckBox] = {}
        for record in app.plugins.records:
            text = f"{record.name} {record.version} — {record.description or record.source}"
            box = ctk.CTkCheckBox(plug, text=text, fg_color=t.GREEN, hover_color=t.GREEN_HOVER)
            if record.load_error:
                box.configure(text=tr("{name}: erro ao carregar ({error})", name=record.name, error=record.load_error))
                box.configure(state="disabled", text_color=t.DANGER)
            elif record.name not in s.disabled_plugins:
                box.select()
            box.pack(anchor="w", pady=2)
            self.plugin_boxes[record.name] = box
        if not app.plugins.records:
            ctk.CTkLabel(plug, text=tr("Nenhum plugin encontrado."), text_color=t.MUTED).pack(anchor="w")

        bar = ctk.CTkFrame(scroll, fg_color="transparent")
        bar.pack(anchor="w", padx=8)
        button(bar, tr("Salvar"), self.save).pack(side="left")
        button(
            bar, tr("Verificar atualização agora"), lambda: app.check_updates(show_current=True), primary=False
        ).pack(side="left", padx=8)
        self.status = ctk.CTkLabel(scroll, text="", text_color=t.GREEN_LIGHT, justify="left")
        self.status.pack(anchor="w", padx=8, pady=8)

    def save(self) -> None:
        values = {k: w.get() for k, w in self.fields.items()}
        api_key = str(values.pop("api_key")).strip()
        try:
            for key, cast in NUMERIC.items():
                values[key] = cast(values[key])
            for key in BOOLEAN:
                values[key] = bool(values[key])
            values["disabled_plugins"] = [
                name for name, box in self.plugin_boxes.items() if not box.get() and box.cget("state") != "disabled"
            ]
            new = Settings(**{**asdict(self.app.settings), **values}).validate()
            path = save_settings(new)
        except (ValueError, OSError) as exc:
            self.status.configure(text=tr("Configuração inválida: {error}", error=exc), text_color=t.DANGER)
            return
        if api_key:
            secrets.save_api_key(api_key)
            self.fields["api_key"].delete(0, "end")
        old = self.app.settings
        restart = (new.language, new.accent, new.tray_icon, new.disabled_plugins) != (
            old.language,
            old.accent,
            old.tray_icon,
            old.disabled_plugins,
        )
        self.app.plugins.disabled = set(new.disabled_plugins)
        self.app.settings = new
        self.app.apply_thresholds()
        msg = tr("Salvo em {path}", path=path)
        if restart:
            msg += "\n" + tr("Reinicie o app para aplicar idioma, tema, bandeja e abas de plugins.")
        self.status.configure(text=msg, text_color=t.GREEN_LIGHT)
