"""Imprime o subsistema PE de um .exe (2 = GUI/sem console, 3 = console). Usado no workflow de release."""

import struct
import sys

with open(sys.argv[1], "rb") as fh:
    data = fh.read(4096)
pe = struct.unpack_from("<I", data, 0x3C)[0]
subsystem = struct.unpack_from("<H", data, pe + 24 + 68)[0]
print(subsystem)
sys.exit(0 if len(sys.argv) < 3 or str(subsystem) == sys.argv[2] else 1)
