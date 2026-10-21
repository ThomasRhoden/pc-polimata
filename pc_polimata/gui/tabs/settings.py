from __future__ import annotations

import customtkinter as ctk

from pc_polimata.core import secrets
from pc_polimata.core.settings import ACCENTS, LANGUAGES, Settings, save_settings
from pc_polimata.core.units import TEMP_UNITS
from pc_polimata.gui import theme as t
from pc_polimata.gui.widgets import button
from pc_polimata.i18n import tr


class SettingsTab:
    def __init__(self, master: ctk.CTkFrame, app) -> None:
        self.app = app
        s = app.settings
        form = ctk.CTkFrame(master, fg_color="transparent")
        form.pack(anchor="w", padx=12, pady=12)
        self.fields: dict[str, ctk.CTkBaseClass] = {}

        def row(label: str, widget: ctk.CTkBaseClass, key: str) -> None:
            r = len(self.fields)
            ctk.CTkLabel(form, text=label, anchor="w", width=260).grid(row=r, column=0, sticky="w", pady=5)
            widget.grid(row=r, column=1, sticky="w", pady=5)
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
        row("LLM base URL (OpenAI-compatible)", entry(s.llm_base_url), "llm_base_url")
        row("LLM model", entry(s.llm_model), "llm_model")
        row(
            tr("Chave de API (opcional)"),
            entry("", show="•", placeholder_text=secrets.mask(secrets.get_api_key())),
            "api_key",
        )
        button(master, tr("Salvar"), self.save).pack(anchor="w", padx=12)
        self.status = ctk.CTkLabel(master, text="", text_color=t.GREEN_LIGHT, justify="left")
        self.status.pack(anchor="w", padx=12, pady=8)

    def save(self) -> None:
        values = {k: w.get() for k, w in self.fields.items()}
        api_key = values.pop("api_key").strip()
        try:
            new = Settings(**{**values, "refresh_ms": int(values["refresh_ms"])}).validate()
            path = save_settings(new)
        except (ValueError, OSError) as exc:
            self.status.configure(text=f"{tr('Configuração inválida')}: {exc}", text_color=t.DANGER)
            return
        if api_key:
            secrets.save_api_key(api_key)
            self.fields["api_key"].delete(0, "end")
        self.app.settings.temperature_unit = new.temperature_unit  # aplicados imediatamente
        self.app.settings.refresh_ms = new.refresh_ms
        self.app.settings.llm_base_url, self.app.settings.llm_model = new.llm_base_url, new.llm_model
        self.status.configure(
            text=f"{tr('Salvo em')} {path}\n{tr('Reinicie o app para aplicar idioma e tema.')}",
            text_color=t.GREEN_LIGHT,
        )
