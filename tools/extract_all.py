#!/usr/bin/env python3
"""Extract locked original archives, every TIM2, and untranslated text catalogs."""
import argparse,collections,csv,hashlib,json,re,shutil,struct
from pathlib import Path
import numpy as np
from PIL import Image
from localization_pipeline import ROOT,hed_tree,file_hash,sha,source_snapshot,write_json
from iso_archive_stage import SOURCE,exact
from rtb_codec import parse as parse_rtb,serialize as serialize_rtb
from status_db_codec import parse as parse_db,serialize as serialize_db,text_fields,SCHEMAS
from ui_texture_codec import parse as parse_tm2,serialize as serialize_tm2
from font_pair_probe import decode_glyph

JP=re.compile('[\u3040-\u30ff\u3400-\u9fff]')
NULL_TEXT=re.compile(rb'(?:[\x09\x0a\x0d\x20-\x7e\xa1-\xdf]|[\x81-\x9f\xe0-\xfc][\x40-\x7e\x80-\xfc]){4,1024}\x00')
MEDIA={'.tm2','.uad','.ag','.ags','.bd','.th','.ipu','.ico','.img'}


def decode(raw):
    try:return raw.decode('cp932'),None
    except UnicodeDecodeError as ex:return None,str(ex)


def safe_path(out,relative):
    p=Path(relative)
    if p.is_absolute() or any(x in ('.','..') for x in p.parts):raise ValueError('Unsafe extracted path')
    dest=out/p
    if out.resolve() not in dest.resolve().parents:raise ValueError('Path escapes output')
    dest.parent.mkdir(parents=True,exist_ok=True)
    return dest


def put(out,relative,data):
    p=safe_path(out,relative)
    if p.exists():
        if p.is_symlink() or p.read_bytes()!=data:raise ValueError('Different existing extraction: '+str(p))
    else:p.write_bytes(data)
    return p


def literal(raw,**context):
    text,error=decode(raw)
    return dict(context,source=text,raw_hex=raw.hex(),source_sha256=sha(raw),source_byte_length=len(raw),decode_error=error,japanese_candidate=bool(text and JP.search(text)),target='',status='untranslated')


def rgba(model):
    indices=np.frombuffer(model['indices'],dtype=np.uint8)
    if model['bpp']==4:
        unpacked=np.empty(indices.size*2,dtype=np.uint8);unpacked[::2]=indices&15;unpacked[1::2]=indices>>4;indices=unpacked
    pal=np.array([list(c) for c in model['palette']],dtype=np.uint16);pal[:,3]=np.minimum(255,pal[:,3]*2)
    return pal.astype(np.uint8)[indices].reshape(model['height'],model['width'],4)


def write_png(out,name,values):
    p=safe_path(out,name);im=Image.fromarray(values,'RGBA');im.save(p)
    with Image.open(p) as check:
        if check.mode!='RGBA' or check.tobytes()!=im.tobytes():raise ValueError('PNG pixels changed')
    return dict(png=str(p.relative_to(ROOT)),png_sha256=file_hash(p),rgba_sha256=sha(im.tobytes()),width=im.width,height=im.height)


def rtb_strings(raw,path,member_hash):
    model=parse_rtb(raw)
    if serialize_rtb(model)!=raw:raise ValueError('RTB roundtrip failed')
    for f in model['functions']:
        for i,o in enumerate(f['instructions']):
            if o['opcode']!=0x33:continue
            field=model['fields'][o['string_fields'][1]];value=bytes.fromhex(o['args'][0])
            yield literal(value,id=f'{path}:0x{o["offset"]:08x}',kind='rtb_literal',confidence='parsed_string_instruction',path=path,member_sha256=member_hash,function=f['name'],function_offset=f['offset'],instruction_index=i,opcode_offset=o['offset'],payload_offset=field['offset'],packed_operand=o['packed'])


