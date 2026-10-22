"""Garante que todo texto marcado com tr()/N_() tem tradução EN com os mesmos placeholders."""

import ast
import string
from pathlib import Path

import pytest

import pc_polimata
from pc_polimata import i18n

PACKAGE = Path(pc_polimata.__file__).parent


def translatable_strings() -> dict[str, str]:
    """Texto -> 'arquivo:linha' de cada chamada tr("...")/N_("...") com literal."""
    found: dict[str, str] = {}
    for path in PACKAGE.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in {"tr", "N_"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                found.setdefault(node.args[0].value, f"{path.relative_to(PACKAGE)}:{node.lineno}")
    return found


def fields(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


STRINGS = translatable_strings()


def test_scanner_finds_strings():
    assert len(STRINGS) > 100


def test_every_pt_key_has_english_translation():
    missing = {text: where for text, where in STRINGS.items() if text not in i18n.EN}
    assert not missing, "Sem tradução EN:\n" + "\n".join(f"{w}: {t!r}" for t, w in missing.items())


@pytest.mark.parametrize("text", sorted(STRINGS))
def test_placeholders_match(text):
    if text in i18n.EN:
        assert fields(text) == fields(i18n.EN[text])


def test_no_stale_translations():
    stale = set(i18n.EN) - set(STRINGS)
    assert not stale, f"Traduções sem uso: {sorted(stale)}"
