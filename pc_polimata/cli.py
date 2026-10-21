"""Interface de linha de comando (funciona sem GUI / headless)."""

from __future__ import annotations

import argparse
import sys

from pc_polimata.core import benchmark, report
from pc_polimata.core.system_info import get_system_info


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pc_polimata", description="Diagnóstico e benchmark de hardware.")
    p.add_argument("--report", action="store_true", help="gera relatório sem abrir a GUI")
    p.add_argument("--benchmark", action="store_true", help="inclui benchmark de CPU e disco")
    p.add_argument("--duration", type=float, default=3.0, help="segundos por fase do benchmark")
    p.add_argument("-o", "--output", help="arquivo de saída (.json ou .html); padrão: stdout JSON")
    return p


def run_report(args: argparse.Namespace) -> int:
    sections = {}
    if args.benchmark:
        sections["cpu_benchmark"] = benchmark.run_cpu_benchmark(args.duration).to_dict()
        sections["disk_benchmark"] = benchmark.run_disk_benchmark(64).to_dict()
    data = report.build_report(get_system_info(), **sections)
    if args.output:
        path = report.save_report(data, args.output)
        print(f"Relatório salvo em {path}")
    else:
        print(report.to_json(data))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.report or args.benchmark:
        return run_report(args)
    try:
        from pc_polimata.gui.app import run_gui
    except ImportError as exc:
        print(f"GUI indisponível ({exc}). Use --report.", file=sys.stderr)
        return 1
    run_gui()
    return 0
