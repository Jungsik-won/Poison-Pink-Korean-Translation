#!/usr/bin/env python3
import sys
from extract_file import extract_archive_file

kanji_data = extract_archive_file('Poison Pink (Japan)/DATA/SYSTEM', 'kanji.dat')
print(f"kanji_data length: {len(kanji_data)}")

# Glyph 0
glyph0 = kanji_data[:144]
print("Glyph 0 hex:", glyph0[:32].hex())

# Let's test 24x24 at 2bpp: 24 * 24 * 2 / 8 = 144 bytes!
# Exactly 144 bytes! 24 pixels wide, 24 pixels tall, 2 bits per pixel!
print("\nTesting 24x24 @ 2bpp for Glyph 0:")
chars = [' ', '.', 'o', '#']
for y in range(24):
    row_bytes = glyph0[y*6 : (y+1)*6] # 24 pixels * 2 bits = 48 bits = 6 bytes
    line = ""
    for b in row_bytes:
        # Try MSB first
        p0 = (b >> 6) & 3
        p1 = (b >> 4) & 3
        p2 = (b >> 2) & 3
        p3 = b & 3
        line += chars[p0] + chars[p1] + chars[p2] + chars[p3]
    print(line)

print("\nTesting Glyph 1:")
glyph1 = kanji_data[144:288]
for y in range(24):
    row_bytes = glyph1[y*6 : (y+1)*6]
    line = ""
    for b in row_bytes:
        p0 = (b >> 6) & 3
        p1 = (b >> 4) & 3
        p2 = (b >> 2) & 3
        p3 = b & 3
        line += chars[p0] + chars[p1] + chars[p2] + chars[p3]
    print(line)

