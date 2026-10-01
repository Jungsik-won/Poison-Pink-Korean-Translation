#!/usr/bin/env python3
"""Import bounded text changes over the latest user artwork ISO, preserving all other members."""
import argparse, bisect, hashlib, json, struct
from collections import Counter, defaultdict
from pathlib import Path
from localization_pipeline import ROOT, sha, file_hash, hed_tree, write_json
from iso_archive_stage import exact, iso_inventory, overlay, CHUNK
from korean_sentence_probe import FONT_SOURCE, choose_slots, used_byte_pairs, rasterize, encode_korean, decode_korean
from font_pair_probe import encode_glyph, decode_glyph, japanese_index
from tutorial_slice import grow_font_archive
import rtb_codec as rtb
import status_db_codec as db

INPUT=ROOT/'localization/imports/20260917_corrected'
OUT=ROOT/'build/user_translations_v1'
ALIGN=0x4000
BASE_PATH='build/tutorial_11_user_v1/Poison Pink (Japan) - expanded user help.iso'
BASE_HASH='93b016e26da49cee1173dcc0f727f9cd5c78879f0adefde6ed449909f37dbceb'

def align(n,a=ALIGN):return (n+a-1)//a*a

def elf_refs(data):
    """Conservative address references: aligned data pointers, adjacent LUI/addiu, GP/addiu."""
    shoff=struct.unpack_from('<I',data,32)[0];count=struct.unpack_from('<H',data,48)[0]
    sections=[struct.unpack_from('<10I',data,shoff+i*40) for i in range(count)]
    refs=defaultdict(list)
    # Do not treat instruction words as data pointer evidence.
    for s in sections:
        if s[1]!=1 or s[2]&4:continue
        for p in range(align(s[4],4),s[4]+s[5]-3,4):
            val=struct.unpack_from('<I',data,p)[0]
            if 0x400000<=val<0x570000:refs[val].append(dict(kind='data_pointer',offset=p))
    reginfo=next(s for s in sections if s[1]==0x70000006)
    gp=struct.unpack_from('<I',data,reginfo[4]+20)[0]
    for s in sections:
        if s[1]!=1 or not s[2]&4:continue
        for p in range(s[4],s[4]+s[5]-3,4):
            w=struct.unpack_from('<I',data,p)[0];op=w>>26;rs=(w>>21)&31;imm=w&65535
            if op==9 and rs==28:
                val=(gp+(imm if imm<32768 else imm-65536))&0xffffffff
                refs[val].append(dict(kind='gp_addiu',offset=p,gp=gp,word=w))
            if op not in (9,13) or p<s[4]+4:continue
            prev=struct.unpack_from('<I',data,p-4)[0]
            if prev>>26!=15 or ((prev>>16)&31)!=rs:continue
            val=(prev&65535)<<16
            val=(val+(imm if imm<32768 else imm-65536))&0xffffffff if op==9 else val|imm
            refs[val].append(dict(kind='adjacent_lui',offset=p-4,words=[prev,w]))
    return refs

