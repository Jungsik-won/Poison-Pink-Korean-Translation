#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from hed_parser import parse_hed_file

def main():
    hed_files = sorted([f for f in os.listdir('Poison Pink (Japan)/DATA') if f.endswith('.HED')])
    for h in hed_files:
        path = os.path.join('Poison Pink (Japan)/DATA', h)
        dat_path = path.replace('.HED', '.DAT')
        dat_size = os.path.getsize(dat_path) if os.path.exists(dat_path) else 0
        entries = parse_hed_file(path)
        
        file_entries = [e for e in entries if e['size'] > 0 and e['name'] not in ('..', '--DirEnd--')]
        
        exts = {}
        for e in file_entries:
            ext = os.path.splitext(e['name'])[1].lower()
            exts[ext] = exts.get(ext, 0) + 1
            
        print(f"Archive: {h:<12} | DAT Size: {dat_size:10d} | Total Entries: {len(entries):5d} | Files: {len(file_entries):5d}")
        print(f"  Extensions: {sorted(exts.items(), key=lambda x: -x[1])}")
        
if __name__ == '__main__':
    main()
