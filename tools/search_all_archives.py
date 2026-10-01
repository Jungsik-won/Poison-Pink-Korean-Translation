#!/usr/bin/env python3
import os
import sys
import struct
import re
from hed_parser import parse_hed_file

# Japanese unicode ranges
HIRAGANA_KATAKANA = re.compile(r'[\u3041-\u3096\u30a1-\u30fa]')

def extract_valid_jp_strings(data, min_chars=3):
    # Scan raw bytes for Shift-JIS strings that have Japanese kana/kanji
    results = []
    i = 0
    n = len(data)
    while i < n:
        b = data[i]
        # Check Shift-JIS lead byte
        if (0x81 <= b <= 0x9f or 0xe0 <= b <= 0xef) and i + 1 < n:
            # Possible SJIS
            start = i
            valid = True
            while i < n:
                b1 = data[i]
                if (0x81 <= b1 <= 0x9f or 0xe0 <= b1 <= 0xef) and i + 1 < n:
                    b2 = data[i+1]
                    if (0x40 <= b2 <= 0x7e or 0x80 <= b2 <= 0xfc) and b2 != 0x7f:
                        i += 2
                        continue
                # ASCII printable allowed inside strings (space, punctuation, alnum)
                elif 0x20 <= b1 <= 0x7e or b1 in (0x0a, 0x0d, 0x09):
                    i += 1
                    continue
                break
            chunk = data[start:i]
            if len(chunk) >= min_chars:
                try:
                    text = chunk.decode('cp932')
                    # Count Hiragana / Katakana characters to eliminate binary noise
                    kana_count = len(HIRAGANA_KATAKANA.findall(text))
                    if kana_count >= 2: # At least 2 kana ensures natural Japanese text
                        results.append((start, text.strip()))
                except:
                    pass
            continue
        i += 1
    return results

def main():
    hed_files = sorted([f for f in os.listdir('Poison Pink (Japan)/DATA') if f.endswith('.HED')])
    total_findings = []
    
    for h in hed_files:
        archive_name = h[:-4]
        hed_path = os.path.join('Poison Pink (Japan)/DATA', h)
        dat_path = os.path.join('Poison Pink (Japan)/DATA', archive_name + '.DAT')
        if not os.path.exists(dat_path):
            continue
        entries = parse_hed_file(hed_path)
        
        with open(dat_path, 'rb') as dat_fp:
            for e in entries:
                if e['size'] == 0 or e['name'] in ('..', '--DirEnd--'):
                    continue
                dat_fp.seek(e['offset'])
                data = dat_fp.read(e['size'])
                jp_strs = extract_valid_jp_strings(data)
                if jp_strs:
                    total_findings.append({
                        'archive': archive_name,
                        'file': e['name'],
                        'size': e['size'],
                        'count': len(jp_strs),
                        'samples': [s[1] for s in jp_strs[:5]]
                    })
                    
    total_findings.sort(key=lambda x: -x['count'])
    print(f"Total files with natural Japanese text: {len(total_findings)}\n")
    print(f"{'Archive':<10} | {'Filename':<20} | {'Size':<8} | {'JP Strings':<10} | Samples")
    print("-" * 100)
    for f in total_findings[:50]:
        sample_str = " // ".join(f['samples'][:2]).replace('\n', ' ')
        if len(sample_str) > 50:
            sample_str = sample_str[:47] + "..."
        print(f"{f['archive']:<10} | {f['file']:<20} | {f['size']:<8} | {f['count']:<10} | {sample_str}")

if __name__ == '__main__':
    main()