def candidates(raw,path,member_hash):
    for m in NULL_TEXT.finditer(raw):
        value=m.group()[:-1];text,error=decode(value)
        if error or len(JP.findall(text))<2:continue
        yield literal(value,id=f'{path}:candidate:0x{m.start():08x}',kind='binary_string_candidate',confidence='unverified_null_terminated_scan',path=path,member_sha256=member_hash,payload_offset=m.start())


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',default='extracted/original');a=ap.parse_args()
    out=(ROOT/a.output).resolve()
    if out==SOURCE.resolve() or ROOT not in out.parents or SOURCE.resolve() in out.parents:raise ValueError('Unsafe output')
    if (out/'manifest.json').exists():raise ValueError('Completed extraction exists')
    out.mkdir(parents=True,exist_ok=True)
    lock=json.loads((ROOT/'localization/source.lock.json').read_text())['files']
    if source_snapshot(SOURCE)!=lock:raise ValueError('Original source lock mismatch')
    raw_rows=[];image_rows=[];unknown=[];archives=[];counts=collections.Counter();all_text=[];binary_rows=[];embedded=[]
    for hed in sorted((SOURCE/'DATA').glob('*.HED')):
        dat=hed.with_suffix('.DAT')
        if not dat.exists():continue # SUBDIR.HED is retained below as a disc metadata file.
        entries,dirs=hed_tree(hed.read_bytes());spans=sorted((e['offset'],e['offset']+e['size']) for e in entries)
        if any(end>dat.stat().st_size for start,end in spans) or any(spans[i][1]>spans[i+1][0] for i in range(len(spans)-1)):raise ValueError('Overlapping/out-of-bounds archive')
        archives.append(dict(archive=hed.stem,files=len(entries),payload_bytes=sum(e['size'] for e in entries),hed_sha256=file_hash(hed),dat_sha256=lock[str(dat.relative_to(SOURCE))]['sha256']))
        with dat.open('rb') as fp:
            for entry in entries:
                path=entry['path'];ext=Path(path).suffix.lower();dest=safe_path(out,'raw/'+hed.stem+'/'+path);fp.seek(entry['offset']);h=hashlib.sha256();remain=entry['size']
                if dest.exists():
                    with dest.open('rb') as check:
                        while remain:
                            data=exact(fp,min(remain,1048576));h.update(data)
                            if exact(check,len(data))!=data:raise ValueError('Different extracted member')
                            remain-=len(data)
                        if check.read(1):raise ValueError('Extra extracted bytes')
                else:
                    with dest.open('xb') as target:
                        while remain:
                            data=exact(fp,min(remain,1048576));h.update(data);target.write(data);remain-=len(data)
                digest=h.hexdigest();raw_rows.append(dict(archive=hed.stem,path=path,hed_index=entry['index'],offset=entry['offset'],bytes=entry['size'],sha256=digest,raw=str(dest.relative_to(ROOT))))
                counts['raw_members']+=1
                if ext=='.tm2':
                    raw=dest.read_bytes()
                    try:
                        model=parse_tm2(raw)
                        if serialize_tm2(model)!=raw:raise ValueError('TM2 roundtrip failed')
                        result=write_png(out,'images/'+hed.stem+'/'+path+'.png',rgba(model))
                        image_rows.append(dict(archive=hed.stem,path=path,raw_sha256=digest,bpp=model['bpp'],clut_storage=model['clut_storage'],roundtrip_verified=True,visual_review=False,**result));counts['textures']+=1
                    except ValueError as ex:unknown.append(dict(path=path,kind='texture_decode',reason=str(ex),raw_preserved=True))
                elif ext=='.rtb':
                    rows=list(rtb_strings(dest.read_bytes(),path,digest));all_text.extend(rows);counts['rtb_files']+=1;counts['rtb_literals']+=len(rows)
                    text='\n\n'.join('[%s / %s / 0x%08x]\n%s'%(r['id'],r['function'],r['payload_offset'],r['source'] if r['source'] is not None else '<decode error: '+r['raw_hex']+'>') for r in rows)
                    put(out,'text/rtb/'+path+'.txt',text.encode('utf-8'))
                elif hed.stem=='STATUS' and Path(path).stem in SCHEMAS:
                    kind=Path(path).stem;raw=dest.read_bytes();model=parse_db(raw,kind)
                    if serialize_db(model)!=raw:raise ValueError('DB roundtrip failed')
                    rows=[literal(f['value'],id=f'{path}:{key[0]}:{key[1]}:{key[2]}',kind='db_field',confidence='parsed_db_field',path=path,member_sha256=digest,section=key[0],record=key[1],field=key[2],payload_offset=f['offset']) for key,f in text_fields(model)]
                    all_text.extend(rows);counts['db_files']+=1;counts['db_fields']+=len(rows)
                elif ext in {'.txt','.h','.cnf'}:
                    raw=dest.read_bytes();row=literal(raw,id=path,kind='plain_file',confidence='whole_text_file',path=path,member_sha256=digest,payload_offset=0);all_text.append(row)
                    if row['source'] is not None:put(out,'text/plain/'+hed.stem+'/'+path+'.utf8.txt',row['source'].encode('utf-8'))
                elif ext not in MEDIA and path not in ('system/kanji.dat','system/kantable.dat'):
                    binary_rows.extend(candidates(dest.read_bytes(),path,digest))
                # Native embedded TIM2 payloads in model/other containers are also inventoried.
                if ext!='.tm2' and ext not in {'.ag','.ags','.bd','.th','.ipu','.ico'}:
                    data=dest.read_bytes();cursor=0
                    while True:
                        pos=data.find(b'TIM2\x04\x00\x01\x00',cursor)
                        if pos<0:break
                        cursor=pos+8
                        if pos+64>len(data):continue
                        size=16+struct.unpack_from('<I',data,pos+16)[0]
                        if pos+size>len(data):continue
                        try:model=parse_tm2(data[pos:pos+size])
                        except ValueError:continue
                        name=f'images/embedded/{hed.stem}/{path}.at-{pos:08x}';result=write_png(out,name+'.png',rgba(model))
                        carved=put(out,name+'.tm2',data[pos:pos+size])
                        embedded.append(dict(archive=hed.stem,path=path,offset=pos,bytes=size,raw=str(carved.relative_to(ROOT)),raw_sha256=sha(data[pos:pos+size]),roundtrip_verified=serialize_tm2(model)==data[pos:pos+size],**result))
        print('Extracted',hed.stem,len(entries),'members;',counts['textures'],'textures;',counts['rtb_literals'],'RTB literals',flush=True)
    # Keep non-archive disc files (ELF, HED metadata, modules, CNF, etc.).
    for path in sorted(SOURCE.rglob('*')):
        if not path.is_file() or path.name=='.DS_Store' or path.suffix.lower()=='.iso':continue
        if path.parent==SOURCE/'DATA' and path.suffix=='.DAT':continue
        relative=str(path.relative_to(SOURCE));raw=path.read_bytes();dest=put(out,'disc/'+relative,raw)
        raw_rows.append(dict(archive=None,path=relative,bytes=len(raw),sha256=sha(raw),raw=str(dest.relative_to(ROOT))))
        if raw[:4]==b'\x7fELF':binary_rows.extend(candidates(raw,relative,sha(raw)))
    # Export the original 24x24 2-bit glyph bank without changing its encoding table.
    font=(out/'raw/SYSTEM/system/kanji.dat').read_bytes();glyph_count=len(font)//144
    if len(font)%288:raise ValueError('Incomplete glyph pair')
    atlas=Image.new('RGBA',(32*24,((glyph_count+31)//32)*24));glyphs=[]
    for gid in range(glyph_count):
        pixels=np.array(decode_glyph(font,gid),dtype=np.uint8).reshape(24,24)*85
        values=np.full((24,24,4),255,dtype=np.uint8);values[:,:,3]=pixels
        result=write_png(out,f'images/font/glyph-{gid:04d}.png',values);glyphs.append(dict(glyph_id=gid,**result));atlas.paste(Image.fromarray(values,'RGBA'),((gid%32)*24,(gid//32)*24))
    atlas.save(out/'images/font/atlas.png');counts['glyphs']=glyph_count
    # Human-editable TSVs have blank targets. JSONL retains exact offsets and bytes.
    for name,rows in [('structured',all_text),('binary_candidates',binary_rows)]:
        p=safe_path(out,'text/'+name+'.jsonl')
        with p.open('w',encoding='utf-8') as fp:
            for row in rows:fp.write(json.dumps(row,ensure_ascii=False)+'\n')
        with safe_path(out,'text/'+name+'.tsv').open('w',encoding='utf-8',newline='') as fp:
            writer=csv.writer(fp,delimiter='\t');writer.writerow(['id','kind','path','function','offset','source','target','status','confidence'])
            for row in rows:writer.writerow([row['id'],row['kind'],row['path'],row.get('function',''),row.get('payload_offset',''),row['source'] or '', '',row['status'],row['confidence']])
    from extract_elf_text import export as export_elf
    counts['elf_strings']=export_elf(out)['strings']
    counts['structured_texts']=len(all_text);counts['structured_japanese_candidates']=sum(r['japanese_candidate'] for r in all_text);counts['binary_candidates']=len(binary_rows);counts['embedded_textures']=len(embedded)
    # Independent reread of every extracted raw file, not just counts from the writer.
    for row in raw_rows:
        p=ROOT/row['raw']
        if p.stat().st_size!=row['bytes'] or file_hash(p)!=row['sha256']:raise ValueError('Extracted file failed verification')
    for name,rows in [('files',raw_rows),('images',image_rows),('embedded_images',embedded),('glyphs',glyphs)]:write_json(out/(name+'.json'),rows)
    report=dict(schema_version=1,source='locked original, not translated ISO',output=str(out.relative_to(ROOT)),source_lock_sha256=file_hash(ROOT/'localization/source.lock.json'),source_lock_matched=True,archives=archives,counts=dict(counts),all_raw_hashes_verified=True,unknown_formats=unknown,translation_performed=False,visual_or_runtime_verification=False,limitations=['CP932 text views retain game-specific glyph differences; original bytes are authoritative.','Binary candidates may include false positives and are not confirmed dialogue.','All archive members including video/audio/models are kept raw; videos are not expanded into frames.','PS2 save-icon model is kept raw; not a flat TIM2 image.','PNG layout is statically decoded; no game/image inspection performed.'])
    write_json(out/'manifest.json',report);write_json(ROOT/'reports/full_extraction.json',report)
    print(json.dumps(dict(counts=counts,unknown=unknown),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
