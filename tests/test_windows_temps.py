from types import SimpleNamespace as NS

from pc_polimata.core import windows_temps as wt


def sensor(parent, name, value, kind="Temperature"):
    return NS(Parent=parent, Name=name, Value=value, SensorType=kind)


class FakeWMI:
    def __init__(self, sensors=None, controllers=None, fail_ns=()):
        self.sensors, self.controllers, self.fail_ns = sensors or [], controllers or [], fail_ns

    def WMI(self, namespace="root\\cimv2"):
        if namespace in self.fail_ns:
            raise OSError("namespace inexistente")
        return NS(Sensor=lambda: self.sensors, Win32_VideoController=lambda: self.controllers)


SENSORS = [
    sensor("/amdcpu/0", "Core #1", 60.0),
    sensor("/amdcpu/0", "Core (Tctl/Tdie)", 71.5),
    sensor("/gpu-nvidia/0", "GPU Core", 64.0),
    sensor("/amdcpu/0", "CPU Total", 40.0, kind="Load"),
]


def test_parse_prefers_package():
    assert wt.parse_sensors(SENSORS) == (71.5, 64.0)


def test_parse_empty():
    assert wt.parse_sensors([]) == (None, None)


def test_non_windows_returns_none():
    assert wt.read_windows_temps(FakeWMI(SENSORS), platform="linux").cpu_c is None


def test_falls_back_to_openhardwaremonitor():
    fake = FakeWMI(SENSORS, fail_ns=(wt.NAMESPACES[0],))
    temps = wt.read_windows_temps(fake, platform="win32")
    assert temps.cpu_c == 71.5 and temps.source == wt.NAMESPACES[1]


def test_program_not_running():
    fake = FakeWMI(fail_ns=wt.NAMESPACES)
    assert wt.read_windows_temps(fake, platform="win32") == wt.WindowsTemps()


def test_video_controllers():
    fake = FakeWMI(controllers=[NS(Name="AMD Radeon RX 6600", DriverVersion="31.0", AdapterRAM=2**33)])
    [gpu] = wt.list_video_controllers(fake, platform="win32")
    assert gpu == {"name": "AMD Radeon RX 6600", "driver": "31.0", "memory_total_mb": 8192, "driver_date": None}


def engine(name, util):
    return NS(Name=name, UtilizationPercentage=util)


ENGINES = [
    engine("pid_10_luid_0x00000000_0x0000D1B1_phys_0_eng_0_engtype_3D", 30),
    engine("pid_22_luid_0x00000000_0x0000D1B1_phys_0_eng_0_engtype_3D", 25),
    engine("pid_22_luid_0x00000000_0x0000D1B1_phys_0_eng_3_engtype_VideoDecode", 90),
    engine("pid_5_luid_0x00000000_0x0000E2C2_phys_0_eng_0_engtype_3D", 80),
    engine("pid_6_luid_0x00000000_0x0000E2C2_phys_0_eng_0_engtype_3D", 70),
    engine("garbage", 50),
]


def test_parse_gpu_engines_sums_3d_per_adapter():
    assert wt.parse_gpu_engines(ENGINES) == {
        "0x00000000_0x0000d1b1_phys_0": 55.0,
        "0x00000000_0x0000e2c2_phys_0": 100.0,  # 150 limitado a 100
    }


def test_read_gpu_utilization():
    fake = NS(WMI=lambda: NS(Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine=lambda: ENGINES))
    assert len(wt.read_gpu_utilization(fake, platform="win32")) == 2
    assert wt.read_gpu_utilization(fake, platform="linux") == {}


def test_read_gpu_utilization_missing_class():
    def boom():
        raise AttributeError("classe inexistente")

    fake = NS(WMI=lambda: NS(Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine=boom))
    assert wt.read_gpu_utilization(fake, platform="win32") == {}


def test_parse_driver_date():
    assert wt.parse_driver_date("20240315000000.000000-000") == "2024-03-15"
    assert wt.parse_driver_date(None) is None
