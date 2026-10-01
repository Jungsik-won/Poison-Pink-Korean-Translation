#!/usr/bin/env python3
import os
import sys
import re
import struct

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from hed_parser import parse_hed_file

# Hiragana / Katakana regex in UTF-8:
# Hiragana: \u3041-\u3096 -> E3 81 81 - E3 82 96
# Katakana: \u30a1-\u30fa -> E3 82 A1 - E3 83 BA
KANA_RE = re.compile(r'[\u3041-\u3096\u30a1-\u30fa]')

# Compiled regex for candidate Shift-JIS string sequences (at least 2 SJIS chars or SJIS mixed with ASCII)
SJIS_SEQ_RE = re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]|[\x20-\x7e\n\r\t]){4,}')

def scan_buffer(data):
    results = []
    for m in SJIS_SEQ_RE.finditer(data):
        raw = m.group()
        # Must contain at least one SJIS lead byte
        if not any((0x81 <= b <= 0x9f or 0xe0 <= b <= 0xef) for b in raw):
            continue
        try:
            text = raw.decode('cp932')
            kanas = KANA_RE.findall(text)
            if len(kanas) >= 2:
                # Clean up text
                clean = text.strip()
                if len(clean) >= 2:
                    results.append((m.start(), clean))
        except:
            continue
    return results

def main():
    base_dir = 'Poison Pink (Japan)/DATA'
    hed_files = sorted([f for f in os.listdir(base_dir) if f.endswith('.HED')])
    
    all_results = []
    for h in hed_files:
        archive_name = h[:-4]
        hed_path = os.path.join(base_dir, h)
        dat_path = os.path.join(base_dir, archive_name + '.DAT')
        if not os.path.exists(dat_path):
            continue
            
        entries = parse_hed_file(hed_path)
        with open(dat_path, 'rb') as fp:
            for e in entries:
                if e['size'] == 0 or e['name'] in ('..', '--DirEnd--'):
                    continue
                # Skip massive pure video/sound if we want fast scan
                if archive_name in ('MOVIE', 'SOUND') and not e['name'].endswith(('.txt', '.dat')):
                    continue
                fp.seek(e['offset'])
                data = fp.read(e['size'])
                matches = scan_buffer(data)
                if matches:
                    all_results.append({
                        'archive': archive_name,
                        'name': e['name'],
                        'size': e['size'],
                        'count': len(matches),
                        'samples': [m[1] for m in matches[:5]]
                    })
                    
    all_results.sort(key=lambda x: -x['count'])
    print(f"Total files with natural Japanese text: {len(all_results)}\n")
    print(f"{'Archive':<10} | {'Filename':<22} | {'Size':<8} | {'Matches':<7} | Sample")
    print("-" * 110)
    for r in all_results[:40]:
        s = " // ".join(r['samples'][:2]).replace('\n', ' ')
        if len(s) > 60:
            s = s[:57] + "..."
        print(f"{r['archive']:<10} | {r['name']:<22} | {r['size']:<8} | {r['count']:<7} | {s}")

if __name__ == '__main__':
    main()
