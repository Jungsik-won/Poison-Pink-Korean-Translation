#!/usr/bin/env python3
"""
Poison Pink (PS2) - Movie Extractor & Remuxer with 16KB Interleaved Stereo Sound
Reverse engineered from SLPS_258.54 and MOVIE.DAT.

Audio Specification:
- Codec: Sony SPU2 VAG ADPCM
- Channel Layout: Stereo (2 Channels)
- Interleave Block Size: 16,384 bytes (0x4000, 8 DVD sectors) per channel
  [16KB Left Channel] [16KB Right Channel] [16KB Left Channel] [16KB Right Channel] ...
- Sample Rate: 44,100 Hz
- Samples per 16-byte block: 28 samples (low-nibble first)
- Video: Sony IPU 640x448 @ 29.97 fps (NTSC)
"""

import os
import sys
import struct
import wave
import subprocess

# Standard Sony VAG ADPCM filter coefficients
VAG_COEFFS = [
    [0.0, 0.0],
    [60.0 / 64.0, 0.0],
    [115.0 / 64.0, -52.0 / 64.0],
    [98.0 / 64.0, -55.0 / 64.0],
    [122.0 / 64.0, -60.0 / 64.0]
]

INTERLEAVE_BYTES = 16384  # 0x4000 = 16 KB per channel
STRIDE_BYTES = INTERLEAVE_BYTES * 2  # 32,768 bytes (0x8000)

def decode_block(block, hist):
    """Decodes a single 16-byte Sony SPU2 VAG ADPCM block into 28 PCM samples."""
    shift = block[0] & 0x0f
    filt = (block[0] >> 4) & 0x07
    if filt > 4:
        filt = 0
    k0, k1 = VAG_COEFFS[filt]
    
    samples = []
    s1, s2 = hist[0], hist[1]
    
    # 14 payload bytes -> 28 4-bit nibbles (low nibble first)
    for b in block[2:16]:
        for nib in (b & 0x0f, (b >> 4) & 0x0f):
            if nib >= 8:
                nib -= 16
            sample = (nib << (12 - shift)) + s1 * k0 + s2 * k1
            s2 = s1
            s1 = sample
            # Clamp to 16-bit signed integer
            samples.append(max(-32768, min(32767, int(sample))))
            
    hist[0], hist[1] = s1, s2
    return samples

def ag_to_wav(ag_path, wav_path, sample_rate=44100):
    """Decodes a 16KB interleaved .ag file into standard 16-bit stereo WAV."""
    with open(ag_path, 'rb') as fp:
        data = fp.read()
        
    num_strides = len(data) // STRIDE_BYTES
    hist_l = [0.0, 0.0]
    hist_r = [0.0, 0.0]
    
    stereo_pcm = bytearray()
    
    for s in range(num_strides):
        l_chunk = data[s * STRIDE_BYTES : s * STRIDE_BYTES + INTERLEAVE_BYTES]
        r_chunk = data[s * STRIDE_BYTES + INTERLEAVE_BYTES : (s + 1) * STRIDE_BYTES]
        
        l_samp = []
        r_samp = []
        for b in range(0, INTERLEAVE_BYTES, 16):
            l_samp.extend(decode_block(l_chunk[b : b + 16], hist_l))
            r_samp.extend(decode_block(r_chunk[b : b + 16], hist_r))
            
        for l, r in zip(l_samp, r_samp):
            stereo_pcm.extend(struct.pack('<hh', l, r))
            
    # Write output stereo WAV
    with wave.open(wav_path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(stereo_pcm)

def main():
    out_dir = 'extracted_movies'
    os.makedirs(out_dir, exist_ok=True)
    raw_base = 'extracted/original/raw/MOVIE/movie'
    
    print("=================================================================")
    print(" Poison Pink Cutscene Extraction & True Stereo Remuxing (16KB IL)")
    print("=================================================================")
    
    for i in range(1, 16):
        tag = f"s{i:02d}"
        ipu_src = os.path.join(raw_base, tag, f"{tag}.ipu")
        ag_src = os.path.join(raw_base, tag, f"{tag}.ag")
        
        ipu_dst = os.path.join(out_dir, f"{tag}.ipu")
        ag_dst = os.path.join(out_dir, f"{tag}.ag")
        wav_dst = os.path.join(out_dir, f"{tag}.wav")
        mp4_dst = os.path.join(out_dir, f"{tag}.mp4")
        tmp_mp4 = os.path.join(out_dir, f"{tag}_tmp.mp4")
        
        if not os.path.exists(ipu_src) or not os.path.exists(ag_src):
            print(f"[{tag}] Error: source files not found in {raw_base}/{tag}!")
            continue
            
        # Ensure raw .ipu and .ag are in extracted_movies/
        if not os.path.exists(ipu_dst) or os.path.getsize(ipu_dst) != os.path.getsize(ipu_src):
            import shutil
            shutil.copy2(ipu_src, ipu_dst)
        if not os.path.exists(ag_dst) or os.path.getsize(ag_dst) != os.path.getsize(ag_src):
            import shutil
            shutil.copy2(ag_src, ag_dst)
            
        print(f"\n[{tag}] Step 1/2: Decoding 16KB-interleaved stereo audio...")
        ag_to_wav(ag_dst, wav_dst, 44100)
        
        print(f"[{tag}] Step 2/2: Muxing 29.97fps IPU video and stereo audio to MP4...")
        cmd = [
            'ffmpeg', '-y',
            '-r', '29.97',
            '-i', ipu_dst,
            '-i', wav_dst,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '18',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-shortest',
            tmp_mp4
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if res.returncode == 0:
            os.replace(tmp_mp4, mp4_dst)
            size_mb = os.path.getsize(mp4_dst) / (1024 * 1024)
            print(f"[{tag}] SUCCESS -> {mp4_dst} ({size_mb:.2f} MB)")
        else:
            print(f"[{tag}] FFMPEG Error: {res.stderr.decode('utf-8', errors='replace')[-200:]}")
            
        if os.path.exists(wav_dst):
            os.remove(wav_dst)
            
    print("\n[Done] All 15 cutscenes extracted and remuxed with TRUE stereo sound!")

if __name__ == '__main__':
    main()
