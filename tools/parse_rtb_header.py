#!/usr/bin/env python3
import struct
from extract_file import extract_archive_file

data = extract_archive_file('Poison Pink (Japan)/DATA/DMAP', 't00_0010.rtb')

# Let's inspect the first 16 bytes:
# fe 17 03 6b fb 08 00 0b ...
print("Header:", data[:16].hex())

# Let's see how many symbols are parsed with:
# [tag/id] [length: 1 byte] [name]
pos = 0
# First 4 bytes?
magic, count = struct.unpack('<HH', data[:4])
print(f"magic=0x{magic:04x}, count=0x{count:04x} ({count})")

pos = 4
symbols = []
while pos < len(data):
    # Let's test if there is a 4-byte hash/id, 1-byte length, then string
    # If the byte at pos+4 looks like an ascii length (1..100) and following bytes are ASCII:
    if pos + 5 >= len(data):
        break
    # Let's check 4-byte id + 1-byte len
    uid = struct.unpack('<I', data[pos:pos+4])[0]
    slen = data[pos+4]
    if 1 <= slen <= 64 and pos + 5 + slen <= len(data):
        sbytes = data[pos+5 : pos+5+slen]
        # Check if ASCII identifier [a-zA-Z0-9_.]
        if all(32 <= b <= 126 for b in sbytes):
            sname = sbytes.decode('ascii')
            symbols.append((pos, uid, sname))
            pos += 5 + slen
            continue
    # If not matching, we reached the end of this table!
    break

print(f"Parsed {len(symbols)} symbols. Next table starts at offset 0x{pos:04x} ({pos})")
for p, uid, name in symbols[:15]:
    print(f"  0x{p:04x}: ID=0x{uid:08x} -> {name}")
print("...")
for p, uid, name in symbols[-5:]:
    print(f"  0x{p:04x}: ID=0x{uid:08x} -> {name}")

print(f"\nNext 64 bytes at 0x{pos:04x}:")
print(data[pos:pos+64].hex())