def rebuild_archive(hed,dat,replacements):
    """Use existing zero padding first; append overflowing members at aligned offsets."""
    entries,_=hed_tree(hed);ordered=sorted(entries,key=lambda e:e['offset'])
    limits={e['path']:(ordered[i+1]['offset'] if i+1<len(ordered) else len(dat)) for i,e in enumerate(ordered)}
    out=bytearray(dat);newhed=bytearray(hed);changes=[]
    for e in entries:
        if e['path'] not in replacements:continue
        payload=replacements[e['path']];old=dat[e['offset']:e['offset']+e['size']]
        if payload==old:continue
        off=e['offset']
        if off+len(payload)>limits[e['path']]:
            off=align(len(out));out.extend(bytes(off-len(out)));out.extend(payload)
            out.extend(bytes(align(len(out))-len(out)))
        else:
            if len(payload)>e['size'] and any(dat[off+e['size']:off+len(payload)]):raise ValueError('Nonzero member padding')
            span=max(e['size'],len(payload));out[off:off+span]=payload+bytes(span-len(payload))
        struct.pack_into('<II',newhed,e['index']*44,off,len(payload))
        changes.append(dict(path=e['path'],old_offset=e['offset'],new_offset=off,old_size=e['size'],new_size=len(payload),sha256=sha(payload)))
    newentries,_=hed_tree(newhed)
    for before,after in zip(entries,newentries):
        assert before['path']==after['path'] and before['timestamp']==after['timestamp']
        expected=replacements.get(before['path'],dat[before['offset']:before['offset']+before['size']])
        assert out[after['offset']:after['offset']+after['size']]==expected
    spans=sorted((e['offset'],e['offset']+e['size']) for e in newentries)
    assert all(a[1]<=b[0] for a,b in zip(spans,spans[1:]))
    return bytes(newhed),bytes(out),dict(members_verified=len(entries),changes=changes,all_other_members_identical=True)

