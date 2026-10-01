#!/usr/bin/env python3
import os
import sys
import subprocess
from hed_parser import parse_hed_file

def main():
    hed_path = 'Poison Pink (Japan)/DATA/MOVIE.HED'
    dat_path = 'Poison Pink (Japan)/DATA/MOVIE.DAT'
    out_dir = 'extracted_movies'
    os.makedirs(out_dir, exist_ok=True)
    
    entries = parse_hed_file(hed_path)
    # Find all .ipu and .ag files
    targets = [e for e in entries if e['size'] > 0 and (e['name'].endswith('.ipu') or e['name'].endswith('.ag'))]
    print(f"Found {len(targets)} movie asset files ({len([t for t in targets if t['name'].endswith('.ipu')])} videos, {len([t for t in targets if t['name'].endswith('.ag')])} audio).")
    
    with open(dat_path, 'rb') as fp:
        for t in targets:
            name = t['name']
            out_path = os.path.join(out_dir, name)
            # Only extract if not already extracted or size differs
            if not os.path.exists(out_path) or os.path.getsize(out_path) != t['size']:
                print(f"Extracting {name} ({t['size']/(1024*1024):.2f} MB)...")
                fp.seek(t['offset'])
                data = fp.read(t['size'])
                with open(out_path, 'wb') as out_f:
                    out_f.write(data)
            else:
                print(f"{name} already extracted ({t['size']/(1024*1024):.2f} MB).")
                
    # Now convert all .ipu files to .mp4 using ffmpeg
    ipu_files = sorted([f for f in os.listdir(out_dir) if f.endswith('.ipu')])
    print(f"\nConverting {len(ipu_files)} IPU video files to MP4 (H.264)...")
    
    for ipu in ipu_files:
        ipu_path = os.path.join(out_dir, ipu)
        mp4_name = ipu.replace('.ipu', '.mp4')
        mp4_path = os.path.join(out_dir, mp4_name)
        
        if os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 0:
            print(f"  {mp4_name} already exists ({os.path.getsize(mp4_path)/(1024*1024):.2f} MB).")
            continue
            
        print(f"  Converting {ipu} -> {mp4_name}...")
        cmd = [
            'ffmpeg', '-y',
            '-i', ipu_path,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '18',
            '-pix_fmt', 'yuv420p',
            mp4_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if res.returncode == 0:
            print(f"    Done: {mp4_name} ({os.path.getsize(mp4_path)/(1024*1024):.2f} MB)")
        else:
            print(f"    Error converting {ipu}: {res.stderr.decode('utf-8', errors='replace')[-200:]}")

    print("\nAll movie extractions and MP4 conversions complete!")

if __name__ == '__main__':
    main()
