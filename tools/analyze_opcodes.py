#!/usr/bin/env python3
import struct
from extract_file import extract_archive_file

data = extract_archive_file('Poison Pink (Japan)/DATA/DMAP', 't00_0010.rtb')

# Bytecode starts around 0x313d
start_bytecode = 0x313d
pos = start_bytecode

opcodes = {}
# Let's inspect known opcodes
# 0x33: string -> len 5 + 1 + len
# 0x31: int -> 5 + 4 bytes? (e.g. 31 01 7c f0 c1 00 00 00 00)
# 0x68: call -> 5 + 4 (hash) + 4 (arg count?) + 1
# 0x6c: jump/branch?
# Let's find all instances of 0x6c:
jumps = []
for p in range(start_bytecode, len(data)-9):
    if data[p] == 0x6c and data[p+2:p+5] in (b'\x7c\xf0\xc1', b'\x7c\x10\xc0'):
        target_val = struct.unpack('<i', data[p+5:p+9])[0]
        jumps.append((p, target_val))

print(f"Found {len(jumps)} instances of opcode 0x6c:")
for p, target in jumps[:20]:
    print(f"  0x{p:04x}: offset={target} (0x{target:x}) -> abs target candidate: 0x{p+9+target:04x} or 0x{target:04x}")

