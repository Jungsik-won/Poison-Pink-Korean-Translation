#!/usr/bin/env python3
import os
import sys
import struct
from datetime import datetime

ENTRY_SIZE = 44

def parse_hed_file(hed_path):
    with open(hed_path, 'rb') as f:
        data = f.read()
    
    num_entries = len(data) // ENTRY_SIZE
    entries = []
    
    for i in range(num_entries):
        chunk = data[i*ENTRY_SIZE:(i+1)*ENTRY_SIZE]
        offset, size = struct.unpack('<II', chunk[:8])
        raw_name = chunk[8:40]
        # Null-terminated name
        name = raw_name.split(b'\x00')[0].decode('latin1', errors='replace')
        timestamp = struct.unpack('<I', chunk[40:44])[0]
        
        entries.append({
            'index': i,
            'offset': offset,
            'size': size,
            'name': name,
            'timestamp': timestamp,
            'raw': chunk
        })
    return entries

def print_hed_summary(hed_path):
    entries = parse_hed_file(hed_path)
    print(f"=== {os.path.basename(hed_path)}: {len(entries)} entries ===")
    for e in entries[:25]:
        dt = ""
        if 0x30000000 <= e['timestamp'] <= 0x60000000:
            try:
                dt = datetime.utcfromtimestamp(e['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            except:
                dt = hex(e['timestamp'])
        else:
            dt = hex(e['timestamp'])
        print(f"[{e['index']:4d}] Offset: 0x{e['offset']:08x} ({e['offset']:10d}) | Size: {e['size']:8d} | {e['name']:<24} | {dt}")
    if len(entries) > 25:
        print(f"... and {len(entries) - 25} more entries.")

if __name__ == '__main__':
    hed_files = sorted([f for f in os.listdir('Poison Pink (Japan)/DATA') if f.endswith('.HED')])
    for h in hed_files:
        print_hed_summary(os.path.join('Poison Pink (Japan)/DATA', h))
        print()
