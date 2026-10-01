#!/usr/bin/env python3
import struct

f = [
    [0.0, 0.0],
    [60.0 / 64.0, 0.0],
    [115.0 / 64.0, -52.0 / 64.0],
    [98.0 / 64.0, -55.0 / 64.0],
    [122.0 / 64.0, -60.0 / 64.0]
]

def decode_block(block, hist):
    shift = block[0] & 0x0f
    filt = (block[0] >> 4) & 0x07
    if filt > 4:
        filt = 0
    k0, k1 = f[filt]
    samples = []
    s1, s2 = hist[0], hist[1]
    for b in block[2:16]:
        for nib in (b & 0x0f, (b >> 4) & 0x0f):
            if nib >= 8:
                nib -= 16
            sample = (nib << (12 - shift)) + s1 * k0 + s2 * k1
            s2 = s1
            s1 = sample
            samples.append(max(-32768, min(32767, int(sample))))
    hist[0], hist[1] = s1, s2
    return samples

def test_config(interleave):
    with open('extracted_movies/s01.ag', 'rb') as fp:
        # Read 128KB of active sound (e.g. from 0x10000)
        fp.seek(0x20000)
        data = fp.read(interleave * 16)
        
    l_blocks = bytearray()
    r_blocks = bytearray()
    step = interleave * 2
    for pos in range(0, len(data), step):
        l_blocks.extend(data[pos : pos + interleave])
        r_blocks.extend(data[pos + interleave : pos + step])
        
    hist_l = [0.0, 0.0]
    l_samples = []
    for i in range(0, len(l_blocks), 16):
        l_samples.extend(decode_block(l_blocks[i:i+16], hist_l))
        
    # Check smoothness
    if len(l_samples) < 2:
        return 999999
    diff = sum(abs(l_samples[i+1] - l_samples[i]) for i in range(len(l_samples)-1)) / len(l_samples)
    # Check clip count (overflows)
    clips = sum(1 for s in l_samples if abs(s) >= 32760)
    print(f"Interleave 0x{interleave:04x}: avg_diff={diff:6.1f} | clips={clips:5d}")
    return diff

for ilv in [0x10, 0x20, 0x40, 0x80, 0x100, 0x200, 0x400, 0x800, 0x1000, 0x2000]:
    test_config(ilv)
