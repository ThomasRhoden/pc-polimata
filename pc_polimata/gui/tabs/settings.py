from __future__ import annotations

import customtkinter as ctk

from pc_polimata.core import secrets
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
}


class SettingsTab:
    def __init__(self, master: ctk.CTkFrame, app) -> None:
        self.app = app
        s = app.settings
        scroll = ctk.CTkScrollableFrame(master, fg_color="transparent")
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
        row(tr("URL base do LLM (compatível com OpenAI)"), entry(s.llm_base_url), "llm_base_url")
        row(tr("Modelo do LLM"), entry(s.llm_model), "llm_model")
        placeholder = tr(secrets.mask(secrets.get_api_key()))
        row(tr("Chave de API (opcional)"), entry("", show="•", placeholder_text=placeholder), "api_key")

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
            values["check_updates"] = bool(values["check_updates"])
            new = Settings(**values).validate()
            path = save_settings(new)
        except (ValueError, OSError) as exc:
            self.status.configure(text=tr("Configuração inválida: {error}", error=exc), text_color=t.DANGER)
            return
        if api_key:
            secrets.save_api_key(api_key)
            self.fields["api_key"].delete(0, "end")
        restart = new.language != self.app.settings.language or new.accent != self.app.settings.accent
        self.app.settings = new
        self.app.apply_thresholds()
        msg = tr("Salvo em {path}", path=path)
        if restart:
            msg += "\n" + tr("Reinicie o app para aplicar idioma e tema.")
        self.status.configure(text=msg, text_color=t.GREEN_LIGHT)
