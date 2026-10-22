import json

from pc_polimata.core import gpu


def make_card(root, name, vendor="0x1002", **files):
    dev = root / name / "device"
    (dev / "hwmon" / "hwmon3").mkdir(parents=True)
    (dev / "vendor").write_text(vendor + "\n")
    for fname, value in files.items():
        target = dev / "hwmon" / "hwmon3" / "temp1_input" if fname == "temp" else dev / fname
        target.write_text(str(value) + "\n")
    return dev


def test_amd_sysfs_reads_everything(tmp_path):
    make_card(
        tmp_path,
        "card0",
        gpu_busy_percent=37,
        temp=55000,
        mem_info_vram_total=8 * 2**30,
        mem_info_vram_used=2 * 2**30,
        product_name="Radeon RX 6600",
    )
    make_card(tmp_path, "card1", vendor="0x10de")  # NVIDIA: ignorada
    (tmp_path / "card0-HDMI-A-1").mkdir()
    [g] = gpu.from_amd_sysfs(tmp_path)
    assert g.name == "Radeon RX 6600"
    assert (g.load_percent, g.temperature_c, g.memory_total_mb, g.memory_used_mb) == (37, 55, 8192, 2048)


def test_amd_sysfs_missing_files(tmp_path):
    make_card(tmp_path, "card0", device="0x73ff")
    [g] = gpu.from_amd_sysfs(tmp_path)
    assert g.load_percent is None and g.temperature_c is None and "0x73ff" in g.name


def test_amd_sysfs_no_drm(tmp_path):
    assert gpu.from_amd_sysfs(tmp_path / "nope") == []


def test_parse_rocm_smi():
    out = json.dumps(
        {
            "card0": {
                "GPU use (%)": "12",
                "Temperature (Sensor edge) (C)": "48.0",
                "VRAM Total Memory (B)": str(16 * 2**30),
                "VRAM Total Used Memory (B)": str(2**30),
                "Card series": "Radeon RX 7800 XT",
            },
            "system": {},
        }
    )
    [g] = gpu.parse_rocm_smi(out)
    assert (g.name, g.load_percent, g.temperature_c, g.memory_total_mb) == (
        "Radeon RX 7800 XT",
        12,
        48,
        16384,
    )


def test_get_gpus_never_raises(monkeypatch):
    def boom():
        raise RuntimeError

    monkeypatch.setattr(gpu, "BACKENDS", (boom, lambda: [gpu.GPUStatus("X")]))
    assert gpu.get_gpus()[0].name == "X"


def test_assign_utilization():
    assert gpu.assign_utilization(1, {"a": 0.0, "b": 42.04}) == [42.0]
    assert gpu.assign_utilization(2, {"a": 10.0}) == [10.0, None]
    assert gpu.assign_utilization(2, {}) == [None, None]


def test_from_wmi_combines_sources(monkeypatch):
    from pc_polimata.core import windows_temps as wt

    monkeypatch.setattr(
        wt,
        "list_video_controllers",
        lambda: [
            {"name": "AMD Radeon RX 6600", "driver": "31.0", "memory_total_mb": 8192, "driver_date": "2024-01-02"}
        ],
    )
    monkeypatch.setattr(wt, "read_gpu_utilization", lambda: {"x": 63.0})
    monkeypatch.setattr(wt, "read_windows_temps", lambda: wt.WindowsTemps(gpu_c=58.0))
    [g] = gpu._from_wmi()
    assert (g.load_percent, g.temperature_c, g.driver_date, g.source) == (63.0, 58.0, "2024-01-02", "wmi")
