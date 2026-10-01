#!/usr/bin/env python3
"""Bounded ELF literal + font extension + skill-title texture build on UI v3."""
import argparse
import json
import struct
from pathlib import Path
from PIL import Image
from localization_pipeline import ROOT, sha, file_hash, hed_tree, write_json
from iso_archive_stage import iso_inventory, exact, overlay
from korean_sentence_probe import FONT_SOURCE, choose_slots, used_byte_pairs, rasterize, encode_korean, decode_korean
from font_pair_probe import encode_glyph
from tutorial_slice import grow_font_archive
from ui_slice import compile_asset, verify_overlay
from ui_texture_codec import parse, preview_rgba


def patch_literals(raw, review, mapping):
    if sha(raw)!=review['elf_sha256']:raise ValueError('ELF source changed')
    # Restrict this experiment to the observed ELF32 MIPS LOAD and .sdata.
    if raw[:7]!=b'\x7fELF\x01\x01\x01' or struct.unpack_from('<H',raw,18)[0]!=8:
        raise ValueError('Unsupported ELF')
    phoff=struct.unpack_from('<I',raw,28)[0]
    if struct.unpack_from('<HH',raw,42)!=(32,1):raise ValueError('Unexpected LOAD count')
    kind,off,va,pa,size,memsize,flags,align=struct.unpack_from('<8I',raw,phoff)
    if (kind,off,va)!=(1,0x1000,0x100000):raise ValueError('Unexpected LOAD mapping')
    shoff=struct.unpack_from('<I',raw,32)[0]
    section=struct.unpack_from('<10I',raw,shoff+12*40)
    if section[1:6]!=(1,0x10000003,0x54d780,0x44e780,37224):raise ValueError('Unexpected .sdata')
    out=bytearray(raw);occupied=set();checks=[]
    for row in review['literals']:
        pos=row['offset'];old=bytes.fromhex(row['raw_hex']);new=encode_korean(row['target'],mapping)
        if row['status']!='reviewed' or not row['reviewer'] or not row['target']:raise ValueError('Unreviewed literal')
        if old.decode('cp932')!=row['source'] or not old or b'\0' in old:raise ValueError('Wrong source literal')
        selected=section
        if row.get('section','.sdata')=='.rodata':
            selected=struct.unpack_from('<10I',raw,shoff+10*40)
            if selected[1:6]!=(1,2,0x511c80,0x412c80,207536):raise ValueError('Unexpected .rodata')
        elif row.get('section','.sdata')!='.sdata':raise ValueError('Unsupported literal section')
        if not(selected[4]<=pos and pos+len(old)+1<=selected[4]+selected[5]):raise ValueError('Literal outside reviewed section')
        if raw[pos-1]!=0 or raw[pos:pos+len(old)+1]!=old+b'\0':raise ValueError('Literal boundary mismatch')
        if len(new)>len(old) or b'\0' in new or b'\n' in new:raise ValueError('Literal exceeds existing capacity')
        if decode_korean(new,mapping)!=row['target']:raise ValueError('Encoding roundtrip failure')
        positions=set(range(pos,pos+len(old)+1))
        if occupied & positions:raise ValueError('Overlapping literals')
        occupied.update(positions)
        address=pos-off+va
        refs=row['pointer_offsets']
        actual=[i for i in range(0,len(raw)-3,4) if struct.unpack_from('<I',raw,i)[0]==address]
        direct=row.get('direct_reference')
        if refs!=actual or not(refs or direct):raise ValueError('Pointer references changed')
        if direct:
            p=direct['offset'];words=struct.unpack_from('<3I',raw,p)
            # Observed a3 = 0x00550000 + 0x1820; intervening swc1 does not
            # modify GPR a3. Bind all words, not a loose immediate search.
            if words!=(0x3c070055,0xe7b40004,0x24e71820) or address!=0x551820:
                raise ValueError('Direct code reference changed')
        out[pos:pos+len(old)+1]=new+bytes(len(old)+1-len(new))
        checks.append(dict(id=row['id'],source=row['source'],target=row['target'],offset=pos,
            virtual_address=address,pointer_offsets=refs,direct_reference=direct,capacity_bytes=len(old),encoded_bytes=len(new)))
    changed={i for i,(a,b) in enumerate(zip(raw,out)) if a!=b}
    if not changed or not changed<=occupied:raise ValueError('Unplanned ELF byte')
    for row in review['literals']:
        for p in row['pointer_offsets']:
            if out[p:p+4]!=raw[p:p+4]:raise ValueError('Pointer changed')
    return bytes(out),checks


