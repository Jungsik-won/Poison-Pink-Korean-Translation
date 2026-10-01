#!/usr/bin/env python3
import struct
from extract_file import extract_archive_file

data = extract_archive_file('Poison Pink (Japan)/DATA/STATUS', 'PPITEM.dat')
total_items = struct.unpack('<H', data[:2])[0]

pos = 2
parsed_items = []
for i in range(total_items):
    start_pos = pos
    if pos + 4 >= len(data):
        break
    cat_id = struct.unpack('<H', data[pos:pos+2])[0]
    item_id = struct.unpack('<H', data[pos+2:pos+4])[0]
    pos += 4
    
    # Read name until null terminator
    name_bytes = bytearray()
    while pos < len(data) and data[pos] != 0:
        name_bytes.append(data[pos])
        pos += 1
    # Skip null terminators (padding to 2 or 4 bytes, or 4 zeros)
    while pos < len(data) and data[pos] == 0:
        pos += 1
        
    try:
        name = name_bytes.decode('cp932')
    except:
        name = repr(name_bytes)
        
    # Read stats block: let's see how long the stats block is
    # Let's inspect next few bytes
    parsed_items.append({
        'index': i,
        'start_pos': start_pos,
        'cat_id': cat_id,
        'item_id': item_id,
        'name': name
    })
    # If we know the stats block length, we advance pos
    break

# Let's test finding items by scanning for (cat_id, item_id)
print(f"Total declared items: {total_items}")
print(f"Item 0: {parsed_items[0]}")
