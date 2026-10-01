#!/usr/bin/env python3
import os
import sys
import struct

try:
    from tools.hed_parser import parse_hed_file
except ImportError:
    from hed_parser import parse_hed_file

def extract_archive_file(archive_base, target_filename, out_path=None):
    hed_path = archive_base + '.HED'
    dat_path = archive_base + '.DAT'
    if not os.path.exists(hed_path) or not os.path.exists(dat_path):
        print(f"Error: Archive {archive_base} not found.")
        return None
        
    entries = parse_hed_file(hed_path)
    matched = [e for e in entries if e['name'].lower() == target_filename.lower()]
    if not matched:
        print(f"File {target_filename} not found in {hed_path}")
        return None
        
    entry = matched[0]
    with open(dat_path, 'rb') as fp:
        fp.seek(entry['offset'])
        data = fp.read(entry['size'])
        
    if out_path:
        with open(out_path, 'wb') as fp:
            fp.write(data)
        print(f"Extracted {target_filename} ({len(data)} bytes) to {out_path}")
    return data

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: extract_file.py <ARCHIVE_BASE_WITHOUT_EXT> <FILENAME> [OUT_PATH]")
        sys.exit(1)
    arch = sys.argv[1]
    fname = sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else None
    data = extract_archive_file(arch, fname, out)
    if data and not out:
        print(f"Read {len(data)} bytes of {fname}")
        print("Hex:", data[:64].hex())
