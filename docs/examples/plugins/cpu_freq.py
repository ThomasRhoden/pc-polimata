"""Plugin local de exemplo: copie para <config>/plugins/ (ver docs/PLUGINS.md)."""

import psutil


class CpuFreq:
    name = "cpu_freq"
    version = "0.1.0"
    description = "Current/min/max CPU frequency"

    def collect(self):
        f = psutil.cpu_freq()
        return {"current_mhz": f.current, "min_mhz": f.min, "max_mhz": f.max} if f else {"available": False}


plugin = CpuFreq()
