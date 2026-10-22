"""Interface de linha de comando (funciona sem GUI / headless)."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from pc_polimata import __version__
from pc_polimata.core import (
    benchmark,
    diagnosis,
    drivers,
    exchange,
    games,
    memory_bench,
    plugins,
    presentmon,
    report,
    secrets,
    smart,
    updates,
)
from pc_polimata.core.gpu import GPUStatus
from pc_polimata.core.history import HistoryStore
from pc_polimata.core.settings import load_settings
from pc_polimata.core.system_info import get_system_info
from pc_polimata.i18n import SUPPORTED, set_language, tr

REPORT_FLAGS = ("report", "benchmark", "memory", "smart", "games", "diagnose", "drivers", "plugins")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pc-polimata", description=tr("Diagnóstico e benchmark de hardware."))
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--lang", choices=SUPPORTED, help=tr("idioma das mensagens e do relatório"))
    p.add_argument("--report", action="store_true", help=tr("gera relatório sem abrir a GUI"))
    p.add_argument("--benchmark", action="store_true", help=tr("inclui benchmark de CPU e disco"))
    p.add_argument("--memory", action="store_true", help=tr("inclui benchmark de memória"))
    p.add_argument("--smart", action="store_true", help=tr("inclui saúde dos discos (smartctl)"))
    p.add_argument("--games", action="store_true", help=tr("inclui estimativa de desempenho em jogos"))
    p.add_argument("--drivers", action="store_true", help=tr("inclui versão/data dos drivers de vídeo"))
    p.add_argument("--diagnose", action="store_true", help=tr("inclui diagnóstico por regras"))
    p.add_argument("--llm", action="store_true", help=tr("com --diagnose, usa o LLM se houver chave de API"))
    p.add_argument("--plugins", action="store_true", help=tr("inclui os dados dos plugins habilitados"))
    p.add_argument("--list-plugins", action="store_true", help=tr("lista os plugins encontrados e sai"))
    p.add_argument("--export-runs", metavar="FILE", help=tr("exporta as últimas execuções do histórico em JSON"))
    p.add_argument("--compare", nargs=2, metavar=("A", "B"), help=tr("compara dois arquivos exportados"))
    p.add_argument("--fps-csv", metavar="CSV", help=tr("calcula FPS/1%% low de um CSV do PresentMon"))
    p.add_argument("--process", help=tr("com --fps-csv, filtra pelo executável do jogo"))
    p.add_argument("--check-update", action="store_true", help=tr("consulta o GitHub por uma versão mais nova"))
    p.add_argument("--duration", type=float, default=3.0, help=tr("segundos por fase do benchmark"))
    p.add_argument("--no-history", action="store_true", help=tr("não salva benchmarks no histórico SQLite"))
    p.add_argument("-o", "--output", help=tr("arquivo de saída (.json, .html ou .pdf); padrão: JSON no stdout"))
    return p


def _save_history(enabled: bool, runs: list[tuple[str, dict]], system: dict) -> None:
    if not enabled or not runs:
        return
    try:
        store = HistoryStore()
    except Exception as exc:  # noqa: BLE001
        print(tr("Aviso: histórico indisponível ({error})", error=exc), file=sys.stderr)
        return
    hardware = {"cpu": system["cpu"]["name"], "gpus": [g["name"] for g in system["gpus"]]}
    for kind, metrics in runs:
        store.save_run(kind, metrics, hardware, note="cli")
    store.close()


def run_report(args: argparse.Namespace) -> int:
    system = get_system_info()
    sections: dict[str, Any] = {}
    runs: list[tuple[str, dict]] = []
    if args.benchmark:
        sections["cpu_benchmark"] = benchmark.run_cpu_benchmark(args.duration).to_dict()
        sections["disk_benchmark"] = benchmark.run_disk_benchmark(64).to_dict()
        runs += [("cpu", sections["cpu_benchmark"]), ("disk", sections["disk_benchmark"])]
    if args.memory:
        sections["memory_benchmark"] = memory_bench.run_memory_benchmark().to_dict()
        runs.append(("memory", sections["memory_benchmark"]))
    if args.smart:
        sections["disk_health"] = [h.to_dict() for h in smart.check_disks()]
    if args.drivers:
        gpus = [
            GPUStatus(**{k: v for k, v in g.items() if k in GPUStatus.__dataclass_fields__}) for g in system["gpus"]
        ]
        sections["drivers"] = [d.to_dict() for d in drivers.driver_report(gpus)]
    if args.games:
        sections["games_estimate"] = games.estimate_for_system(system)
    if args.plugins:
        settings = load_settings()
        host = plugins.PluginHost(plugins.discover(), settings.disabled_plugins)
        sections["plugins"] = {n: r.to_dict() for n, r in host.collect_all().items()}
    _save_history(not args.no_history, runs, system)

    data = report.build_report(system, **sections)
    if args.diagnose:
        settings = load_settings()
        key = secrets.get_api_key() if args.llm else None
        data["diagnosis"] = diagnosis.diagnose(
            data, key, base_url=settings.llm_base_url, model=settings.llm_model, language=settings.language
        ).to_dict()
    if args.output:
        try:
            path = report.save_report(data, args.output)
        except report.PdfUnavailableError as exc:
            print(exc, file=sys.stderr)
            return 2
        print(tr("Relatório salvo em {path}", path=path))
    else:
        print(report.to_json(data))
    return 0


def run_tools(args: argparse.Namespace) -> int:
    """Comandos avulsos que não geram relatório."""
    if args.list_plugins:
        for rec in plugins.discover():
            state = tr("erro: {error}", error=rec.load_error) if rec.load_error else rec.source
            print(f"{rec.name:<20} {rec.version:<10} {state}")
        return 0
    if args.export_runs:
        try:
            store = HistoryStore()
        except Exception as exc:  # noqa: BLE001
            print(tr("Aviso: histórico indisponível ({error})", error=exc), file=sys.stderr)
            return 1
        latest = [r for kind in exchange.PRIMARY_METRICS for r in store.list_runs(kind, limit=1)]
        store.close()
        if not latest:
            print(tr("Nenhuma execução salva ainda."), file=sys.stderr)
            return 1
        system = get_system_info()
        path = exchange.export_bundle(
            exchange.make_bundle(system["cpu"]["name"] or "PC", system, latest), args.export_runs
        )
        print(tr("Salvo em {path}", path=path))
        return 0
    if args.compare:
        try:
            a, b = (exchange.import_bundle(p) for p in args.compare)
        except (OSError, ValueError) as exc:
            print(tr("Arquivo inválido: {error}", error=exc), file=sys.stderr)
            return 2
        result = {"a": a.to_dict(), "b": b.to_dict(), "rows": [r.to_dict() for r in exchange.compare_bundles(a, b)]}
        print(report.to_json(result))
        return 0
    try:
        with open(args.fps_csv, encoding="utf-8", errors="replace") as fh:
            stats = presentmon.parse_csv(fh.read(), args.process)
    except (OSError, ValueError) as exc:
        print(tr("Falha na medição: {error}", error=exc), file=sys.stderr)
        return 2
    print(report.to_json(stats.to_dict()))
    return 0


def _initial_language(argv: list[str]) -> None:
    """Aplica o idioma antes de montar o parser (para o --help sair traduzido)."""
    lang = load_settings().language
    if "--lang" in argv and argv.index("--lang") + 1 < len(argv):
        lang = argv[argv.index("--lang") + 1]
    if lang in SUPPORTED:
        set_language(lang)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    _initial_language(argv)
    args = build_parser().parse_args(argv)
    if args.list_plugins or args.export_runs or args.compare or args.fps_csv:
        return run_tools(args)
    if args.check_update:
        status = updates.check_for_update()
        if status.error:
            print(tr("Não foi possível verificar atualizações: {error}", error=status.error))
        elif status.update_available:
            print(tr("Nova versão disponível: {latest} — {url}", latest=status.latest, url=status.url))
        else:
            print(tr("Você já está na versão mais recente ({current}).", current=status.current))
        if not any(getattr(args, f) for f in REPORT_FLAGS):
            return 0
    if any(getattr(args, f) for f in REPORT_FLAGS):
        return run_report(args)
    try:
        from pc_polimata.gui.app import run_gui
    except ImportError as exc:
        print(tr("GUI indisponível ({error}). Use --report.", error=exc), file=sys.stderr)
        return 1
    run_gui()
    return 0
