#!/usr/bin/env python3
"""Translate reviewed player-facing ELF literals over Korean text v1."""
import argparse, csv, json, re, struct
from pathlib import Path
from localization_pipeline import ROOT, sha, file_hash, write_json, hed_tree
from iso_archive_stage import iso_inventory, exact, overlay
import build_user_translation_import as shared
from korean_sentence_probe import encode_korean, decode_korean
from ui_titles import extend_font

BASE = 'build/user_translations_v1/Poison Pink (Japan) - Korean text v1.iso'
BASE_SHA = '7a9f425a5bfc883d94349888445b87684c66315b854782b7c69fa4468c63b3e8'
OUT = ROOT/'build/system_messages_v1'
RANGES = [(0x429b80,0x42ae40), (0x42da60,0x42e988),
          (0x4329f8,0x432e08), (0x436310,0x436720),
          (0x4368c8,0x4391b0), (0x439c48,0x439d30),
          (0x43a128,0x43ae20), (0x453368,0x453670)]
EXTRA = {0x439e98,0x439ea8,0x4508b8,0x451d48,0x452878,0x453b68,0x453b70,0x456ee0,0x456ef0}

def tokens(text):
    return re.findall(r'@\s*[a-z0-9]|%[-+ #0-9.*]*[a-zA-Z]', text)

def pack_literal(original, p, source, target, capacity, mapping, packed):
    old=source.encode('cp932');new=encode_korean(target,mapping)
    assert original[p:p+len(old)+1]==old+b'\0'
    assert tokens(source)==tokens(target), (source,target,'control tokens')
    assert source.count('\n')==target.count('\n'), (source,target,'newline count')
    if len(new)>capacity:raise ValueError((hex(p),len(new),capacity,source,target))
    assert b'\0' not in new and decode_korean(new,mapping)==target
    # Packed multi-line messages are walked through NUL separators. Never insert
    # earlier terminators, even when the Korean line is shorter than the source.
    if packed:
        assert capacity==len(old)
        payload=new+b' '*(capacity-len(new))+b'\0'
        assert [i for i,b in enumerate(payload) if b==0]==[len(old)]
    else:
        payload=new+bytes(capacity+1-len(new))
    return payload

