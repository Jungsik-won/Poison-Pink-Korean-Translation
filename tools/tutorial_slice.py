#!/usr/bin/env python3
"""Build the reviewed 24-message tutorial slice; relocate only SYSTEM.DAT in ISO."""
import hashlib
import json
import struct
from pathlib import Path
from PIL import Image,ImageDraw
from localization_pipeline import ROOT,sha,file_hash,hed_tree,write_json
from iso_archive_stage import SOURCE,ISO,CHUNK,exact,source_sha,overlay,iso_inventory,stage_archive
from korean_sentence_probe import archive_member,MEMBER_PATH,FONT_SOURCE,rasterize,choose_slots,used_byte_pairs,encode_korean,decode_korean
from font_pair_probe import get_font,encode_glyph,decode_glyph
from rtb_codec import parse,replace_strings,control_signature

OUT=ROOT/'build/tutorial_slice'
ALIGN=0x4000


def grow_font_archive(hed,dat,font,table):
    entries,_=hed_tree(hed)
    entry=next(e for e in entries if e['path']=='system/kanji.dat')
    after=sorted((e for e in entries if e['offset']>entry['offset']),key=lambda e:e['offset'])
    next_offset=after[0]['offset']
    if len(font)<entry['size'] or font[:entry['size']]!=dat[entry['offset']:entry['offset']+entry['size']]:
        raise ValueError('Expected appended font preserving all original glyphs')
    if any(dat[entry['offset']+entry['size']:next_offset]):raise ValueError('Nonzero font padding')
    growth=max(0,entry['offset']+len(font)-next_offset)
    shift=(growth+ALIGN-1)//ALIGN*ALIGN
    out=bytearray(dat[:entry['offset']]+font+bytes(next_offset+shift-entry['offset']-len(font))+dat[next_offset:])
    newhed=bytearray(hed)
    struct.pack_into('<I',newhed,entry['index']*44+4,len(font))
    for e in after:struct.pack_into('<I',newhed,e['index']*44,e['offset']+shift)
    newentries,_=hed_tree(newhed)
    t=next(e for e in newentries if e['path']=='system/kantable.dat')
    if len(table)!=t['size']:raise ValueError('Table size changed')
    out[t['offset']:t['offset']+t['size']]=table
    for a,b in zip(entries,newentries):
        expected=font if a['path']==entry['path'] else table if a['path']==t['path'] else dat[a['offset']:a['offset']+a['size']]
        if out[b['offset']:b['offset']+b['size']]!=expected:raise ValueError('Member mismatch')
        if b['offset']%ALIGN:raise ValueError('Unaligned archive member')
    return bytes(newhed),bytes(out),shift


