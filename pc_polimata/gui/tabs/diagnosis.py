from __future__ import annotations

import customtkinter as ctk

from pc_polimata.core import diagnosis, secrets
from pc_polimata.gui import theme as t
from pc_polimata.gui.widgets import button, run_in_thread, set_text, textbox
from pc_polimata.i18n import get_language, tr

ICONS = {"crítico": "✖", "atenção": "▲", "info": "●"}


class DiagnosisTab:
    def __init__(self, master: ctk.CTkFrame, app) -> None:
        self.app = app
        bar = ctk.CTkFrame(master, fg_color="transparent")
        bar.pack(fill="x", padx=8, pady=8)
        self.btn = button(bar, tr("Analisar"), self.run)
        self.btn.pack(side="left")
        self.use_llm = ctk.CTkCheckBox(
            bar, text=tr("Usar LLM (requer chave de API)"), fg_color=t.GREEN, hover_color=t.GREEN_HOVER
        )
        self.use_llm.pack(side="left", padx=12)
        self.key_label = ctk.CTkLabel(bar, text="", text_color=t.MUTED)
        self.key_label.pack(side="left")
        self.box = textbox(master)
        self.update_key_label()
        set_text(
            self.box,
            tr(
                "O diagnóstico por regras funciona offline. A análise por LLM envia o relatório (sem hostname)\n"
                "ao endpoint configurado em Configurações. Execute benchmarks/gargalo/SMART antes para\n"
                "um diagnóstico mais completo."
            ),
        )

    def update_key_label(self) -> None:
        self.key_label.configure(text=tr("Chave de API: {key}", key=tr(secrets.mask(secrets.get_api_key()))))

    def run(self) -> None:
        self.update_key_label()
        self.btn.configure(state="disabled")
        set_text(self.box, tr("Executando..."))
        report = self.app.build_report()
        key = secrets.get_api_key() if self.use_llm.get() else None
        s = self.app.settings
        run_in_thread(
            self.btn,
            lambda: diagnosis.diagnose(
                report, key, base_url=s.llm_base_url, model=s.llm_model, language=get_language()
            ),
            self.done,
        )

    def done(self, res) -> None:
        self.btn.configure(state="normal")
        if isinstance(res, Exception):
            set_text(self.box, tr("Erro: {error}", error=res))
            return
        self.app.record("diagnosis", res.to_dict())
        lines = [tr("Saúde geral: {score}/100   (fonte: {source})", score=res.score, source=tr(res.source)), ""]
        lines += [f"{ICONS[f.severity]} [{tr(f.severity)}] {f.title}\n    {f.detail}" for f in res.findings]
        if self.use_llm.get() and not res.llm_analysis:
            lines += ["", tr("LLM indisponível: {error}", error=res.llm_error or tr("chave de API não configurada"))]
        if res.llm_analysis:
            lines += ["", tr("— Análise do LLM —"), res.llm_analysis]
        set_text(self.box, "\n".join(lines))
