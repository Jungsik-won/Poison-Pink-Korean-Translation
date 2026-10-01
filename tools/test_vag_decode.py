#!/usr/bin/env python3
import struct
import wave

# Sony PSX / PS2 SPU2 ADPCM coefficients
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
        # Low nibble then high nibble
        for nib in (b & 0x0f, (b >> 4) & 0x0f):
            # Sign extend 4-bit to signed integer (-8 .. 7)
            if nib >= 8:
                nib -= 16
            sample = (nib << (12 - shift)) + s1 * k0 + s2 * k1
            s2 = s1
            s1 = sample
            # Clamp to 16-bit
            clamped = max(-32768, min(32767, int(sample)))
            samples.append(clamped)
    hist[0], hist[1] = s1, s2
    return samples

def test_interleave(raw_path, interleave=0x800, sample_rate=44100):
    with open(raw_path, 'rb') as fp:
        data = fp.read()
    
    # De-interleave into L and R channels
    l_blocks = bytearray()
    r_blocks = bytearray()
    pos = 0
    step = interleave * 2
    while pos + step <= len(data):
        l_blocks.extend(data[pos : pos + interleave])
        r_blocks.extend(data[pos + interleave : pos + step])
        pos += step
        
    hist_l = [0.0, 0.0]
    hist_r = [0.0, 0.0]
    
    l_samples = []
    for i in range(0, len(l_blocks), 16):
        l_samples.extend(decode_block(l_blocks[i:i+16], hist_l))
        
    r_samples = []
    for i in range(0, len(r_blocks), 16):
        r_samples.extend(decode_block(r_blocks[i:i+16], hist_r))
        
    # Check max volume
    max_l = max(abs(s) for s in l_samples) if l_samples else 0
    max_r = max(abs(s) for s in r_samples) if r_samples else 0
    print(f"Interleave 0x{interleave:x}: L len={len(l_samples)}, max_L={max_l}, max_R={max_r}")
    
    out_wav = f"extracted_movies/test_{interleave:x}.wav"
    with wave.open(out_wav, 'wb') as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        # Interleave samples
        stereo = bytearray()
        for sl, sr in zip(l_samples, r_samples):
            stereo.extend(struct.pack('<hh', sl, sr))
        wav.writeframes(stereo)
    print(f"Saved {out_wav}")

test_interleave('extracted_movies/s01.ag', 0x800, 44100)
test_interleave('extracted_movies/s01.ag', 0x10, 44100)
