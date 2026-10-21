"""Conversão e formatação de unidades."""

from __future__ import annotations

TEMP_UNITS = ("C", "F")


def celsius_to_fahrenheit(c: float) -> float:
    return c * 9 / 5 + 32


def format_temp(celsius: float | None, unit: str = "C") -> str:
    if unit not in TEMP_UNITS:
        raise ValueError(f"unknown unit: {unit}")
    if celsius is None:
        return "n/d"
    value = celsius_to_fahrenheit(celsius) if unit == "F" else celsius
    return f"{value:.0f} °{unit}"
