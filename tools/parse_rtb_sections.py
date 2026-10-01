#!/usr/bin/env python3
import struct
from extract_file import extract_archive_file

data = extract_archive_file('Poison Pink (Japan)/DATA/DMAP', 't00_0010.rtb')

pos = 0
magic = data[0]
num_symbols = struct.unpack('<H', data[1:3])[0]
pos = 3
symbols = {}
for i in range(num_symbols):
    uid = struct.unpack('<I', data[pos:pos+4])[0]
    slen = data[pos+4]
    sname = data[pos+5:pos+5+slen].decode('ascii', errors='replace')
    symbols[uid] = sname
    pos += 5 + slen

print(f"Section 1 (Symbol Table): {num_symbols} symbols, ends at 0x{pos:04x}")

# Section 2: Source files
num_files = data[pos]
pos += 1
files = []
for i in range(num_files):
    flen = data[pos]
    fname = data[pos+1:pos+1+flen].decode('ascii', errors='replace')
    files.append(fname)
    pos += 1 + flen
print(f"Section 2 (Source files): {len(files)} files, ends at 0x{pos:04x}")
for i, fn in enumerate(files):
    print(f"  [{i:2d}] {fn}")

# Section 3: Function / Export table?
num_funcs = data[pos]
pos += 1
print(f"\nSection 3 at 0x{pos-1:04x}: count={num_funcs}")
funcs = []
for i in range(num_funcs):
    f_hash, f_idx = struct.unpack('<II', data[pos:pos+8])
    sym_name = symbols.get(f_hash, f"Unknown_0x{f_hash:08x}")
    funcs.append((f_hash, f_idx, sym_name))
    pos += 8
for f_hash, f_idx, sym in funcs:
    print(f"  hash=0x{f_hash:08x} ({sym:<24}) -> val={f_idx}")

print(f"\nSection 4 starts at 0x{pos:04x}:")
print("Next 64 bytes:")
print(data[pos:pos+64].hex())

