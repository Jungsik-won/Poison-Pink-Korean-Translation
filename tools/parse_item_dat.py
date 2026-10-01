#!/usr/bin/env python3
import struct
from extract_file import extract_archive_file

data = extract_archive_file('Poison Pink (Japan)/DATA/STATUS', 'PPITEM.dat')
print(f"PPITEM.dat total size: {len(data)}")

# Let's inspect the first 2 bytes
total_items = struct.unpack('<H', data[:2])[0]
print(f"Total items declared in header: {total_items}")

# Let's examine how entries are delimited
# In earlier dump:
# 0000: 96 00 (count: 150)
# Item 1 starts at 0x0002:
# 0002: 01 00 01 00
# 0006: 95 ba 8e 6d 82 cc 92 b7 8c 95 00 00 00 00 (兵士の長剣)
# Item 2 was at 0x002c:
# 002c: 01 00 02 00 01 00 92 b7 8c 95 00 00 00 00 (長剣)
# Notice: 0x002c - 0x0002 = 0x2a = 42 bytes? Or is 0x002c offset:
# Wait! Let's check the offsets of all items!

pos = 2
items = []
for i in range(total_items):
    if pos >= len(data):
        break
    # Let's see what is at pos:
    # Could each entry have a fixed size or variable size?
    # Let's look for null-terminated strings or fixed structures
    # Let's dump the next 48 bytes
    chunk = data[pos:pos+48]
    # Check if there is an id and string
    # Try to decode string starting at pos+4 or pos+6
    name_bytes = data[pos+6:pos+20].split(b'\x00')[0]
    name = name_bytes.decode('cp932', errors='replace')
    items.append((pos, name))
    # If fixed size: let's test sizes between 30 and 100
    # Let's look for the next item's ID or structure
    break

# Let's find all item names in the file to see their offsets
