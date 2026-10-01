#!/usr/bin/env python3
import os
import sys
import struct

from extract_file import extract_archive_file

def parse_rtb_text_opcodes(data):
    # Pattern: 33 01 7c f0 c1 [LEN] [TEXT]
    # Let's search for b'\x33\x01\x7c\xf0\xc1'
    marker = b'\x33\x01\x7c\xf0\xc1'
    pos = 0
    strings = []
    while True:
        idx = data.find(marker, pos)
        if idx == -1:
            break
        len_pos = idx + len(marker)
        if len_pos < len(data):
            str_len = data[len_pos]
            text_bytes = data[len_pos+1 : len_pos+1+str_len]
            try:
                decoded = text_bytes.decode('cp932')
                strings.append({
                    'offset': idx,
                    'len': str_len,
                    'text': decoded,
                    'raw': text_bytes
                })
            except Exception as e:
                strings.append({
                    'offset': idx,
                    'len': str_len,
                    'text': f"[DECODE ERR: {e}]",
                    'raw': text_bytes
                })
        pos = idx + 1
    return strings

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 't00_0010.rtb'
    data = extract_archive_file('Poison Pink (Japan)/DATA/DMAP', target)
    strings = parse_rtb_text_opcodes(data)
    print(f"File {target}: Extracted {len(strings)} strings via opcode 0x33 0x01 0x7c 0xf0 0xc1")
    for s in strings[:30]:
        t = s['text'].replace('\n', '\\n')
        print(f"  [0x{s['offset']:05x}] (len {s['len']:3d}): {t}")
