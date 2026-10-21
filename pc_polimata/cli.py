"""Interface de linha de comando (funciona sem GUI / headless)."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from pc_polimata import __version__
from pc_polimata.core import benchmark, diagnosis, games, memory_bench, report, secrets, smart
from pc_polimata.core.history import HistoryStore
from pc_polimata.core.settings import load_settings
from pc_polimata.core.system_info import get_system_info


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pc-polimata", description="Diagnóstico e benchmark de hardware.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--report", action="store_true", help="gera relatório sem abrir a GUI")
    p.add_argument("--benchmark", action="store_true", help="inclui benchmark de CPU e disco")
    p.add_argument("--memory", action="store_true", help="inclui benchmark de memória")
    p.add_argument("--smart", action="store_true", help="inclui saúde dos discos (smartctl)")
    p.add_argument("--games", action="store_true", help="inclui estimativa de desempenho em jogos")
    p.add_argument("--diagnose", action="store_true", help="inclui diagnóstico por regras")
    p.add_argument("--llm", action="store_true", help="com --diagnose, usa o LLM se houver chave de API")
    p.add_argument("--duration", type=float, default=3.0, help="segundos por fase do benchmark")
    p.add_argument("--no-history", action="store_true", help="não salva benchmarks no histórico SQLite")
    p.add_argument("-o", "--output", help="arquivo de saída (.json ou .html); padrão: stdout JSON")
    return p


def _save_history(enabled: bool, runs: list[tuple[str, dict]], system: dict) -> None:
    if not enabled or not runs:
        return
    try:
        store = HistoryStore()
    except Exception as exc:  # noqa: BLE001
        print(f"Aviso: histórico indisponível ({exc})", file=sys.stderr)
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
    if args.games:
        sections["games_estimate"] = games.estimate_for_system(system)
    _save_history(not args.no_history, runs, system)

    data = report.build_report(system, **sections)
    if args.diagnose:
        settings = load_settings()
        key = secrets.get_api_key() if args.llm else None
        data["diagnosis"] = diagnosis.diagnose(
            data, key, base_url=settings.llm_base_url, model=settings.llm_model, language=settings.language
        ).to_dict()
    if args.output:
        path = report.save_report(data, args.output)
        print(f"Relatório salvo em {path}")
    else:
        print(report.to_json(data))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if any((args.report, args.benchmark, args.memory, args.smart, args.games, args.diagnose)):
        return run_report(args)
    try:
        from pc_polimata.gui.app import run_gui
    except ImportError as exc:
        print(f"GUI indisponível ({exc}). Use --report.", file=sys.stderr)
        return 1
    run_gui()
    return 0
