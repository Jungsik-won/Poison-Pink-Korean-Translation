#!/usr/bin/env python3
import os
import struct
from extract_file import extract_archive_file
from hed_parser import parse_hed_file

def inspect_tim2(data, name):
    if len(data) < 48 or data[:4] != b'TIM2':
        return None
    # TIM2 format:
    # 0x00: 'TIM2'
    # 0x04: Format version (byte)
    # 0x05: Format ID (byte)
    # 0x06: Picture count (uint16)
    # Header size: 16 or 128
    ver, fmt_id, pic_cnt = struct.unpack('<BBH', data[4:8])
    # Picture header (starts at 0x10):
    total_sz, clut_sz, img_sz, hdr_sz, clut_colors, pic_fmt = struct.unpack('<IIIIHH', data[16:36])
    w, h = struct.unpack('<HH', data[36:40])
    bpp_mode = data[40] # GS tex0 format: 0=PSMCT32, 1=PSMCT24, 2=PSMCT16, 19=PSMT8, 20=PSMT4
    return {
        'name': name,
        'size': len(data),
        'w': w,
        'h': h,
        'clut_colors': clut_colors,
        'bpp_mode': bpp_mode
    }

def main():
    entries = parse_hed_file('Poison Pink (Japan)/DATA/STATUS.HED')
    tm2s = [e for e in entries if e['name'].endswith('.tm2')]
    print(f"Total TM2 textures in STATUS: {len(tm2s)}")
    
    with open('Poison Pink (Japan)/DATA/STATUS.DAT', 'rb') as fp:
        for e in tm2s:
            fp.seek(e['offset'])
            raw = fp.read(e['size'])
            info = inspect_tim2(raw, e['name'])
            if info:
                # Highlight UI text candidates (like sys*, title*, bplogo, etc.)
                if any(x in info['name'] for x in ['sys', 'title', 'logo', 'win', 'btn', 'ico', 'dic']):
                    print(f"  {info['name']:<18} | {info['w']:4d} x {info['h']:4d} | colors={info['clut_colors']:3d} | size={info['size']:7d}")

if __name__ == '__main__':
    main()
