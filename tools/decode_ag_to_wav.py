#!/usr/bin/env python3
import sys
import os
import struct
import wave

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

def ag_to_wav(ag_path, wav_path, sample_rate=44100):
    with open(ag_path, 'rb') as fp:
        data = fp.read()
        
    hist_l = [0.0, 0.0]
    hist_r = [0.0, 0.0]
    
    # 16 bytes L, 16 bytes R
    stereo_pcm = bytearray()
    num_pairs = len(data) // 32
    
    for i in range(num_pairs):
        l_block = data[i*32 : i*32 + 16]
        r_block = data[i*32 + 16 : (i+1)*32]
        
        l_samp = decode_block(l_block, hist_l)
        r_samp = decode_block(r_block, hist_r)
        
        for l, r in zip(l_samp, r_samp):
            stereo_pcm.extend(struct.pack('<hh', l, r))
            
    with wave.open(wav_path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(stereo_pcm)
        
    print(f"Decoded {ag_path} -> {wav_path} ({len(stereo_pcm)/(44100*4):.2f}s)")

if __name__ == '__main__':
    ag_path = sys.argv[1] if len(sys.argv) > 1 else 'extracted_movies/s01.ag'
    wav_path = sys.argv[2] if len(sys.argv) > 2 else ag_path.replace('.ag', '.wav')
    ag_to_wav(ag_path, wav_path, 44100)
