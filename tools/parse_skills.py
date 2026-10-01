#!/usr/bin/env python3
import struct
import json
from extract_file import extract_archive_file

data = extract_archive_file('Poison Pink (Japan)/DATA/STATUS', 'PPSKILL.dat')
total_skills = struct.unpack('<H', data[:2])[0]

pos = 2
skills = []
for i in range(total_skills):
    if pos >= len(data):
        break
    s_id, unk1, cat = struct.unpack('<HHH', data[pos:pos+6])
    pos += 6
    
    # Read name
    n_start = pos
    while pos < len(data) and data[pos] != 0:
        pos += 1
    name = data[n_start:pos].decode('cp932', errors='replace')
    while pos < len(data) and data[pos] == 0:
        pos += 1
        
    # Stats: 66 bytes
    stats = data[pos:pos+66]
    pos += 66
    
    # Read description
    d_start = pos
    while pos < len(data) and data[pos] != 0:
        pos += 1
    desc = data[d_start:pos].decode('cp932', errors='replace')
    if pos < len(data) and data[pos] == 0:
        pos += 1
        
    skills.append({
        'id': s_id,
        'cat': cat,
        'name': name,
        'desc': desc
    })

print(f"Parsed {len(skills)} of {total_skills} skills successfully!")
out_file = 'tools/all_skills.json'
with open(out_file, 'w', encoding='utf-8') as fp:
    json.dump(skills, fp, ensure_ascii=False, indent=2)
print(f"Saved to {out_file}")

for s in skills[:8]:
    d = s['desc'].replace('\n', ' / ')
    print(f"[{s['id']:3d}] {s['name']:<16} | {d}")