def iso_record_field_offsets(inventory,path):
    parent,name=path.rsplit('/',1)
    directory=next(e for e in inventory['directories'] if e['path']==parent)
    base=directory['lba']*2048
    with ISO.open('rb') as f:f.seek(base);data=exact(f,directory['size'])
    pos=0;matches=[]
    while pos<len(data):
        length=data[pos]
        if not length:pos=(pos//2048+1)*2048;continue
        raw=data[pos:pos+length];n=raw[33:33+raw[32]].decode('ascii')
        if n.split(';')[0]==name:matches.append((base+pos+2,base+pos+10))
        pos+=length
    if len(matches)!=1:raise ValueError('ISO record missing or duplicated')
    return matches[0]


def verify_plan(output,patches,expected_output_sha):
    changes={}
    with ISO.open('rb') as f:
        for patch in patches:
            f.seek(patch['offset']);old=exact(f,len(patch['data']))
            if sha(old)!=patch['expected_sha256']:raise ValueError('Unexpected old patch bytes')
            changes.update((patch['offset']+i,(x,y)) for i,(x,y) in enumerate(zip(old,patch['data'])) if x!=y)
    count=len(changes);oldsha=hashlib.sha256();newsha=hashlib.sha256();pos=0
    with ISO.open('rb') as a,output.open('rb') as b:
        while True:
            old=a.read(CHUNK)
            if not old:break
            new=exact(b,len(old));oldsha.update(old);newsha.update(new)
            if old!=new:
                for i,(x,y) in enumerate(zip(old,new)):
                    if x!=y and changes.pop(pos+i,None)!=(x,y):raise ValueError('Unplanned ISO byte')
            pos+=len(old)
        if b.read(1):raise ValueError('Unexpected ISO tail')
    if changes or oldsha.hexdigest()!=source_sha(ISO) or newsha.hexdigest()!=expected_output_sha:
        raise ValueError('Whole ISO verification failed')
    return dict(passed=True,changed_bytes=count,sha256=newsha.hexdigest())


def build():
    output=OUT/'Poison Pink (Japan) - tutorial slice.iso'
    if output.exists() or (OUT/'manifest.json').exists():raise ValueError('Refusing output overwrite')
    review=json.loads((ROOT/'localization/tutorial_slice.json').read_text())['records']
    if len(review)!=47 or sum(r['role']!='speaker' for r in review)!=24:raise ValueError('Unexpected review scope')
    base_report=json.loads((ROOT/'reports/korean_sentence_probe.json').read_text())
    if file_hash(FONT_SOURCE)!=base_report['font_source_sha256']:raise ValueError('Font revision mismatch')
    original,table=get_font()
    first=next(r['target'] for r in review if r['opcode_offset']==0xbb34)
    last=list(dict.fromkeys(c for c in first if ord(c)>127))
    chars=sorted({c for r in review for c in r['target'] if ord(c)>127}-set(last))
    if (len(chars)+len(last))%2:
        spare=next(c for c in '값꽃닭앉' if c not in chars and c not in last);chars.append(spare)
    chars+=last
    slots=choose_slots(table,used_byte_pairs(),len(chars))
    mapping={c:dict(code_hex=code.to_bytes(2,'big').hex(),table_index=idx,glyph_id=2016+i)
             for i,(c,(code,idx)) in enumerate(zip(chars,slots))}
    glyphs=rasterize(FONT_SOURCE,chars);font=bytearray(original+bytes(len(chars)*144));newtable=list(table)
    for c,item in mapping.items():
        encode_glyph(font,item['glyph_id'],glyphs[c]);newtable[item['table_index']]=item['glyph_id']
    if font[:len(original)]!=original:raise ValueError('Original font altered')
    for i,v in enumerate(table):
        if v!=-1 and newtable[i]!=v:raise ValueError('Original mapping altered')
    _,rtb=archive_member('DMAP',MEMBER_PATH);patches={};widths=[]
    for row in review:
        raw=bytes.fromhex(row['raw_hex'])
        if row['status']!='reviewed' or not row['reviewer'] or row['member_sha256']!=sha(rtb) or row['source_sha256']!=sha(raw):
            raise ValueError('Unreviewed or wrong source text')
        encoded=encode_korean(row['target'],mapping)
        if decode_korean(encoded,mapping)!=row['target']:raise ValueError('Encoding roundtrip failed')
        lines=row['target'].split('\n');width=[sum(12 if ord(c)<128 else 24 for c in line) for line in lines]
        if len(lines)>2 or max(width)>360:raise ValueError('Conservative dialog width exceeded')
        if row['opcode_offset'] in patches:raise ValueError('Duplicate translation offset')
        patches[row['opcode_offset']]=(raw,encoded);widths.append(dict(id=row['id'],bytes=len(encoded),line_widths=width))
    modified=replace_strings(rtb,patches,sha(rtb))
    if control_signature(parse(rtb))!=control_signature(parse(modified)):raise ValueError('Control flow changed')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'t00_0010.rtb').write_bytes(modified)
    (OUT/'kanji.dat').write_bytes(font)
    tablebytes=struct.pack('<{}h'.format(len(newtable)),*newtable);(OUT/'kantable.dat').write_bytes(tablebytes)
    hedpath=SOURCE/'DATA/SYSTEM.HED';datpath=SOURCE/'DATA/SYSTEM.DAT'
    if file_hash(hedpath)!=source_sha(hedpath) or file_hash(datpath)!=source_sha(datpath):raise ValueError('SYSTEM source mismatch')
    systemhed,systemdat,shift=grow_font_archive(hedpath.read_bytes(),datpath.read_bytes(),bytes(font),tablebytes)
    (OUT/'DATA').mkdir(exist_ok=True)
    (OUT/'DATA/SYSTEM.HED').write_bytes(systemhed);(OUT/'DATA/SYSTEM.DAT').write_bytes(systemdat)
    dmap=stage_archive('DMAP',OUT/'DATA',{MEMBER_PATH:modified},allow_padding_growth=True,allow_shrink=True)
    inv=iso_inventory(ISO);entries={e['path']:e for e in inv['files']};system=entries['DATA/SYSTEM.DAT']
    oldstart=system['lba']*2048;newstart=oldstart-shift
    # Place the enlarged file immediately before its original start, retaining its end.
    occupied=[(e['lba']*2048,e['lba']*2048+e['size']) for e in inv['files']+inv['directories'] if e.get('path')!='DATA/SYSTEM.DAT']
    if newstart<20*2048 or any(a<oldstart+system['size'] and b>newstart for a,b in occupied):
        raise ValueError('Relocated SYSTEM overlaps another extent')
    planned=[]
    def patch(off,data):
        with ISO.open('rb') as f:f.seek(off);old=exact(f,len(data))
        planned.append(dict(offset=off,data=data,expected_sha256=sha(old)))
    with ISO.open('rb') as f:
        f.seek(newstart)
        if any(exact(f,shift)):raise ValueError('SYSTEM preceding gap is nonzero')
    for path in ['DATA/SYSTEM.HED','DATA/DMAP.HED','DATA/DMAP.DAT']:
        local=OUT/path
        if local.stat().st_size!=entries[path]['size']:raise ValueError('Unexpected ISO file growth')
        patch(entries[path]['lba']*2048,local.read_bytes())
    patch(newstart,systemdat)
    lba_field,size_field=iso_record_field_offsets(inv,'DATA/SYSTEM.DAT')
    both=lambda v:struct.pack('<I',v)+struct.pack('>I',v)
    patch(lba_field,both(newstart//2048));patch(size_field,both(len(systemdat)))
    iso=overlay(ISO,output,planned,source_sha(ISO))
    expected=json.loads(json.dumps(inv))
    for e in expected['files']:
        if e['path']=='DATA/SYSTEM.DAT':e.update(lba=newstart//2048,size=len(systemdat))
    if iso_inventory(output)!=expected:raise ValueError('Unexpected ISO layout differences')
    verified=verify_plan(output,planned,iso['output_sha256'])
    # Preview every selected string using the exact encoded glyph pixels.
    body=[r for r in review if r['role']!='speaker'];preview=Image.new('RGB',(480,24*84),'#18222c');draw=ImageDraw.Draw(preview)
    for n,row in enumerate(body):
        draw.text((8,n*84),hex(row['opcode_offset']),fill='white')
        for j,line in enumerate(row['target'].split('\n')):
            x=8;y=n*84+18+j*26
            for c in line:
                if c in mapping:
                    g=Image.new('L',(24,24));g.putdata([p*85 for p in decode_glyph(font,mapping[c]['glyph_id'])]);preview.paste('white',(x,y),g);x+=24
                else:draw.text((x,y+7),c,fill='white');x+=12
    preview.save(OUT/'translation-preview.png')
    report=dict(schema_version=1,scope=review,translated_messages=24,translated_speaker_literals=23,
        added_glyphs=len(chars),max_glyph_id=2016+len(chars)-1,mapping=mapping,original_font_preserved=True,
        font_source_sha256=base_report['font_source_sha256'],font_license='SIL OFL 1.1; build/korean_sentence/OFL.txt',
        system_dat_shift=shift,system_iso_lba_old=system['lba'],system_iso_lba_new=newstart//2048,
        other_iso_file_positions_preserved=True,rtb_size_old=len(rtb),rtb_size_new=len(modified),rtb_sha256=sha(modified),
        all_rtb_nontext_fields_and_control_signature_preserved=True,width_preflight=widths,
        width_note='Conservative 24px Hangul/12px ASCII estimate; each actual window still requires runtime review',
        dmap=dmap,iso=iso,entire_iso_diff=verified,iso_path=str(output.relative_to(ROOT)),runtime_verified=False)
    write_json(OUT/'manifest.json',report);write_json(ROOT/'reports/tutorial_slice.json',report)
    print(json.dumps({k:report[k] for k in ['translated_messages','added_glyphs','max_glyph_id','system_dat_shift','rtb_size_new','iso_path']}),flush=True)


if __name__=='__main__':build()
