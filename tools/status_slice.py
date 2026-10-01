#!/usr/bin/env python3
"""Build 5-item/5-skill Korean slice on the verified tutorial translation."""
import json
import argparse
import re
import struct
import unicodedata
from pathlib import Path
from PIL import Image, ImageDraw
from localization_pipeline import ROOT, sha, file_hash, hed_tree, write_json
from iso_archive_stage import SOURCE, ISO, exact, source_sha, overlay, iso_inventory, stage_archive
from tutorial_slice import grow_font_archive, iso_record_field_offsets, verify_plan
from korean_sentence_probe import FONT_SOURCE, rasterize, choose_slots, used_byte_pairs, encode_korean, decode_korean, archive_member
from font_pair_probe import get_font, encode_glyph, decode_glyph, japanese_index
from status_db_codec import SCHEMAS, parse, replace_text, nontext_signature

OUT=ROOT/'build/status_slice'
BASE=ROOT/'build/tutorial_slice'


def apply_review(kind, data, rows, mapping):
    model=parse(data,kind);changes={};checks=[]
    for row in rows:
        if row['kind']!=kind:continue
        s,i,name=row['section'],row['record_index'],row['field'];key=(s,i,name)
        if key in changes:raise ValueError('Duplicate review location')
        if row['status']!='reviewed' or not row['reviewer'] or row['member_sha256']!=sha(data):
            raise ValueError('Review/source mismatch')
        fields={f['name']:f for f in model['sections'][s]['records'][i]['fields']}
        if row['record_id']!=fields['id']['value']:raise ValueError('ID mismatch')
        if name not in fields or fields[name]['type']!='z':raise ValueError('Not a text field')
        raw=bytes.fromhex(row['raw_hex'])
        if raw!=fields[name]['value'] or sha(raw)!=row['source_sha256'] or raw.decode('cp932')!=row['source']:
            raise ValueError('Source text mismatch')
        if not raw:raise ValueError('This slice must not populate empty source text')
        tokens=lambda t:re.findall(r'\d+|[↑↓]',unicodedata.normalize('NFKC',t))
        if tokens(row['source'])!=tokens(row['target']):raise ValueError('Numeric/range tokens changed')
        encoded=encode_korean(row['target'],mapping)
        if decode_korean(encoded,mapping)!=row['target']:raise ValueError('Encoding roundtrip failure')
        # DB descriptions render as one top status line, ignoring embedded newlines.
        top_width=sum(8 if ord(c)<128 else 16 for c in row['target'] if c!='\n')
        if name=='description' and top_width>620:raise ValueError('Top-line estimate exceeds screen width')
        changes[key]=(raw,encoded)
        checks.append(dict(id=row['id'],before_bytes=len(raw),after_bytes=len(encoded),top_line_estimate=top_width))
    modified=replace_text(data,kind,changes,sha(data))
    if nontext_signature(model)!=nontext_signature(parse(modified,kind)):raise ValueError('Numeric field change')
    return modified,checks


