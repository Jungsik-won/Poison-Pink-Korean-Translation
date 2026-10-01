#!/usr/bin/env python3
import os
import sys
import struct

from extract_file import extract_archive_file

def dump_rtb_chunk(data, start, length):
    sub = data[start:start+length]
    print(f"--- Offset 0x{start:04x} ---")
    for i in range(0, len(sub), 16):
        row = sub[i:i+16]
        hex_s = ' '.join(f'{b:02x}' for b in row)
        asc_s = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in row)
        print(f"{start+i:04x}: {hex_s:<48} | {asc_s}")

data = extract_archive_file('Poison Pink (Japan)/DATA/DMAP', 't00_0010.rtb')
dump_rtb_chunk(data, 0xbb20, 160)

