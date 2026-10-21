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
    assert gpu == {"name": "AMD Radeon RX 6600", "driver": "31.0", "memory_total_mb": 8192}
