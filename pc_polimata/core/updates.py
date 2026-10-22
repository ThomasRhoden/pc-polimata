"""Verificação (opt-in) de nova versão do PC Polimata na API de releases do GitHub."""

from __future__ import annotations

import json
import re
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from pc_polimata import __version__

RELEASES_URL = "https://api.github.com/repos/ThomasRhoden/pc-polimata/releases/latest"
Opener = Callable[..., Any]


@dataclass
class UpdateStatus:
    current: str
    latest: str | None
    update_available: bool
    url: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def parse_version(text: str) -> tuple[int, ...]:
    """'v0.10.2' -> (0, 10, 2); sufixos como '-rc1' são ignorados."""
    match = re.match(r"^v?(\d+(?:\.\d+)*)", text.strip())
    if not match:
        raise ValueError(f"invalid version: {text!r}")
    return tuple(int(p) for p in match[1].split("."))


def is_newer(latest: str, current: str) -> bool:
    a, b = parse_version(latest), parse_version(current)
    width = max(len(a), len(b))
    return a + (0,) * (width - len(a)) > b + (0,) * (width - len(b))


def check_for_update(
    current: str = __version__,
    url: str = RELEASES_URL,
    timeout: float = 5.0,
    opener: Opener = urllib.request.urlopen,
) -> UpdateStatus:
    """Nunca lança exceção: falhas de rede viram `error`."""
    req = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json", "User-Agent": f"pc-polimata/{current}"}
    )
    try:
        with opener(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
        tag = str(data["tag_name"])
        return UpdateStatus(current, tag.lstrip("v"), is_newer(tag, current), data.get("html_url"))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return UpdateStatus(current, None, False, error=str(exc))
