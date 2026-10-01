#!/usr/bin/env python3
import re
from extract_file import extract_archive_file

kantable_h = extract_archive_file('Poison Pink (Japan)/DATA/SYSTEM', 'kantable.h').decode('latin1')
numbers = [int(x.strip()) for x in re.findall(r'-?\d+', kantable_h)]

print(f"Total entries in KanTable: {len(numbers)}")
# Let's find what Shift-JIS / index maps to glyph 50
for idx, glyph_id in enumerate(numbers):
    if glyph_id == 50:
        print(f"Glyph 50 is at KanTable index {idx} (0x{idx:04x})")
        # How does KanTable index map to Shift-JIS or JIS?
        # Let's check how indices are structured!
        break

# Let's print the first 30 entries of KanTable
for i in range(30):
    print(f"Index {i:2d} (0x{i:02x}): glyph {numbers[i]}")
