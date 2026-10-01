#!/usr/bin/env python3
import os
import sys

def scan_dir(base_dir):
    records = []
    for root, dirs, files in os.walk(base_dir):
        # Exclude tools directory and hidden directories/files
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'tools']
        for f in sorted(files):
            if f.startswith('.'):
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, base_dir)
            size = os.path.getsize(full_path)
            
            # Read first 16 bytes
            try:
                with open(full_path, 'rb') as fp:
                    header = fp.read(16)
                magic_hex = header.hex()
                magic_ascii = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in header)
            except Exception as e:
                magic_hex = f"ERR: {e}"
                magic_ascii = ""

            records.append({
                'path': rel_path,
                'name': f,
                'ext': os.path.splitext(f)[1].upper(),
                'size': size,
                'magic_hex': magic_hex,
                'magic_ascii': magic_ascii
            })
    return sorted(records, key=lambda x: x['path'])

if __name__ == '__main__':
    base_dir = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')
    results = scan_dir(base_dir)
    print(f"{'Relative Path':<50} | {'Size (Bytes)':<12} | {'Ext':<6} | {'Magic (Hex)':<34} | {'Magic (ASCII)'}")
    print("-" * 125)
    for r in results:
        print(f"{r['path']:<50} | {r['size']:<12} | {r['ext']:<6} | {r['magic_hex']:<34} | {r['magic_ascii']}")
