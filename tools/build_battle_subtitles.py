#!/usr/bin/env python3
"""Embed bounded KV voice subtitles in a new, heap-reserved ELF load segment.

Original archives, movie streams, saves and user emulator configuration are never
modified. Unreviewed recognizer output is not rendered. All mutations are guarded.
Rebuilding requires private local game extractions, the previous standalone build,
and the existing localization pipeline's font mapping report; none are distributed.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from battle_voice_hook_probe import Assembler
from battle_subtitle_probe import words, jal, patch_state
from runtime_compat import virtual_offset, elf_segments, pcsx2_crc
from iso_archive_stage import iso_inventory, overlay, exact
from localization_pipeline import ROOT, sha, write_json

BASE = ROOT / 'build/iso_dialogue_fix_v1/Poison Pink (Japan) - Korean standalone v1.iso'
BASE_SHA = 'f7276bfe1da4b9599d5242daa74ee094ac87e3044173e3c943b6320890fed072'
OUT = ROOT / 'build/battle_voice_subtitles_v1'
ADDRESS = 0x650000


def signature(raw):
    value = 2166136261
    for byte in raw[:512]:
        value = ((value ^ byte) * 16777619) & 0xffffffff
    return value, len(raw)


def encode(text, mapping):
    if '%' in text or '\n' in text or '\0' in text:
        raise ValueError('Only literal, single-line subtitles are supported')
    result = bytearray()
    for char in text:
        if char in mapping: result.extend(bytes.fromhex(mapping[char]['code_hex']))
        elif 32 <= ord(char) <= 126: result.append(ord(char))
        else: raise ValueError('Unmapped character: ' + char)
    return bytes(result) + b'\0'


def assemble(rows, base=ADDRESS):
    mapping = json.loads((ROOT/'reports/system_messages_v1.json').read_text())['mapping']
    # State and temporary draw arguments have their own reserved segment storage.
    state = base + 0x400
    coordinates = state + 0x40
    shadow_coordinates = state + 0x50
    white, black = state + 0x60, state + 0x64
    table = base + 0x500
    strings = table + len(rows)*24
    entries, text_data, seen = [], bytearray(), set()
    for row in rows:
        bank = (ROOT/row['bank']).read_bytes()
        body = 0x40 + struct.unpack_from('<I', bank, 8)[0]
        raw = bank[body+row['offset']:body+row['offset']+row['size']]
        if hashlib.sha256(raw).hexdigest() != row['sha256']: raise ValueError('Voice source changed')
        key = signature(raw)
        if key in seen: raise ValueError('Voice signature collision')
        seen.add(key)
        ptr, frames, x = 0, 0, 0
        if row['status'] == 'reviewed_translation':
            encoded = encode(row['ko'], mapping)
            ptr = strings + len(text_data); text_data.extend(encoded)
            frames = min(240, max(120, int(60*(1+len(row['ko'])/9))))
            width = sum(10.2 if ord(c)<128 else 20.4 for c in row['ko'])
            if width > 584: raise ValueError('Subtitle exceeds safe width')
            x = struct.unpack('<I', struct.pack('<f', (640-width)/2))[0]
        entries.append((*key, ptr, frames, x, 0))
    a = Assembler(base)
    a.label('voice')
    a.emit(0x27bdfff0,0xffa40000,0xffbf0008,0x24090600)
    a.branch(5,4,9,'voice_done')
    a.load(8,0x447000)
    a.emit(0x8d0a0004,0x8d0b0008,0x8d0c000c,0x240d5622)
    a.branch(5,12,13,'voice_done') # 22050 Hz KV only
    a.branch(4,11,0,'voice_done')
    a.load(12,0x100000);a.emit(0x014c682b)
    a.branch(5,13,0,'voice_done') # pointer >= 1 MiB
    a.emit(0x240c0200,0x2d6d0200,0x016d600b) # count=min(size,512)
    a.emit(0x014c6821);a.load(14,0x02000001);a.emit(0x01ae682b)
    a.branch(4,13,0,'voice_done') # pointer+count <=32MiB
    a.load(13,2166136261);a.load(14,16777619)
    a.label('hash')
    a.emit(0x914f0000,0x01af6826,0x01ae0019,0x00006812,0x254a0001,0x258cffff)
    a.branch(5,12,0,'hash')
    a.load(8,state);a.emit(0xad0d001c,0xad0b0020,0x8d090014,0x25290001,0xad090014)
    a.load(10,table);a.load(12,len(entries))
    a.label('lookup')
    a.emit(0x8d490000)
    a.branch(5,9,13,'next')
    a.emit(0x8d490004)
    a.branch(5,9,11,'next')
    a.emit(0x8d490008)
    a.branch(4,9,0,'voice_done') # unreviewed/non-verbal clips never overwrite a readable line
    a.emit(0xad090000,0x8f89802c,0xad090008,0x8d4c000c,0x012c4821,0xad090004,
           0x8d490010,0xad090040,0xad090050,0x8d090018,0x25290001,0xad090018)
    a.branch(4,0,0,'voice_done')
    a.label('next');a.emit(0x254a0018,0x258cffff)
    a.branch(5,12,0,'lookup')
    a.label('voice_done')
    a.emit(0xdfa40000,0xdfbf0008,0x27bd0010,0x27bdfff0,0x3c060044,
           0x08000000 | 0x190118 >> 2,0)
    a.label('frame')
    a.emit(0x27bdffe0,0xffbf0018,0xffb00010);a.load(16,state)
    a.emit(0x8e070000)
    a.branch(4,7,0,'frame_done')
    a.emit(0x8e080004,0x8f89802c,0x01095023,0x2d4b00f1)
    a.branch(4,11,0,'expire') # unsigned remaining must be <=240, catches load/clock resets
    a.branch(4,10,0,'expire')
    a.emit(0x3c040055,0x8c8406ec)
    a.branch(4,4,0,'frame_done')
    a.load(5,shadow_coordinates);a.load(6,black);a.emit(jal(0x1d7348),0)
    a.emit(0x3c040055,0x8c8406ec);a.load(5,coordinates);a.load(6,white)
    a.emit(0x8e070000,jal(0x1d7348),0)
    a.branch(4,0,0,'frame_done')
    a.label('expire');a.emit(0xae000000)
    a.label('frame_done');a.emit(0xdfb00010,0xdfbf0018,0x08000000 | 0x1e0aa0 >> 2,0x27bd0020)
    code = a.finish()
    if len(code)>0x400: raise ValueError('Hook code exceeds reserved region')
    payload=bytearray(0x500)
    payload[:len(code)]=code
    payload[0x440:0x450]=struct.pack('<4f',160,330,65535,.85)
    payload[0x450:0x460]=struct.pack('<4f',160,331,65535,.85)
    payload[0x460:0x468]=bytes([255,255,255,128,0,0,0,128])
    payload.extend(b''.join(words(*r) for r in entries));payload.extend(text_data)
    payload.extend(bytes((-len(payload))%16))
    return bytes(payload),dict(base=base,state=state,table=table,rows=len(rows),
        code_bytes=len(code),segment_bytes=len(payload),labels=a.labels,
        translated=sum(r['status']=='reviewed_translation' for r in rows))


def build_elf(original, payload, meta):
    oldseg=elf_segments(original)
    if len(oldseg)!=1 or max(s[2]+s[5] for s in oldseg)!=0x64ebd0:
        raise ValueError('Unexpected original ELF memory layout')
    if struct.unpack_from('<HH', original,42)!=(32,1):raise ValueError('Unexpected program header table')
    target=bytearray(original);patches=[]
    def change(addr, before, after):
        off=virtual_offset(original,addr,len(before))
        if target[off:off+len(before)]!=before:raise ValueError('Instruction changed at '+hex(addr))
        target[off:off+len(before)]=after;patches.append((addr,before,after))
    change(0x190110,words(0x27bdfff0,0x3c060044),words(0x08000000|meta['labels']['voice']>>2,0))
    change(0x1008d8,words(jal(0x1e0aa0)),words(jal(meta['labels']['frame'])))
    heap=(ADDRESS+len(payload)+4095)&~4095
    def constant(hiaddr,loaddr,old,new):
        hi=struct.unpack_from('<I',original,virtual_offset(original,hiaddr))[0]
        lo=struct.unpack_from('<I',original,virtual_offset(original,loaddr))[0]
        if hi&0xffff!=(old+0x8000)>>16 or lo&0xffff!=old&0xffff:raise ValueError('Heap constant guard failed')
        change(hiaddr,words(hi),words(hi&0xffff0000|((new+0x8000)>>16)))
        change(loaddr,words(lo),words(lo&0xffff0000|(new&0xffff)))
    for pair in [(0x1002fc,0x100304),(0x1e5e4c,0x1e5e60),(0x2168a8,0x2168ac),(0x2168e0,0x2168e8)]:
        constant(*pair,0x64ebd0,heap)
    for pair in [(0x100300,0x100308),(0x1e5e70,0x1e5e78)]:constant(*pair,0x19a1430,0x2000000-heap)
    # Preserve the original BSS clear end. New payload is file-backed, outside BSS.
    assert target[virtual_offset(original,0x10024c):virtual_offset(original,0x100258)] == original[virtual_offset(original,0x10024c):virtual_offset(original,0x100258)]
    offset=(len(target)+4095)&~4095
    if any(target[84:116]):raise ValueError('Second program header slot occupied')
    target[84:116]=words(1,offset,ADDRESS,ADDRESS,len(payload),len(payload),7,4096)
    struct.pack_into('<H',target,44,2)
    target.extend(bytes(offset-len(target)));target.extend(payload)
    assert len(elf_segments(target))==2
    meta.update(heap_start=heap,heap_reserved_bytes=heap-0x64ebd0,elf_crc=pcsx2_crc(target),elf_bytes=len(target),segment_offset=offset)
    return bytes(target),patches


def directory_fields(fp, inv, path):
    directory=next(e for e in inv['directories'] if e['path']=='')
    base=directory['lba']*2048;fp.seek(base);raw=exact(fp,directory['size']);pos=0;found=[]
    while pos<len(raw):
        size=raw[pos]
        if not size:pos=(pos//2048+1)*2048;continue
        name=raw[pos+33:pos+33+raw[pos+32]].decode('ascii').split(';')[0]
        if name==path:found.append((base+pos+2,base+pos+10))
        pos+=size
    if len(found)!=1:raise ValueError('Directory entry not unique')
    return found[0]


def main():
    p=argparse.ArgumentParser();p.add_argument('--iso',action='store_true');p.add_argument('--probe',action='store_true');p.add_argument('--revision',type=int,default=1);args=p.parse_args()
    rows=json.loads((ROOT/'localization/battle_voice_subtitles_v1.json').read_text())['rows']
    payload,meta=assemble(rows)
    original=(ROOT/'build/iso_dialogue_fix_v1/SLPS_258.54').read_bytes()
    elf,patches=build_elf(original,payload,meta)
    OUT.mkdir(exist_ok=True);(OUT/'subtitle_segment.bin').write_bytes(payload);(OUT/'SLPS_258.54').write_bytes(elf)
    meta.update(status='prepared',requires_external_patch=False,base_iso=str(BASE.relative_to(ROOT)),base_iso_sha256=BASE_SHA)
    if args.probe:
        # A copy-only experiment. The live state's original allocator remains;
        # this zero reservation is only used for a brief render test, never release.
        ram=(OUT/'eeMemory.bin').read_bytes()
        assert not any(ram[ADDRESS:ADDRESS+len(payload)])
        probe_patches=[r for r in patches if r[0] in (0x190110,0x1008d8)]
        patch_state(OUT/'user_slot1_original.p2s',OUT/'korean_caption_probe.p2s',probe_patches+[(ADDRESS,bytes(len(payload)),payload)])
    if args.iso:
        inv=iso_inventory(BASE);entries={e['path']:e for e in inv['files']};entry=entries['SLPS_258.54']
        occupied=sorted((e['lba']*2048,(e['lba']*2048+e['size']+2047)//2048*2048) for e in inv['files']+inv['directories'])
        gap_end=entries['DATA/SYSTEM.DAT']['lba']*2048
        gap_start=max(b for a,b in occupied if b<=gap_end)
        position=(gap_end-len(elf))//0x4000*0x4000
        if position<gap_start:raise ValueError('Insufficient unused ISO gap')
        with BASE.open('rb') as fp:
            fp.seek(entry['lba']*2048)
            if exact(fp,entry['size'])!=original:raise ValueError('Baseline ELF differs')
            fp.seek(position);old=exact(fp,len(elf))
            if any(old):raise ValueError('ISO relocation gap is not empty')
            replacements=[dict(offset=position,data=elf,expected_sha256=sha(old))]
            for field,value in zip(directory_fields(fp,inv,'SLPS_258.54'),[position//2048,len(elf)]):
                fp.seek(field);before=exact(fp,8)
                replacements.append(dict(offset=field,data=struct.pack('<I',value)+struct.pack('>I',value),expected_sha256=sha(before)))
        if not 1<=args.revision<=99:raise ValueError('Invalid revision')
        output=OUT/('Poison Pink (Japan) - Korean battle subtitles v%d.iso'%args.revision)
        result=overlay(BASE,output,replacements,BASE_SHA)
        after=iso_inventory(output)
        expected=json.loads(json.dumps(inv));next(e for e in expected['files'] if e['path']=='SLPS_258.54').update(lba=position//2048,size=len(elf))
        if after!=expected:raise ValueError('Unexpected ISO layout change')
        # Full-byte equality outside the relocated ELF and its two directory fields.
        from build_iso_dialogue_fix import verify_unplanned_bytes
        meta.update(status='built_static_verified',iso_path=str(output.relative_to(ROOT)),iso=result,
                    verification=verify_unplanned_bytes(BASE,output,sorted(replacements,key=lambda r:r['offset'])),
                    relocation=dict(old_lba=entry['lba'],new_lba=position//2048),runtime_verified=False)
        (OUT/'SHA256SUMS.txt').write_text(result['output_sha256']+'  '+output.name+'\n')
    write_json(OUT/'report.json',meta)
    print(json.dumps(meta,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