def extend_font(hed,dat,base,targets):
    entries,_=hed_tree(hed);members={e['path']:e for e in entries}
    def member(path):
        e=members[path];return dat[e['offset']:e['offset']+e['size']]
    old_font=member('system/kanji.dat');old_table=member('system/kantable.dat')
    if len(old_font)//144!=base['total_glyphs']:raise ValueError('Wrong base font size')
    mapping=dict(base['mapping']);table=list(struct.unpack('<7560h',old_table))
    for c,m in mapping.items():
        if table[m['table_index']]!=m['glyph_id']:raise ValueError('Existing mapping mismatch')
    chars=sorted({c for text in targets for c in text if ord(c)>127 and c not in mapping})
    padding_glyphs=len(chars)%2
    if file_hash(FONT_SOURCE)!=base['font_source_sha256']:raise ValueError('Font source changed')
    slots=choose_slots(table,used_byte_pairs(),len(chars)) if chars else []
    glyphs=rasterize(FONT_SOURCE,chars) if chars else {}
    font=bytearray(old_font+bytes((len(chars)+padding_glyphs)*144));first=len(old_font)//144
    for i,(c,(code,index)) in enumerate(zip(chars,slots)):
        gid=first+i;table[index]=gid
        mapping[c]=dict(code_hex=code.to_bytes(2,'big').hex(),table_index=index,glyph_id=gid)
        encode_glyph(font,gid,glyphs[c])
    if font[:len(old_font)]!=old_font:raise ValueError('Previous glyph bytes changed')
    for index,value in enumerate(struct.unpack('<7560h',old_table)):
        if value!=-1 and table[index]!=value:raise ValueError('Previous table entry changed')
    newhed,newdat,shift=grow_font_archive(hed,dat,bytes(font),struct.pack('<7560h',*table))
    if shift or len(newdat)!=len(dat):raise ValueError('This slice permits existing font padding only')
    return newhed,newdat,mapping,dict(added_characters=chars,added_glyphs=len(chars)+padding_glyphs,padding_glyphs=padding_glyphs,total_glyphs=len(font)//144,
        previous_glyphs_preserved=True,existing_table_entries_preserved=True,archive_offsets_preserved=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',default='build/ui_titles');p.add_argument('--prepare-only',action='store_true')
    p.add_argument('--review',default='localization/ui_titles.json')
    p.add_argument('--report',default='reports/ui_titles.json')
    args=p.parse_args();out=(ROOT/args.output_dir).resolve()
    if (ROOT/'build').resolve() not in out.parents:raise ValueError('Output must be below build/')
    output=out/'Poison Pink (Japan) - UI titles.iso'
    if output.exists() or (out/'manifest.json').exists():raise ValueError('Refusing completed build overwrite')
    rp=(ROOT/args.review).resolve();report_path=(ROOT/args.report).resolve()
    if (ROOT/'localization').resolve() not in rp.parents or (ROOT/'reports').resolve() not in report_path.parents:
        raise ValueError('Review/report paths must stay in project localization/reports')
    review=json.loads(rp.read_text());source=ROOT/review['base_iso']
    if file_hash(source)!=review['base_iso_sha256']:raise ValueError('Base ISO changed')
    inv=iso_inventory(source);entries={e['path']:e for e in inv['files']};patches=[]
    out.mkdir(parents=True,exist_ok=True)
    with source.open('rb') as fp:
        def read(path):
            e=entries[path];fp.seek(e['lba']*2048);return exact(fp,e['size'])
        def patch(offset,data):
            fp.seek(offset);old=exact(fp,len(data));patches.append(dict(offset=offset,data=data,expected_sha256=sha(old)))
        hed,dat=read('DATA/SYSTEM.HED'),read('DATA/SYSTEM.DAT')
        base=json.loads((ROOT/review['base_font_report']).read_text())
        newhed,newdat,mapping,font=extend_font(hed,dat,base,[r['target'] for r in review['literals']])
        # Only the HED size field and changed font/table member ranges are staged.
        patch(entries['DATA/SYSTEM.HED']['lba']*2048,newhed)
        old_entries,_=hed_tree(hed);new_entries,_=hed_tree(newhed)
        for before,after in zip(old_entries,new_entries):
            if before['offset']!=after['offset']:raise ValueError('SYSTEM member relocated')
            old=dat[before['offset']:before['offset']+before['size']]
            new=newdat[after['offset']:after['offset']+after['size']]
            if old!=new:patch(entries['DATA/SYSTEM.DAT']['lba']*2048+after['offset'],new)
        elf,checks=patch_literals(read('SLPS_258.54'),review,mapping)
        patch(entries['SLPS_258.54']['lba']*2048,elf);(out/'SLPS_258.54').write_bytes(elf)
        assets=[]
        for asset in review['assets']:
            arch=asset['archive'];members,_=hed_tree(read('DATA/'+arch+'.HED'));members={e['path']:e for e in members}
            def get_member(path):
                e=members[path];pos=entries['DATA/'+arch+'.DAT']['lba']*2048+e['offset']
                fp.seek(pos);return pos,exact(fp,e['size'])
            pos,raw=get_member(asset['path']);_,uad=get_member(asset['uad_path'])
            compiled,check=compile_asset(raw,asset,ROOT/asset['author_image'],uad)
            patch(pos,compiled);name=Path(asset['path']).name;(out/name).write_bytes(compiled)
            m=parse(compiled);Image.frombytes('RGBA',(m['width'],m['height']),preview_rgba(m)).save(out/(name+'.png'))
            assets.append(dict(path=asset['path'],**check))
    report=dict(schema_version=1,base_iso=review['base_iso'],base_iso_sha256=review['base_iso_sha256'],
        iso_path=str(output.relative_to(ROOT)),review_sha256=file_hash(rp),elf_before_sha256=review['elf_sha256'],
        elf_after_sha256=sha(elf),literals=checks,font=font,mapping=mapping,assets=assets,
        iso_metadata_preserved=True,runtime_verified=False)
    if args.prepare_only:
        write_json(out/'prepare.json',report)
    else:
        iso=overlay(source,output,patches,review['base_iso_sha256'])
        if iso_inventory(output)!=inv:raise ValueError('ISO metadata changed')
        report.update(iso=iso,entire_iso_diff=verify_overlay(source,output,patches,review['base_iso_sha256'],iso['output_sha256']))
        write_json(out/'manifest.json',report);write_json(report_path,report)
    print(json.dumps(dict(output=str(out),font=font,literals=len(checks),assets=len(assets)),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