def build():
    output=OUT/'Poison Pink (Japan) - status slice.iso'
    if output.exists() or (OUT/'manifest.json').exists():raise ValueError('Refusing output overwrite')
    review=json.loads((ROOT/'localization/status_slice.json').read_text())['records']
    if len(review)!=16:raise ValueError('Unexpected review scope')
    base=json.loads((ROOT/'reports/tutorial_slice.json').read_text())
    base_hed=(BASE/'DATA/SYSTEM.HED').read_bytes();base_dat=(BASE/'DATA/SYSTEM.DAT').read_bytes()
    expected=next(p['after_sha256'] for p in base['iso']['replacements'] if p['offset']==base['system_iso_lba_new']*2048)
    if sha(base_dat)!=expected:raise ValueError('Tutorial SYSTEM changed')
    entries,_=hed_tree(base_hed)
    def member(path):
        e=next(e for e in entries if e['path']==path)
        return base_dat[e['offset']:e['offset']+e['size']]
    old_font=member('system/kanji.dat');old_table=member('system/kantable.dat')
    table=list(struct.unpack('<7560h',old_table));original,original_table=get_font()
    if old_font[:len(original)]!=original:raise ValueError('Original font mismatch')
    mapping=dict(base['mapping'])
    for c,m in mapping.items():
        if table[m['table_index']]!=m['glyph_id']:raise ValueError('Tutorial mapping mismatch')
    # Retain the original game glyphs for range arrows instead of adding replacements.
    for c in '↑↓':
        raw=c.encode('cp932');idx=japanese_index(int.from_bytes(raw,'big'))
        if original_table[idx]<0:raise ValueError('Missing native arrow glyph')
        mapping[c]=dict(code_hex=raw.hex(),table_index=idx,glyph_id=original_table[idx],native=True)
    chars=sorted({c for r in review for c in r['target'] if ord(c)>127 and c not in mapping})
    if len(chars)%2:chars.append(next(c for c in '값꽃닭앉' if c not in chars and c not in mapping))
    if file_hash(FONT_SOURCE)!=base['font_source_sha256']:raise ValueError('Font source changed')
    slots=choose_slots(table,used_byte_pairs(),len(chars));glyphs=rasterize(FONT_SOURCE,chars)
    first_id=len(old_font)//144;font=bytearray(old_font+bytes(len(chars)*144))
    for i,(c,(code,idx)) in enumerate(zip(chars,slots)):
        gid=first_id+i;mapping[c]=dict(code_hex=code.to_bytes(2,'big').hex(),table_index=idx,glyph_id=gid)
        table[idx]=gid;encode_glyph(font,gid,glyphs[c])
    if font[:len(old_font)]!=old_font:raise ValueError('Existing glyph bytes changed')
    for i,v in enumerate(struct.unpack('<7560h',old_table)):
        if v!=-1 and table[i]!=v:raise ValueError('Existing font mapping changed')
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'DATA').mkdir(exist_ok=True)
    replacements={};checks=[];db={}
    for kind in ['PPITEM','PPSKILL']:
        entry,data=archive_member('STATUS','status/'+kind+'.dat')
        modified,checked=apply_review(kind,data,review,mapping)
        replacements[entry['path']]=modified;checks+=checked
        (OUT/(kind+'.dat')).write_bytes(modified)
        db[kind]=dict(before_sha256=sha(data),after_sha256=sha(modified),before_bytes=len(data),after_bytes=len(modified),
                      nontext_fields_preserved=True,exact_eof=True)
    status=stage_archive('STATUS',OUT/'DATA',replacements,allow_padding_growth=True,allow_shrink=True)
    tablebytes=struct.pack('<7560h',*table)
    systemhed,systemdat,shift=grow_font_archive((SOURCE/'DATA/SYSTEM.HED').read_bytes(),(SOURCE/'DATA/SYSTEM.DAT').read_bytes(),bytes(font),tablebytes)
    if file_hash(SOURCE/'DATA/SYSTEM.HED')!=source_sha(SOURCE/'DATA/SYSTEM.HED') or file_hash(SOURCE/'DATA/SYSTEM.DAT')!=source_sha(SOURCE/'DATA/SYSTEM.DAT'):
        raise ValueError('SYSTEM source mismatch')
    for name,data in [('SYSTEM.HED',systemhed),('SYSTEM.DAT',systemdat)]: (OUT/'DATA'/name).write_bytes(data)
    (OUT/'kanji.dat').write_bytes(font);(OUT/'kantable.dat').write_bytes(tablebytes)
    inv=iso_inventory(ISO);iso_entries={e['path']:e for e in inv['files']};system=iso_entries['DATA/SYSTEM.DAT']
    oldstart=system['lba']*2048;newstart=oldstart-shift
    occupied=[(e['lba']*2048,e['lba']*2048+e['size']) for e in inv['files']+inv['directories'] if e.get('path')!='DATA/SYSTEM.DAT']
    if newstart<20*2048 or any(a<oldstart+system['size'] and b>newstart for a,b in occupied):raise ValueError('SYSTEM extent overlap')
    with ISO.open('rb') as f:
        f.seek(newstart)
        if any(exact(f,shift)):raise ValueError('Nonzero preceding ISO gap')
    planned=[]
    def patch(offset,data):
        with ISO.open('rb') as f:f.seek(offset);old=exact(f,len(data))
        planned.append(dict(offset=offset,data=data,expected_sha256=sha(old)))
    for path in ['DATA/DMAP.HED','DATA/DMAP.DAT','DATA/STATUS.HED','DATA/STATUS.DAT','DATA/SYSTEM.HED']:
        local=(BASE if '/DMAP.' in path else OUT)/path
        if '/DMAP.' in path:
            kind=path.rsplit('.',1)[1].lower()
            if file_hash(local)!=base['dmap'][kind]['output_sha256']:raise ValueError('Tutorial DMAP changed')
        if local.stat().st_size!=iso_entries[path]['size']:raise ValueError('Unexpected ISO file size')
        patch(iso_entries[path]['lba']*2048,local.read_bytes())
    patch(newstart,systemdat)
    lba_field,size_field=iso_record_field_offsets(inv,'DATA/SYSTEM.DAT')
    both=lambda v:struct.pack('<I',v)+struct.pack('>I',v)
    patch(lba_field,both(newstart//2048));patch(size_field,both(len(systemdat)))
    iso=overlay(ISO,output,planned,source_sha(ISO))
    expected_inv=json.loads(json.dumps(inv))
    for e in expected_inv['files']:
        if e['path']=='DATA/SYSTEM.DAT':e.update(lba=newstart//2048,size=len(systemdat))
    if iso_inventory(output)!=expected_inv:raise ValueError('ISO metadata differs from plan')
    verified=verify_plan(output,planned,iso['output_sha256'])
    # Exact glyph bitmap preview, including native arrow shapes.
    preview=Image.new('RGB',(800,len(review)*90),'#18222c');draw=ImageDraw.Draw(preview)
    for n,row in enumerate(review):
        draw.text((8,n*90),row['id'],fill='white')
        for j,line in enumerate(row['target'].split('\n')):
            x=8;y=n*90+18+j*26
            for c in line:
                if c in mapping:
                    mask=Image.new('L',(24,24));mask.putdata([v*85 for v in decode_glyph(font,mapping[c]['glyph_id'])])
                    preview.paste('white',(x,y),mask);x+=24
                else:draw.text((x,y+7),c,fill='white');x+=12
    preview.save(OUT/'translation-preview.png')
    report=dict(schema_version=1,iso_path=str(output.relative_to(ROOT)),iso=iso,entire_iso_diff=verified,
        review_sha256=file_hash(ROOT/'localization/status_slice.json'),scope=review,db=db,status_archive=status,
        mapping=mapping,added_glyphs=len(chars),added_characters=chars,total_glyphs=len(font)//144,max_glyph_id=len(font)//144-1,
        previous_2168_glyphs_preserved=True,original_japanese_preserved=True,tutorial_dmap_preserved=True,
        native_range_arrows_preserved=True,font_source_sha256=base['font_source_sha256'],
        font_license='SIL OFL 1.1; build/korean_sentence/OFL.txt',system_dat_shift=shift,
        system_iso_lba_new=newstart//2048,width_preflight=checks,
        width_note='Top status line: estimated 16px Japanese/Hangul and 8px ASCII at 640px; runtime required.',
        runtime_verified=False)
    write_json(OUT/'manifest.json',report);write_json(ROOT/'reports/status_slice.json',report)
    print(json.dumps({k:report[k] for k in ['iso_path','added_glyphs','total_glyphs','max_glyph_id','db']},ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',default='build/status_slice')
    args=parser.parse_args()
    OUT=(ROOT/args.output_dir).resolve()
    if (ROOT/'build').resolve() not in OUT.parents:
        raise ValueError('Output must be a project build subdirectory')
    build()
