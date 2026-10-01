#!/usr/bin/env python3
import struct
import json
from extract_file import extract_archive_file

data = extract_archive_file('Poison Pink (Japan)/DATA/STATUS', 'PPPARAM.dat')
total_entries = struct.unpack('<H', data[:2])[0]
print(f"Total entries declared: {total_entries}")

# Each entry has ID: 1, 2, 3, ...
pos = 2
params = []

for target_id in range(1, total_entries + 1):
    # Find position of target_id
    # Search forward within a small window
    found_pos = -1
    for p in range(pos, min(pos + 200, len(data) - 4)):
        cand_id, cand_len = struct.unpack('<HH', data[p:p+4])
        if cand_id == target_id and 4 <= cand_len <= 48:
            # Check if bytes look like CP932 name
            name_bytes = data[p+4:p+4+cand_len].split(b'\x00')[0]
            try:
                name = name_bytes.decode('cp932')
                found_pos = p
                break
            except:
                pass
    if found_pos == -1:
        # Fallback search anywhere forward
        for p in range(pos, len(data) - 4):
            cand_id, cand_len = struct.unpack('<HH', data[p:p+4])
            if cand_id == target_id and 4 <= cand_len <= 48:
                name_bytes = data[p+4:p+4+cand_len].split(b'\x00')[0]
                try:
                    name = name_bytes.decode('cp932')
                    found_pos = p
                    break
                except:
                    pass
    if found_pos != -1:
        p_id, n_len = struct.unpack('<HH', data[found_pos:found_pos+4])
        name_raw = data[found_pos+4 : found_pos+4+n_len].split(b'\x00')[0]
        name = name_raw.decode('cp932', errors='replace')
        params.append({
            'id': p_id,
            'offset': found_pos,
            'name_len': n_len,
            'name': name
        })
        pos = found_pos + 4 + n_len

print(f"Successfully located and parsed {len(params)} of {total_entries} parameters!")
out_file = 'tools/all_params.json'
with open(out_file, 'w', encoding='utf-8') as fp:
    json.dump(params, fp, ensure_ascii=False, indent=2)
print(f"Saved to {out_file}")

print("\n--- Sample Character / Monster Names ---")
for p in params[:20]:
    print(f"[{p['id']:3d}] (off 0x{p['offset']:04x}): {p['name']}")
print("...")
for p in params[-10:]:
    print(f"[{p['id']:3d}] (off 0x{p['offset']:04x}): {p['name']}")
