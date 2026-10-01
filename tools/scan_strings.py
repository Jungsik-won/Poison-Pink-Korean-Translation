#!/usr/bin/env python3
import sys
import re

def extract_strings(data, min_len=4):
    # ASCII regex
    ascii_re = re.compile(rb'[\x20-\x7E]{' + str(min_len).encode() + rb',}')
    # Shift-JIS regex (roughly: 0x81-0x9F, 0xE0-0xFC followed by 0x40-0x7E, 0x80-0xFC, plus katakana 0xA1-0xDF)
    sjis_re = re.compile(rb'(?:[\x81-\x9f\xe0-\xfc][\x40-\x7e\x80-\xfc]|[\xa1-\xdf]){2,}')
    
    ascii_matches = []
    for m in ascii_re.finditer(data):
        ascii_matches.append((m.start(), m.group().decode('ascii', errors='replace')))
        
    sjis_matches = []
    for m in sjis_re.finditer(data):
        raw = m.group()
        try:
            decoded = raw.decode('cp932')
            sjis_matches.append((m.start(), decoded, raw))
        except:
            pass
            
    return ascii_matches, sjis_matches

if __name__ == '__main__':
    with open('Poison Pink (Japan)/SLPS_258.54', 'rb') as f:
        data = f.read()
    ascii_m, sjis_m = extract_strings(data, min_len=5)
    print(f"SLPS_258.54: ASCII strings count: {len(ascii_m)}, Shift-JIS strings count: {len(sjis_m)}")
    
    print("\nSample Shift-JIS strings in ELF:")
    for offset, text, raw in sjis_m[:30]:
        print(f"  0x{offset:08x}: {text}")
        
    print("\nSample build/source strings in ELF:")
    for offset, s in ascii_m:
        if any(keyword in s.lower() for keyword in ['flight', 'pink', 'banpresto', 'gcc', 'sony', 'version', '200', 'ps2']):
            print(f"  0x{offset:08x}: {s}")
