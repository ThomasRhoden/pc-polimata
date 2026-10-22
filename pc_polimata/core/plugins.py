"""Sistema de plugins.

Fontes, nesta ordem (o primeiro nome vence):
1. plugins de exemplo embutidos (`pc_polimata.plugins`);
2. entry points do grupo ``pc_polimata.plugins`` de pacotes instalados;
3. arquivos ``*.py`` na pasta local ``<config>/plugins``.

Um plugin é qualquer objeto com ``name``, ``version`` e ``collect() -> dict``
(ver `Plugin`). Opcionalmente expõe ``create_tab(master, app)`` para ganhar
uma aba na GUI. Cada chamada ao plugin passa por `PluginHost`, que captura
exceções e mede o tempo: um plugin com defeito vira um erro na tela, nunca
derruba o app.

Atenção: plugins são código Python comum, com as mesmas permissões do app.
"Isolado" aqui significa isolamento de falhas, não um sandbox de segurança.
"""

from __future__ import annotations

import importlib
import importlib.util
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol, runtime_checkable

from pc_polimata.core.settings import config_dir

ENTRY_POINT_GROUP = "pc_polimata.plugins"
BUILTIN = ("pc_polimata.plugins.uptime", "pc_polimata.plugins.battery")


@runtime_checkable
class Plugin(Protocol):
    name: str
    version: str

    def collect(self) -> dict[str, Any]: ...


@dataclass
class PluginRecord:
    name: str
    version: str
    source: str  # "builtin", "entry_point:<dist>" ou caminho do arquivo
    plugin: Plugin | None = None
    load_error: str | None = None
    description: str = ""

    @property
    def has_tab(self) -> bool:
        return callable(getattr(self.plugin, "create_tab", None))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "source": self.source,
            "description": self.description,
            "has_tab": self.has_tab,
            "load_error": self.load_error,
        }


@dataclass
class CollectResult:
    name: str
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "data": self.data, "error": self.error, "elapsed_ms": round(self.elapsed_ms, 1)}


def plugins_dir() -> Path:
    return config_dir() / "plugins"


def _describe(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"


def _resolve(obj: object) -> Plugin:
    """Aceita um objeto plugin, uma classe/fábrica ou um módulo com `plugin`/`get_plugin`."""
    if isinstance(obj, ModuleType):
        if hasattr(obj, "get_plugin"):
            obj = obj.get_plugin()
        elif hasattr(obj, "plugin"):
            obj = obj.plugin
        else:
            raise TypeError("module defines neither 'plugin' nor 'get_plugin()'")
    elif isinstance(obj, type) or (callable(obj) and not isinstance(obj, Plugin)):
        obj = obj()
    if not isinstance(obj, Plugin):
        raise TypeError("object does not implement the Plugin protocol (name, version, collect)")
    if not isinstance(obj.name, str) or not obj.name.strip():
        raise TypeError("plugin name must be a non-empty string")
    return obj


def _record(obj: object, source: str, fallback_name: str) -> PluginRecord:
    try:
        plugin = _resolve(obj)
    except Exception as exc:  # noqa: BLE001 - erro de plugin nunca propaga
        return PluginRecord(fallback_name, "?", source, load_error=_describe(exc))
    return PluginRecord(
        plugin.name, str(plugin.version), source, plugin, description=str(getattr(plugin, "description", ""))
    )


def load_file(path: Path) -> PluginRecord:
    name = f"pc_polimata_local_plugin_{path.stem}"
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - inclui SyntaxError
        return PluginRecord(path.stem, "?", str(path), load_error=_describe(exc))
    return _record(module, str(path), path.stem)


def discover(
    directory: Path | None = None,
    entry_point_loader: Callable[[], Iterable[Any]] | None = None,
    builtin: Iterable[str] = BUILTIN,
) -> list[PluginRecord]:
    """Encontra e carrega todos os plugins; falhas viram `load_error` no registro."""
    records: list[PluginRecord] = []
    for module_name in builtin:
        try:
            records.append(_record(importlib.import_module(module_name), "builtin", module_name))
        except Exception as exc:  # noqa: BLE001
            records.append(PluginRecord(module_name, "?", "builtin", load_error=_describe(exc)))

    loader = entry_point_loader or (lambda: entry_points(group=ENTRY_POINT_GROUP))
    try:
        eps = list(loader())
    except Exception:  # noqa: BLE001 - metadados corrompidos não impedem o resto
        eps = []
    for ep in eps:
        dist = getattr(getattr(ep, "dist", None), "name", None) or "?"
        try:
            obj = ep.load()
        except Exception as exc:  # noqa: BLE001
            records.append(PluginRecord(ep.name, "?", f"entry_point:{dist}", load_error=_describe(exc)))
            continue
        records.append(_record(obj, f"entry_point:{dist}", ep.name))

    folder = directory if directory is not None else plugins_dir()
    if folder.is_dir():
        for path in sorted(folder.glob("*.py")):
            if not path.name.startswith("_"):
                records.append(load_file(path))

    unique: dict[str, PluginRecord] = {}
    for rec in records:
        if rec.name in unique:
            continue
        unique[rec.name] = rec
    return list(unique.values())


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


class PluginHost:
    """Guarda os plugins descobertos e chama cada um com isolamento de falhas."""

    def __init__(self, records: list[PluginRecord], disabled: Iterable[str] = ()) -> None:
        self.records = records
        self.disabled = set(disabled)
        self.last_errors: dict[str, str] = {}

    def enabled(self) -> list[PluginRecord]:
        return [r for r in self.records if r.plugin is not None and r.name not in self.disabled]

    def collect(self, record: PluginRecord) -> CollectResult:
        start = time.perf_counter()
        try:
            if record.plugin is None:
                raise RuntimeError(record.load_error or "plugin not loaded")
            data = record.plugin.collect()
            if not isinstance(data, dict):
                raise TypeError(f"collect() must return dict, got {type(data).__name__}")
            result = CollectResult(record.name, True, _jsonable(data))
            self.last_errors.pop(record.name, None)
        except Exception as exc:  # noqa: BLE001 - o ponto deste host
            result = CollectResult(record.name, False, error=_describe(exc))
            self.last_errors[record.name] = result.error or ""
        result.elapsed_ms = (time.perf_counter() - start) * 1000
        return result

    def collect_all(self) -> dict[str, CollectResult]:
        return {r.name: self.collect(r) for r in self.enabled()}

    def create_tab(self, record: PluginRecord, master: Any, app: Any) -> str | None:
        """Monta a aba do plugin; devolve a mensagem de erro (ou None se deu certo)."""
        factory = getattr(record.plugin, "create_tab", None)
        if not callable(factory):
            return None
        try:
            factory(master, app)
        except Exception as exc:  # noqa: BLE001
            self.last_errors[record.name] = _describe(exc)
            return _describe(exc)
        return None
