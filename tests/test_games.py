import pytest

from pc_polimata.core import games

TIERS = {"5": ["RTX 4060"], "6": ["RTX 4060 Ti"], "1": ["Intel UHD"]}


@pytest.mark.parametrize(
    ("name", "tier"),
    [
        ("NVIDIA GeForce RTX 4060 Ti", 6),
        ("NVIDIA GeForce RTX 4060", 5),
        ("Intel(R) UHD Graphics 620", 1),
        ("RTX 40600", None),
        (None, None),
    ],
)
def test_find_tier_longest_match(name, tier):
    assert games.find_tier(name, TIERS) == tier


def test_cpu_name_normalization():
    data = games.load_tiers()
    assert games.find_tier("13th Gen Intel(R) Core(TM) i5-13600K", data["cpu_tiers"]) == 7
    assert games.find_tier("AMD Ryzen 7 7800X3D 8-Core Processor", data["cpu_tiers"]) == 10


def test_presets():
    assert [games.preset_for(m) for m in (-5, -2, 0, 2, 4)] == ["Abaixo do mínimo", "Baixo", "Médio", "Alto", "Ultra"]


def test_estimate_limited_by():
    [e] = games.estimate(8, 4, [{"name": "G", "cpu_tier": 5, "gpu_tier": 4}])
    assert (e.preset, e.margin, e.limited_by) == ("Médio", 0, "GPU")
    [u] = games.estimate(None, 4, [{"name": "G", "cpu_tier": 5, "gpu_tier": 4}])
    assert u.preset == "Indeterminado"


def test_estimate_for_system_with_override():
    system = {"cpu": {"name": "AMD Ryzen 5 5600X 6-Core Processor"}, "gpus": []}
    out = games.estimate_for_system(system, gpu_override="RTX 3060")
    assert out["cpu_tier"] == 6 and out["gpu_tier"] == 4 and "Estimativa" in out["disclaimer"]
    assert len(out["games"]) == len(games.load_tiers()["games"])


def test_data_file_is_consistent():
    data = games.load_tiers()
    assert all(1 <= g["cpu_tier"] <= 10 and 1 <= g["gpu_tier"] <= 10 for g in data["games"])
    assert "RTX 4090" in games.known_gpus()
