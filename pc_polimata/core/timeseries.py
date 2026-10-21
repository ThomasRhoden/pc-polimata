"""Janela deslizante de amostras para gráficos ao vivo."""

from __future__ import annotations

from collections import deque


class RollingSeries:
    """Guarda as últimas `maxlen` amostras por série (ex.: 60 s a 1 Hz)."""

    def __init__(self, names: list[str], maxlen: int = 60) -> None:
        if maxlen < 2:
            raise ValueError("maxlen must be >= 2")
        self.maxlen = maxlen
        self._data: dict[str, deque[float | None]] = {n: deque(maxlen=maxlen) for n in names}

    @property
    def names(self) -> list[str]:
        return list(self._data)

    def append(self, **values: float | None) -> None:
        for name, series in self._data.items():
            series.append(values.get(name))

    def values(self, name: str) -> list[float | None]:
        return list(self._data[name])

    def __len__(self) -> int:
        return max((len(s) for s in self._data.values()), default=0)


def to_points(
    values: list[float | None],
    width: float,
    height: float,
    maxlen: int,
    vmax: float = 100.0,
    vmin: float = 0.0,
) -> list[list[tuple[float, float]]]:
    """Converte valores em segmentos de coordenadas de tela (None quebra a linha).

    Valores mais recentes ficam à direita; y=0 é o topo do canvas.
    """
    if vmax <= vmin:
        raise ValueError("vmax must be greater than vmin")
    step = width / (maxlen - 1)
    offset = maxlen - len(values)
    segments: list[list[tuple[float, float]]] = [[]]
    for i, v in enumerate(values):
        if v is None:
            if segments[-1]:
                segments.append([])
            continue
        clamped = min(max(v, vmin), vmax)
        segments[-1].append(((offset + i) * step, height - (clamped - vmin) / (vmax - vmin) * height))
    return [s for s in segments if s]
