#!/usr/bin/env python3
import struct
import zlib
import sys

def write_png(width, height, rgba_bytes):
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw.extend(rgba_bytes[y*width*4 : (y+1)*width*4])
    
    def chunk(tag, data):
        c = tag + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(raw), 6)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', idat) + chunk(b'IEND', b'')

def decode_tim2(data):
    if len(data) < 48 or data[:4] != b'TIM2':
        return None
    total_sz, clut_sz, img_sz = struct.unpack('<III', data[16:28])
    hdr_sz = struct.unpack('<H', data[28:30])[0]
    clut_colors = struct.unpack('<H', data[30:32])[0]
    w, h = struct.unpack('<HH', data[36:40])
    
    img_offset = 16 + hdr_sz
    clut_offset = img_offset + img_sz
    
    img_data = data[img_offset : img_offset + img_sz]
    clut_data = data[clut_offset : clut_offset + clut_sz]
    
    colors = []
    if clut_colors > 0:
        for i in range(clut_colors):
            r, g, b, a = struct.unpack('BBBB', clut_data[i*4 : (i+1)*4])
            a_scaled = min(255, a * 2) if a <= 128 else 255
            colors.append((r, g, b, a_scaled))
        
        # Deswizzle 8bpp CLUT (PS2 GS PSMT8)
        if clut_colors == 256:
            unswizzled = [None] * 256
            for i in range(0, 256, 32):
                for j in range(8):
                    unswizzled[i + j] = colors[i + j]
                    unswizzled[i + j + 8] = colors[i + j + 16]
                    unswizzled[i + j + 16] = colors[i + j + 8]
                    unswizzled[i + j + 24] = colors[i + j + 24]
            colors = unswizzled
            
    rgba = bytearray(w * h * 4)
    for i in range(min(w * h, len(img_data))):
        idx = img_data[i]
        c = colors[idx] if idx < len(colors) else (0, 0, 0, 0)
        rgba[i*4 : (i+1)*4] = struct.pack('BBBB', c[0], c[1], c[2], c[3])
        
    return w, h, bytes(rgba)

if __name__ == '__main__':
    from extract_file import extract_archive_file
    fname = sys.argv[1] if len(sys.argv) > 1 else 'sysicn.tm2'
    out_png = sys.argv[2] if len(sys.argv) > 2 else 'tools/' + fname.replace('.tm2', '.png')
    data = extract_archive_file('Poison Pink (Japan)/DATA/STATUS', fname)
    if data:
        w, h, rgba = decode_tim2(data)
        png = write_png(w, h, rgba)
        with open(out_png, 'wb') as fp:
            fp.write(png)
        print(f"Decoded {fname} ({w}x{h}) -> saved {len(png)} bytes to {out_png}")
