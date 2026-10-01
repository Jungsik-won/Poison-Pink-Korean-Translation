#!/usr/bin/env python3
import struct

with open('Poison Pink (Japan)/SLPS_258.54', 'rb') as f:
    elf_data = f.read()

# Let's inspect code around 0x00168d00 to 0x00169500 (VAddr 0x00268d00 - 0x00269500)
# Look for jr instruction (jump to register, typical for switch-case dispatch)
for off in range(0x00168000, 0x00170000, 4):
    instr = struct.unpack('<I', elf_data[off:off+4])[0]
    if (instr & 0xfc1fffff) == 0x00000008: # jr $reg
        rs = (instr >> 21) & 0x1f
        if rs != 31: # not jr $ra
            print(f"Found indirect jump at 0x{off:08x} (VAddr 0x{off+0x00100000:08x}) using register ${rs}")

