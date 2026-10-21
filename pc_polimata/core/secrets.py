"""Chave de API do LLM: variável de ambiente ou arquivo local restrito.

Ordem: PC_POLIMATA_API_KEY -> OPENAI_API_KEY -> <config_dir>/api_key.
O arquivo fica fora do repositório, com permissão 0600 em sistemas POSIX,
e nunca entra no settings.json nem nos relatórios.
"""

from __future__ import annotations

import os
from pathlib import Path

from pc_polimata.core.settings import config_dir

ENV_VARS = ("PC_POLIMATA_API_KEY", "OPENAI_API_KEY")


def key_path(directory: Path | None = None) -> Path:
    return (directory or config_dir()) / "api_key"


def get_api_key(directory: Path | None = None) -> str | None:
    for var in ENV_VARS:
        if value := os.environ.get(var, "").strip():
            return value
    try:
        value = key_path(directory).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def save_api_key(key: str, directory: Path | None = None) -> Path:
    path = key_path(directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not key.strip():
        path.unlink(missing_ok=True)
        return path
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(key.strip())
    return path


def mask(key: str | None) -> str:
    if not key:
        return "(não configurada)"
    return f"{key[:3]}…{key[-4:]}" if len(key) > 8 else "••••"
