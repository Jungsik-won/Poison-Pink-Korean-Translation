#!/usr/bin/env python3
import struct
from extract_file import extract_archive_file

data = extract_archive_file('Poison Pink (Japan)/DATA/STATUS', 'PPITEM.dat')

# Let's inspect the first 256 bytes in detail
pos = 2
item_idx = 0
while pos < 300 and pos < len(data):
    # What are the fields?
    # 0002: 01 00 01 00
    # 0006: 95 ba 8e 6d 82 cc 92 b7 8c 95 00 00 00 00 (兵士の長剣)
    # Let's check where the string ends
    # It has null padding
    # Let's look at the bytes
    print(f"--- Item {item_idx} at offset 0x{pos:04x} ---")
    chunk = data[pos:pos+44]
    print("Hex:", chunk.hex())
    print("Raw:", chunk)
    # Check if there's a length or fixed record
    # Let's find where the next item starts
    # Search for next string or pattern
    # In earlier hex:
    # 0000: 9600
    # 0002: 0100 0100 95ba8e6d82cc92b78c9500000000 011e000000000000000000ecff010000
    # 0023: 2c01000200010092b78c95000000000328...
    # Wait! Look at 0x0023 or 0x002c!
    break
