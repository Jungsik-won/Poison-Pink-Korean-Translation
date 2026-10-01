import os
import sys
import struct
import wave
import numpy as np

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
    if filt > 4: filt = 0
    k0, k1 = f[filt]
    samples = []
    s1, s2 = hist[0], hist[1]
    for b in block[2:16]:
        for nib in (b & 0x0f, (b >> 4) & 0x0f):
            if nib >= 8: nib -= 16
            sample = (nib << (12 - shift)) + s1 * k0 + s2 * k1
            s2 = s1
            s1 = sample
            samples.append(max(-32768, min(32767, int(sample))))
    hist[0], hist[1] = s1, s2
    return samples

def test():
    ag_path = 'extracted/original/raw/MOVIE/movie/s01/s01.ag'
    with open(ag_path, 'rb') as fp:
        data = fp.read(512 * 1024)
        
    os.makedirs('test_audio', exist_ok=True)
    
    candidates = [
        ('il_16', 16),
        ('il_256', 256),
        ('il_512', 512),
        ('il_1024', 1024),
        ('il_2048', 2048),
        ('il_4096', 4096),
        ('il_8192', 8192),
        ('il_16384', 16384),
    ]
    
    for name, il in candidates:
        hist_l = [0.0, 0.0]
        hist_r = [0.0, 0.0]
        stride = il * 2
        num_strides = len(data) // stride
        
        pcm = bytearray()
        l_all = []
        r_all = []
        for s in range(num_strides):
            l_chunk = data[s*stride : s*stride + il]
            r_chunk = data[s*stride + il : (s+1)*stride]
            
            l_samples = []
            r_samples = []
            for b in range(0, il, 16):
                l_samples.extend(decode_block(l_chunk[b:b+16], hist_l))
                r_samples.extend(decode_block(r_chunk[b:b+16], hist_r))
                
            for l, r in zip(l_samples, r_samples):
                pcm.extend(struct.pack('<hh', l, r))
            l_all.extend(l_samples)
            r_all.extend(r_samples)
            
        wav_out = f'test_audio/{name}.wav'
        with wave.open(wav_out, 'wb') as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(44100)
            w.writeframes(pcm)
            
        l_arr = np.array(l_all, dtype=np.float64)
        r_arr = np.array(r_all, dtype=np.float64)
        spb = (il // 16) * 28
        num_b = len(l_arr) // spb
        l_jumps = []
        r_jumps = []
        for b_idx in range(1, num_b):
            idx = b_idx * spb
            l_jumps.append(abs(l_arr[idx] - l_arr[idx-1]))
            r_jumps.append(abs(r_arr[idx] - r_arr[idx-1]))
            
        boundary_jump = (np.mean(l_jumps) + np.mean(r_jumps)) / 2
        normal_jump = (np.mean(np.abs(np.diff(l_arr))) + np.mean(np.abs(np.diff(r_arr)))) / 2
        jump_ratio = boundary_jump / (normal_jump + 1e-6)
        print(f'{name:10s} (0x{il:04x}): boundary_jump={boundary_jump:7.2f}, normal_jump={normal_jump:7.2f}, jump_ratio={jump_ratio:6.2f}')

if __name__ == '__main__':
    test()
