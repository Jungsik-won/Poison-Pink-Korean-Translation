#!/usr/bin/env python3
import sys
import re

# Japanese characters in unicode:
# Hiragana: \u3040-\u309f
# Katakana: \u30a0-\u30ff
# CJK Unified Ideographs: \u4e00-\u9faf
# Fullwidth punctuation/symbols: \u3000-\u303f, \uff00-\uffef

JP_CHAR_RE = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9faf]')

def is_meaningful_japanese(text, min_jp_chars=2):
    jp_chars = JP_CHAR_RE.findall(text)
    if len(jp_chars) < min_jp_chars:
        return False
    # If ratio of jp_chars or ascii printable is high compared to weird symbols
    # Also ensure there are hiragana/katakana or known common kanji
    return True

def scan_file_japanese_sjis(data, min_len=4):
    # Match sequences of bytes that can decode as CP932
    # To avoid random binary noise, look for sequences of at least 2 multibyte characters
    # or mixed ASCII + multibyte
    results = []
    i = 0
    n = len(data)
    while i < n:
        # Check if byte starts a valid CP932 character
        b = data[i]
        if (0x81 <= b <= 0x9f or 0xe0 <= b <= 0xfc) and i + 1 < n:
            b2 = data[i+1]
            if (0x40 <= b2 <= 0x7e or 0x80 <= b2 <= 0xfc) and b2 != 0x7f:
                # Potential start of SJIS string
                start = i
                while i < n:
                    b = data[i]
                    if (0x81 <= b <= 0x9f or 0xe0 <= b <= 0xfc) and i + 1 < n:
                        b2 = data[i+1]
                        if (0x40 <= b2 <= 0x7e or 0x80 <= b2 <= 0xfc) and b2 != 0x7f:
                            i += 2
                            continue
                    elif 0x20 <= b <= 0x7e or b in (0x0a, 0x0d, 0x09):
                        i += 1
                        continue
                    break
                chunk = data[start:i]
                try:
                    decoded = chunk.decode('cp932')
                    if is_meaningful_japanese(decoded):
                        results.append((start, decoded.strip()))
                except:
                    pass
                continue
        i += 1
    return results

if __name__ == '__main__':
    with open('Poison Pink (Japan)/SLPS_258.54', 'rb') as f:
        data = f.read()
    jp_strings = scan_file_japanese_sjis(data)
    print(f"SLPS_258.54 meaningful Japanese strings: {len(jp_strings)}")
    for off, s in jp_strings[:30]:
        print(f"  0x{off:08x}: {s}")