def prepare():
    inv=iso_inventory(ROOT/BASE);entries={e['path']:e for e in inv['files']}
    with (ROOT/BASE).open('rb') as f:
        def read(path):
            e=entries[path];f.seek(e['lba']*2048);return exact(f,e['size'])
        elf=read('SLPS_258.54');hed=read('DATA/SYSTEM.HED');dat=read('DATA/SYSTEM.DAT')
    original=(ROOT/'Poison Pink (Japan)/SLPS_258.54').read_bytes()
    refs=shared.elf_refs(original)
    # a1 is completed in the JAL delay slot; intervening instructions only write
    # a0 and a2. Bind the full observed instruction sequence before accepting it.
    delayed=struct.unpack_from('<5I',original,0x2173a8)
    assert delayed==(0x3c050054,0x03a0202d,0x27a60010,0x0c0dbb52,0x24a58e98)
    refs[0x439e98+0xff000].append(dict(kind='verified_lui_delay_slot',offset=0x2173a8,words=list(delayed)))
    manual=json.loads((ROOT/'localization/system_messages_ko.json').read_text())
    overrides_path=ROOT/'localization/system_messages_overrides.json'
    overrides=json.loads(overrides_path.read_text()) if overrides_path.exists() else {}
    prior=json.loads((ROOT/'reports/user_translations_applied_20260917.json').read_text())
    rows=[];missing=[];preserved=[];excluded=[]
    with (ROOT/'localization/imports/20260917_corrected/elf_ko_corrected.tsv').open() as f:
        catalog=list(csv.DictReader(f,delimiter='\t'))
    for r in catalog:
        p=int(r['offset']);s=r['source'];va=int(r['virtual_address'])
        if not(any(lo<=p<hi for lo,hi in RANGES) or p in EXTRA):continue
        if 'なし［ＨＲ' in s or s=='プログラムミス':
            excluded.append(dict(offset=p,source=s,reason='unused slot / internal diagnostic'));continue
        t=overrides.get(hex(p),manual.get(s,r['target']))
        if not t or not re.search('[ぁ-ヿ一-龯Ａ-Ｚ]',s) and p not in EXTRA:continue
        old=s.encode('cp932')
        if original[p-1]!=0 or original[p:p+len(old)+1]!=old+b'\0':
            excluded.append(dict(offset=p,source=s,reason='not a whole NUL literal'));continue
        if elf[p:p+len(old)+1]!=old+b'\0':
            preserved.append(dict(offset=p,source=s,reason='already patched'));continue
        direct=refs.get(va,[]);parent=None
        packed=0x429be0<=p<0x42adb0
        if packed:
            q=p
            # A preceding NUL is a line separator only if it is not followed by
            # alignment padding. Locate the first referenced line of this block.
            while not refs.get(q+0xff000) and q>0x429b80:
                if original[q-2]==0:break
                q=original.rfind(b'\0',0,q-1)+1
            if refs.get(q+0xff000):parent=dict(offset=q,references=refs[q+0xff000])
        if not direct and not parent:
            missing.append(dict(offset=p,source=s,target=t,reason='no verified address reference'));continue
        capacity=len(old)
        if not packed:
            boundary=(p+len(old)+1+7)//8*8
            if not any(original[p+len(old):boundary]) and not any(va+len(old)<=k<boundary+0xff000 for k in refs):
                capacity=boundary-p-1
        if any(va<k<va+capacity+1 for k in refs):
            missing.append(dict(offset=p,source=s,target=t,reason='interior address reference'));continue
        assert elf[p:p+capacity+1]==original[p:p+capacity+1]
        rows.append(dict(offset=p,virtual_address=va,source=s,target=t,capacity=capacity,
                         packed=packed,references=direct,parent=parent))
    needed={c for r in rows for c in r['target'] if ord(c)>127 and c not in prior['mapping']}
    # Most glyphs already exist in text v1. Extend only the font, preserving all
    # existing mapping entries and data members; the helper enforces zero padding.
    base=dict(mapping=prior['mapping'],total_glyphs=prior['font']['total_glyphs'],font_source_sha256=prior['font_source_sha256'])
    # Rare Unicode symbols in gallery captions have game-native CP932 glyphs.
    table=next(e for e in hed_tree(hed)[0] if e['path']=='system/kantable.dat')
    tablevalues=struct.unpack('<7560h',dat[table['offset']:table['offset']+table['size']])
    from font_pair_probe import japanese_index
    native=[]
    for c in sorted(needed):
        if '\uac00'<=c<='\ud7a3':continue
        try:
            raw=c.encode('cp932');assert len(raw)==2;idx=japanese_index(int.from_bytes(raw,'big'));assert tablevalues[idx]>=0
        except (UnicodeError,AssertionError,ValueError,IndexError):continue
        base['mapping'][c]=dict(code_hex=raw.hex(),table_index=idx,glyph_id=tablevalues[idx],native=True);native.append(c)
    nh,nd,mapping,font=extend_font(hed,dat,base,[r['target'] for r in rows]);font['native_symbols_reused']=native
    modified=bytearray(elf);issues=[];occupied=set()
    for r in rows:
        if r['offset']==0x4535e0:
            # The complete name cannot fit in its 8-byte slot. Relocate it to an
            # explicitly reclaimed tail of another translated literal below.
            continue
        try:payload=pack_literal(original,r['offset'],r['source'],r['target'],r['capacity'],mapping,r['packed'])
        except (ValueError,AssertionError) as e:issues.append(dict(**r,error=str(e)));continue
        p=r['offset'];span=set(range(p,p+len(payload)));assert not span&occupied;occupied.update(span)
        modified[p:p+len(payload)]=payload;r['encoded_bytes']=len(encode_korean(r['target'],mapping))
    relocations=[]
    for r in rows:
        if r['offset']!=0x4535e0:continue
        va=r['virtual_address'];raw=encode_korean(r['target'],mapping)+b'\0'
        # One fixed data-table pointer is present in the complete aligned ELF;
        # also reject direct GP/LUI references captured by the address scanner.
        actual=[p for p in range(0,len(original)-3,4) if original[p:p+4]==struct.pack('<I',va)]
        assert actual==[0x3dced8] and r['references']==[dict(kind='data_pointer',offset=0x3dced8)]
        # Reject even loose nearby LUI/low-immediate constructions for this name;
        # its observed use is the rescue-character pointer table, not code.
        for p in range(0x1000,0x327000,4):
            w=struct.unpack_from('<I',original,p)[0]
            if w>>26!=15 or w&65535 not in (va>>16,(va+32768)>>16):continue
            reg=(w>>16)&31
            for q in range(p+4,p+260,4):
                v=struct.unpack_from('<I',original,q)[0]
                if v>>26 not in (9,13) or (v>>21)&31!=reg:continue
                imm=v&65535
                address=((w&65535)<<16)+(imm if imm<32768 else imm-65536) if v>>26==9 else ((w&65535)<<16)|imm
                assert address!=va, 'Unaccounted code reference to relocated name'
        donor=next((d for d in rows if not d['packed'] and 'encoded_bytes' in d and
                    (d['offset']+d['encoded_bytes']+1+7)//8*8+len(raw)<=d['offset']+d['capacity']+1),None)
        if donor is None:raise ValueError('No verified literal tail for the full character name')
        pool=(donor['offset']+donor['encoded_bytes']+1+7)//8*8
        assert not any(modified[pool:pool+len(raw)])
        assert not any(donor['virtual_address']<k<donor['virtual_address']+donor['capacity']+1 for k in refs)
        modified[pool:pool+len(raw)]=raw
        for p in actual:
            assert elf[p:p+4]==original[p:p+4]
            struct.pack_into('<I',modified,p,pool+0xff000);occupied.update(range(p,p+4))
        r['encoded_bytes']=len(raw)-1;r['relocated_to']=pool
        relocations.append(dict(source_offset=r['offset'],new_offset=pool,donor_offset=donor['offset'],pointer_offsets=actual,target=r['target']))
    assert len(modified)==len(elf)
    assert all(i in occupied for i,(a,b) in enumerate(zip(elf,modified)) if a!=b)
    for r in rows:
        if any(x['offset']==r['offset'] for x in issues):continue
        p=r.get('relocated_to',r['offset']);end=modified.index(0,p)
        assert decode_korean(bytes(modified[p:end]),mapping).rstrip()==r['target'].rstrip()
        if r['packed']:
            p=r['offset'];size=len(r['source'].encode('cp932'))
            assert modified[p+size]==0 and 0 not in modified[p:p+size]
    assert modified[:0x1000]==elf[:0x1000]
    # Verify every executable ELF section byte, independently of the span check.
    shoff=struct.unpack_from('<I',elf,32)[0];count=struct.unpack_from('<H',elf,48)[0]
    for i in range(count):
        section=struct.unpack_from('<10I',elf,shoff+i*40)
        if section[2]&4:assert modified[section[4]:section[4]+section[5]]==elf[section[4]:section[4]+section[5]]
    OUT.mkdir(parents=True,exist_ok=True)
    report=dict(base_iso=BASE,base_iso_sha256=BASE_SHA,iso_path=str((OUT/'Poison Pink (Japan) - Korean system v1.iso').relative_to(ROOT)),
                literals=rows,issues=issues,unresolved=missing,preserved=preserved,excluded=excluded,font=font,mapping=mapping,
                font_source_sha256=prior['font_source_sha256'],relocations=relocations,
                user_artwork=prior['user_artwork_preserved'],runtime_verified=False)
    write_json(OUT/'prepare.json',report)
    if issues or missing:
        print(json.dumps(dict(issues=issues,unresolved=missing,selected=len(rows)),ensure_ascii=False,indent=2));return None
    staged={'SLPS_258.54':bytes(modified),'DATA/SYSTEM.HED':nh,'DATA/SYSTEM.DAT':nd}
    patches=[]
    with (ROOT/BASE).open('rb') as f:
        for path,payload in staged.items():
            e=entries[path];assert len(payload)==e['size'];p=e['lba']*2048;f.seek(p);old=exact(f,len(payload))
            if old!=payload:patches.append(dict(offset=p,data=payload,expected_sha256=sha(old)))
    return inv,staged,patches,report

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    prepared=prepare()
    if prepared is None:raise SystemExit(1)
    inv,staged,patches,report=prepared
    print(json.dumps(dict(selected=len(report['literals']),preserved=len(report['preserved']),font=report['font']),ensure_ascii=False),flush=True)
    if args.prepare_only:return
    output=ROOT/report['iso_path'];assert not output.exists()
    iso=overlay(ROOT/BASE,output,patches,BASE_SHA)
    shared.BASE_HASH=BASE_SHA
    verification=shared.verify_stream(ROOT/BASE,output,patches,iso['output_sha256'])
    assert iso_inventory(output)==inv
    with output.open('rb') as f:
        for path,data in staged.items():
            e=next(e for e in inv['files'] if e['path']==path);f.seek(e['lba']*2048);assert exact(f,e['size'])==data
    # No patch overlaps any DMAP/STATUS archive byte: their scripts, DBs and all
    # adopted images remain exactly as in the latest translation build.
    for e in inv['files']:
        if e['path'].startswith(('DATA/DMAP.','DATA/STATUS.')):
            assert all(p['offset']+len(p['data'])<=e['lba']*2048 or p['offset']>=e['lba']*2048+e['size'] for p in patches)
    report.update(iso=iso,entire_iso_diff=verification,user_artwork_preserved=True,rtb_and_db_preserved=True,
                  elf_instructions_preserved=True,only_reviewed_name_pointer_relocated=report['relocations'],iso_layout_preserved=True,
                  tool_sha256=file_hash(Path(__file__)))
    write_json(OUT/'manifest.json',report);write_json(ROOT/'reports/system_messages_v1.json',report)
    print(json.dumps(dict(output=str(output),sha256=iso['output_sha256'],literals=len(report['literals']),verified=True),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