def directory_fields(fp,inv,path):
    parent,_,name=path.rpartition('/');directory=next(e for e in inv['directories'] if e['path']==parent)
    base=directory['lba']*2048;fp.seek(base);raw=exact(fp,directory['size']);pos=0;found=[]
    while pos<len(raw):
        size=raw[pos]
        if not size:pos=(pos//2048+1)*2048;continue
        n=raw[pos+33:pos+33+raw[pos+32]].decode('ascii').split(';')[0]
        if n==name:found.append((base+pos+2,base+pos+10))
        pos+=size
    assert len(found)==1
    return found[0]

def verify_stream(source,output,patches,expected):
    """Verify every output byte against base plus plan without a per-byte dictionary."""
    old_hash=hashlib.sha256();new_hash=hashlib.sha256();changed=0
    with source.open('rb') as a,output.open('rb') as b:
        def unchanged(n):
            while n:
                x=exact(a,min(n,CHUNK));y=exact(b,len(x));assert x==y
                old_hash.update(x);new_hash.update(y);n-=len(x)
        for p in sorted(patches,key=lambda p:p['offset']):
            unchanged(p['offset']-a.tell())
            x=exact(a,len(p['data']));y=exact(b,len(x));assert y==p['data'] and sha(x)==p['expected_sha256']
            old_hash.update(x);new_hash.update(y);changed+=sum(i!=j for i,j in zip(x,y))
        unchanged(source.stat().st_size-a.tell());assert not b.read(1)
    assert old_hash.hexdigest()==BASE_HASH and new_hash.hexdigest()==expected
    return dict(passed=True,changed_bytes=changed,all_unplanned_bytes_identical=True)

def build(prepare_only=False):
    output=OUT/'Poison Pink (Japan) - Korean text v1.iso'
    if output.exists():raise ValueError('Refusing completed ISO overwrite')
    OUT.mkdir(parents=True,exist_ok=True)
    source=ROOT/BASE_PATH;inv=iso_inventory(source);iso_entries={e['path']:e for e in inv['files']}
    plan=[json.loads(l) for l in (INPUT/'plan.jsonl').open()]
    print('Loading latest user artwork ISO and checking text references',flush=True)
    with source.open('rb') as fp:
        def read(path):
            e=iso_entries[path];fp.seek(e['lba']*2048);return exact(fp,e['size'])
        elf=read('SLPS_258.54');refs=elf_refs(elf);refkeys=sorted(refs)
        selected=[];late_exclusions=[]
        for row in plan:
            if row['catalog']=='elf':
                m=row['metadata'];va=m['virtual_address'];end=va+m['source_byte_length']
                interior=refkeys[bisect.bisect_right(refkeys,va):bisect.bisect_left(refkeys,end)]
                if not refs.get(va) or interior:
                    late_exclusions.append(dict(id=row['id'],reason='unresolved_reference' if not refs.get(va) else 'interior_string_reference'));continue
                row['references']=refs[va]
            selected.append(row)
        hed,dat=read('DATA/SYSTEM.HED'),read('DATA/SYSTEM.DAT');members={e['path']:e for e in hed_tree(hed)[0]}
        def member(path):
            e=members[path];return dat[e['offset']:e['offset']+e['size']]
        old_font=member('system/kanji.dat');old_table=member('system/kantable.dat');table=list(struct.unpack('<7560h',old_table))
        base=json.loads((ROOT/'reports/ui_remaining.json').read_text());mapping=dict(base['mapping'])
        assert len(old_font)//144==2212
        for c,m in mapping.items():assert table[m['table_index']]==m['glyph_id']
        targets={r['target'] for r in selected};needed={c for t in targets for c in t if ord(c)>127 and c not in mapping}
        # Reuse existing Japanese punctuation/range symbols; Hangul receives new glyphs.
        native=[]
        for c in sorted(needed):
            if '\uac00'<=c<='\ud7a3':continue
            try:
                raw=c.encode('cp932');assert len(raw)==2;idx=japanese_index(int.from_bytes(raw,'big'));assert 0<=idx<len(table) and table[idx]>=0
            except (UnicodeError,ValueError,AssertionError):continue
            mapping[c]=dict(code_hex=raw.hex(),table_index=idx,glyph_id=table[idx],native=True);native.append(c)
        chars=sorted(needed-set(native));padding=len(chars)%2
        assert file_hash(FONT_SOURCE)==json.loads((ROOT/'reports/status_slice.json').read_text())['font_source_sha256']
        slots=choose_slots(table,used_byte_pairs(),len(chars));glyphs=rasterize(FONT_SOURCE,chars)
        font=bytearray(old_font+bytes((len(chars)+padding)*144))
        for i,(c,(code,idx)) in enumerate(zip(chars,slots)):
            gid=len(old_font)//144+i;table[idx]=gid;mapping[c]=dict(code_hex=code.to_bytes(2,'big').hex(),table_index=idx,glyph_id=gid)
            encode_glyph(font,gid,glyphs[c])
            assert decode_glyph(font,gid)==glyphs[c]
        assert font[:len(old_font)]==old_font
        assert all(v==-1 or table[i]==v for i,v in enumerate(struct.unpack('<7560h',old_table)))
        assert len(font)//144<32768
        encoded={t:encode_korean(t,mapping) for t in targets}
        assert all(decode_korean(raw,mapping)==t for t,raw in encoded.items())
        nh,nd,shift=grow_font_archive(hed,dat,bytes(font),struct.pack('<7560h',*table))
        staged={'DATA/SYSTEM.HED':nh,'DATA/SYSTEM.DAT':nd};archives={};checks=[]
        print('Font ready:',len(chars),'new characters;',len(selected),'selected records',flush=True)
        by_path=defaultdict(list)
        for r in selected:
            if r['catalog']=='structured':by_path[r['metadata']['path']].append(r)
        for arch in ['DMAP','STATUS']:
            hed=read('DATA/'+arch+'.HED');dat=read('DATA/'+arch+'.DAT');members={e['path']:e for e in hed_tree(hed)[0]};replacements={}
            for path,rows in by_path.items():
                if path not in members:continue
                e=members[path];current=dat[e['offset']:e['offset']+e['size']]
                original=(ROOT/'extracted/original/raw'/arch/path).read_bytes()
                assert sha(original)==rows[0]['metadata']['member_sha256']
                if path.endswith('.rtb'):
                    oldmodel=rtb.parse(original);model=rtb.parse(current)
                    assert rtb.control_signature(oldmodel)==rtb.control_signature(model)
                    oldops=[o for f in oldmodel['functions'] for o in f['instructions'] if o['opcode']==0x33]
                    ops=[o for f in model['functions'] for o in f['instructions'] if o['opcode']==0x33]
                    assert len(ops)==len(oldops)
                    indexes={o['offset']:i for i,o in enumerate(oldops)};edits={}
                    for r in rows:
                        m=r['metadata'];i=indexes[m['opcode_offset']];assert oldops[i]['args'][0]==m['raw_hex']
                        edits[ops[i]['offset']]=(bytes.fromhex(ops[i]['args'][0]),encoded[r['target']])
                    modified=rtb.replace_strings(current,edits,sha(current))
                    final=rtb.parse(modified);finalops=[o for f in final['functions'] for o in f['instructions'] if o['opcode']==0x33]
                    for i,(before,after) in enumerate(zip(ops,finalops)):
                        expected=edits.get(before['offset'],(None,bytes.fromhex(before['args'][0])))[1]
                        assert bytes.fromhex(after['args'][0])==expected
                else:
                    kind=Path(path).stem;model=db.parse(current,kind);origmodel=db.parse(original,kind);edits={}
                    def fields(model,s,i):return {f['name']:f for f in model['sections'][s]['records'][i]['fields']}
                    for r in rows:
                        m=r['metadata'];s=m['section'];i=m['record'];name=m['field']
                        assert fields(origmodel,s,i)[name]['value'].hex()==m['raw_hex']
                        edits[(s,i,name)]=(fields(model,s,i)[name]['value'],encoded[r['target']])
                    modified=db.replace_text(current,kind,edits,sha(current));final=db.parse(modified,kind)
                    assert db.nontext_signature(model)==db.nontext_signature(final)
                    for s,section in enumerate(model['sections']):
                        for i,record in enumerate(section['records']):
                            for f in record['fields']:
                                expected=edits[(s,i,f['name'])][1] if (s,i,f['name']) in edits else f['value']
                                assert fields(final,s,i)[f['name']]['value']==expected
                replacements[path]=modified
                checks.append(dict(path=path,rows=len(rows),before_sha256=sha(current),after_sha256=sha(modified),before_bytes=len(current),after_bytes=len(modified),nontext_preserved=True,untargeted_text_preserved=True))
                if len(checks)%25==0:print('Checked text members',len(checks),flush=True)
            nh,nd,report=rebuild_archive(hed,dat,replacements);archives[arch]=report
            staged['DATA/'+arch+'.HED']=nh;staged['DATA/'+arch+'.DAT']=nd
        original_elf=(ROOT/'extracted/original/disc/SLPS_258.54').read_bytes();newelf=bytearray(elf);elfchecks=[]
        for r in selected:
            if r['catalog']!='elf':continue
            m=r['metadata'];pos=m['payload_offset'];old=bytes.fromhex(m['raw_hex']);new=encoded[r['target']]
            assert original_elf[pos-1]==0 and original_elf[pos:pos+len(old)+1]==old+b'\0'
            assert len(new)<=len(old) and b'\0' not in new
            newelf[pos:pos+len(old)+1]=new+bytes(len(old)+1-len(new))
            elfchecks.append(dict(id=r['id'],source=r['source'],target=r['target'],offset=pos,capacity=len(old),bytes=len(new),references=r['references']))
        allowed=set(i for r in elfchecks for i in range(r['offset'],r['offset']+r['capacity']+1))
        assert all(a==b or i in allowed for i,(a,b) in enumerate(zip(elf,newelf)))
        staged['SLPS_258.54']=bytes(newelf)
        patches=[];expected_inv=json.loads(json.dumps(inv));moves=[]
        occupied=sorted((e['lba']*2048,align(e['lba']*2048+e['size'],2048)) for e in inv['files']+inv['directories'])
        gap_end=iso_entries['DATA/SYSTEM.DAT']['lba']*2048
        gap_start=max(b for a,b in occupied if b<=gap_end)
        cursor=gap_end
        for path,payload in staged.items():
            e=iso_entries[path];oldpos=e['lba']*2048;newpos=oldpos
            if len(payload)>e['size']:
                newpos=(cursor-len(payload))//ALIGN*ALIGN
                if newpos<gap_start:raise ValueError('Insufficient unused ISO gap')
                fp.seek(newpos);remaining=cursor-newpos
                while remaining:
                    block=exact(fp,min(CHUNK,remaining));assert not any(block);remaining-=len(block)
                cursor=newpos
            fp.seek(newpos);old=exact(fp,len(payload))
            if old!=payload:patches.append(dict(offset=newpos,data=payload,expected_sha256=sha(old)))
            if newpos!=oldpos or len(payload)!=e['size']:
                lba_field,size_field=directory_fields(fp,inv,path)
                for off,n in [(lba_field,newpos//2048),(size_field,len(payload))]:
                    data=struct.pack('<I',n)+struct.pack('>I',n);fp.seek(off);old=exact(fp,8)
                    if old!=data:patches.append(dict(offset=off,data=data,expected_sha256=sha(old)))
                next(x for x in expected_inv['files'] if x['path']==path).update(lba=newpos//2048,size=len(payload))
                moves.append(dict(path=path,old_lba=e['lba'],new_lba=newpos//2048,old_size=e['size'],new_size=len(payload)))
        # Hash every adopted texture from the baseline, then compare the final archive content.
        artwork=[]
        policy=json.loads((ROOT/'localization/pipeline.json').read_text())['user_artwork_policy']['adopted_assets']
        for path in policy:
            arch=path.split('/')[0].upper();oldhed=read('DATA/'+arch+'.HED');olddat=read('DATA/'+arch+'.DAT')
            oe=next(e for e in hed_tree(oldhed)[0] if e['path']==path)
            newhed=staged.get('DATA/'+arch+'.HED',oldhed);newdat=staged.get('DATA/'+arch+'.DAT',olddat)
            ne=next(e for e in hed_tree(newhed)[0] if e['path']==path)
            before=olddat[oe['offset']:oe['offset']+oe['size']];after=newdat[ne['offset']:ne['offset']+ne['size']]
            assert before==after;artwork.append(dict(path=path,sha256=sha(after)))
    report=dict(base_iso=BASE_PATH,base_iso_sha256=BASE_HASH,iso_path=str(output.relative_to(ROOT)),runtime_verified=False,
        applied_counts=dict(Counter('elf' if r['catalog']=='elf' else r['metadata']['kind'] for r in selected)),
        font=dict(added_characters=chars,added_glyphs=len(chars)+padding,total_glyphs=len(font)//144,previous_2212_glyphs_preserved=True,original_mapping_preserved=True,native_symbols_reused=native),
        mapping=mapping,font_source_sha256=file_hash(FONT_SOURCE),archives=archives,text_member_checks=checks,elf=elfchecks,late_exclusions=late_exclusions,
        user_artwork_preserved=artwork,iso_directory_changes=moves,plan_sha256=file_hash(INPUT/'plan.jsonl'))
    write_json(OUT/'prepare.json',report)
    if prepare_only:
        print(json.dumps(dict(prepared=True,applied_counts=report['applied_counts'],late_exclusions=len(late_exclusions),relocations=moves),ensure_ascii=False),flush=True);return
    print('Writing and verifying ISO',flush=True)
    iso=overlay(source,output,patches,BASE_HASH);assert iso_inventory(output)==expected_inv
    report.update(iso=iso,entire_iso_diff=verify_stream(source,output,patches,iso['output_sha256']))
    # Verify all emitted file payloads independently from the output ISO.
    with output.open('rb') as fp:
        for path,payload in staged.items():
            e=next(e for e in expected_inv['files'] if e['path']==path);fp.seek(e['lba']*2048);assert exact(fp,e['size'])==payload
    write_json(OUT/'manifest.json',report);write_json(ROOT/'reports/user_translations_applied_20260917.json',report)
    print(json.dumps(dict(output=str(output),sha256=iso['output_sha256'],counts=report['applied_counts'],artwork_preserved=len(artwork),static_checks=True),ensure_ascii=False),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare-only',action='store_true');a=p.parse_args();build(a.prepare_only)
