#!/usr/bin/env python3
import os
import sys
import json
import struct
from hed_parser import parse_hed_file

def extract_dialogue_from_rtb(data, filename):
    # Header:
    # 0x00: 0xFE
    # 0x01: 2-byte symbol count
    if len(data) < 10 or data[0] != 0xfe:
        return []
    
    # We look for opcode 0x33:
    # Pattern: \x33\x01 [3 bytes tag] [1 byte len] [Shift-JIS text]
    # Followed by \x65\x01 [3 bytes tag]
    marker = b'\x33\x01'
    pos = 0
    records = []
    
    while True:
        idx = data.find(marker, pos)
        if idx == -1:
            break
        # Tag is at idx+2..idx+5
        tag = data[idx+2:idx+5]
        str_len = data[idx+5] if idx+5 < len(data) else 0
        text_bytes = data[idx+6 : idx+6+str_len]
        
        # Check if following instruction is 0x65 or similar
        next_op = data[idx+6+str_len] if idx+6+str_len < len(data) else 0
        
        # Decode text
        try:
            text = text_bytes.decode('cp932')
        except:
            text = None
            
        if text and len(text.strip()) > 0:
            records.append({
                'offset': idx,
                'len': str_len,
                'tag': tag.hex(),
                'text': text,
                'next_op': hex(next_op)
            })
        pos = idx + 1
        
    # Group by speaker / dialogue
    # In RTB, speaker name is usually a short string preceding a longer dialogue
    dialogues = []
    i = 0
    while i < len(records):
        cur = records[i]
        # If current is short (< 16 chars) and next is a multi-line or longer dialogue
        # e.g., 'ラキ', 'テージ'
        if i + 1 < len(records) and len(cur['text']) <= 8 and len(records[i+1]['text']) > len(cur['text']):
            # Potential speaker + dialogue pair
            dialogues.append({
                'file': filename,
                'speaker': cur['text'],
                'speaker_offset': cur['offset'],
                'text': records[i+1]['text'],
                'text_offset': records[i+1]['offset'],
                'text_len': records[i+1]['len']
            })
            i += 2
        else:
            dialogues.append({
                'file': filename,
                'speaker': '',
                'speaker_offset': 0,
                'text': cur['text'],
                'text_offset': cur['offset'],
                'text_len': cur['len']
            })
            i += 1
            
    return dialogues

def main():
    hed_path = 'Poison Pink (Japan)/DATA/DMAP.HED'
    dat_path = 'Poison Pink (Japan)/DATA/DMAP.DAT'
    entries = parse_hed_file(hed_path)
    rtb_entries = [e for e in entries if e['name'].endswith('.rtb') and e['size'] > 0]
    
    print(f"Extracting dialogues from {len(rtb_entries)} RTB files...")
    all_dialogues = []
    total_text_count = 0
    
    with open(dat_path, 'rb') as fp:
        for e in rtb_entries:
            fp.seek(e['offset'])
            data = fp.read(e['size'])
            d = extract_dialogue_from_rtb(data, e['name'])
            # Filter out pure asset filenames like .tm2, .ups
            filtered = [x for x in d if not x['text'].endswith(('.tm2', '.ups', '.uad', '.vly', '.ag', '.ags'))]
            all_dialogues.extend(filtered)
            total_text_count += len(filtered)
            
    print(f"Total dialogue lines extracted: {total_text_count}")
    
    out_file = 'tools/all_dmap_dialogues.json'
    with open(out_file, 'w', encoding='utf-8') as fp:
        json.dump(all_dialogues, fp, ensure_ascii=False, indent=2)
        
    print(f"Saved to {out_file} ({os.path.getsize(out_file)} bytes)")
    
    # Print sample
    print("\n--- Sample Extracted Dialogues ---")
    for row in [x for x in all_dialogues if x['speaker']][:15]:
        t = row['text'].replace('\n', ' ')
        print(f"[{row['file']}] {row['speaker']}: {t}")

if __name__ == '__main__':
    main()
