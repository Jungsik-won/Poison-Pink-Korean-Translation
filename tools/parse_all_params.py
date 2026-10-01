#!/usr/bin/env python3
import struct
import json
from extract_file import extract_archive_file

data = extract_archive_file('Poison Pink (Japan)/DATA/STATUS', 'PPPARAM.dat')
total_entries = struct.unpack('<H', data[:2])[0]

# Sequentially parse all records
records = []
pos = 2

for i in range(1, total_entries + 1):
    # The record starts with uint16 ID == i
    # Let's search forward for struct.pack('<H', i)
    # The name follows uint16 serial (at pos+4)
    found = -1
    for p in range(pos, min(pos + 120, len(data) - 4)):
        cand_id = struct.unpack('<H', data[p:p+2])[0]
        if cand_id == i:
            # check if data[p+4] is start of string (printable Shift-JIS or Katakana)
            b = data[p+4]
            if (0x81 <= b <= 0x9f or 0xe0 <= b <= 0xef or 0x41 <= b <= 0x7a):
                found = p
                break
    if found == -1:
        # Wider search
        for p in range(pos, len(data) - 4):
            cand_id = struct.unpack('<H', data[p:p+2])[0]
            if cand_id == i:
                b = data[p+4]
                if (0x81 <= b <= 0x9f or 0xe0 <= b <= 0xef or 0x41 <= b <= 0x7a):
                    found = p
                    break
    if found != -1:
        unit_id, model_id = struct.unpack('<HH', data[found:found+4])
        # Name
        n_end = found + 4
        while n_end < len(data) and data[n_end] != 0:
            n_end += 1
        name = data[found+4:n_end].decode('cp932', errors='replace')
        records.append({
            'id': unit_id,
            'model_id': model_id,
            'offset': found,
            'name': name
        })
        pos = n_end + 1
    else:
        print(f"Warning: could not locate unit {i}")

print(f"Successfully parsed {len(records)} of {total_entries} units!")
out_file = 'tools/all_characters_and_monsters.json'
with open(out_file, 'w', encoding='utf-8') as fp:
    json.dump(records, fp, ensure_ascii=False, indent=2)
print(f"Saved to {out_file}")

# Print sample
for r in records[:15]:
    print(f"[{r['id']:3d}] (model {r['model_id']:4d}): {r['name']}")
print("...")
for r in records[-15:]:
    print(f"[{r['id']:3d}] (model {r['model_id']:4d}): {r['name']}")
