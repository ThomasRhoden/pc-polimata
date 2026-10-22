"""Faixa de alerta não bloqueante no topo da janela."""

from __future__ import annotations

import customtkinter as ctk

from pc_polimata.gui import theme as t


class AlertBanner(ctk.CTkFrame):
    """Mostra mensagens empilhadas e se esconde sozinha após `timeout_ms`."""

    def __init__(self, master, timeout_ms: int = 12_000) -> None:
        super().__init__(master, fg_color=t.DANGER, corner_radius=6)
        self.timeout_ms = timeout_ms
        self.label = ctk.CTkLabel(self, text="", text_color="#ffffff", anchor="w", justify="left")
        self.label.pack(side="left", fill="x", expand=True, padx=10, pady=4)
        ctk.CTkButton(self, text="✕", width=28, fg_color="transparent", hover_color=t.BROWN, command=self.hide).pack(
            side="right", padx=4
        )
        self.messages: list[str] = []
        self._job: str | None = None
        self._before: ctk.CTkBaseClass | None = None

    def attach_before(self, widget: ctk.CTkBaseClass) -> None:
        self._before = widget

    def show(self, message: str, color: str | None = None) -> None:
        self.messages = (self.messages + [message])[-3:]
        self.configure(fg_color=color or t.DANGER)
        self.label.configure(text="⚠  " + "\n⚠  ".join(self.messages))
        if not self.winfo_ismapped():
            self.pack(fill="x", padx=12, pady=(6, 0), before=self._before)
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(self.timeout_ms, self.hide)

    def hide(self) -> None:
        self.messages = []
        self._job = None
        self.pack_forget()
