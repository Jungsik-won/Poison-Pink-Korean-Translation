#!/usr/bin/env python3
import os
import sys

from extract_file import extract_archive_file

def inspect_file(arch, fname):
    data = extract_archive_file(arch, fname)
    if data:
        magic = data[:16]
        hex_m = magic.hex()
        asc_m = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in magic)
        print(f"[{fname:<16}] Size: {len(data):8d} | Magic: {hex_m} | ASCII: {asc_m}")

for f in ['ev_win4.uad', 'nload_00.vly', 'PPPARAM.dat', 'file.ico']:
    inspect_file('Poison Pink (Japan)/DATA/STATUS', f)

for f in ['cf0010.scp', 'MINFO00_0000.dat']:
    inspect_file('Poison Pink (Japan)/DATA/DMAP', f)
