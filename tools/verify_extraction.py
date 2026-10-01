#!/usr/bin/env python3
"""Verify extracted bytes/text offsets/PNG hashes without displaying images."""
import argparse,csv,json
from pathlib import Path
from localization_pipeline import ROOT,file_hash,sha,write_json


def verify(out):
    report=json.loads((out/'manifest.json').read_text())
    files=json.loads((out/'files.json').read_text());lookup={r['path']:r for r in files}
    if len(lookup)!=len(files):raise ValueError('Ambiguous source paths')
    for row in files:
        p=ROOT/row['raw']
        if p.stat().st_size!=row['bytes'] or file_hash(p)!=row['sha256']:raise ValueError('Extracted file changed: '+row['path'])
    images=json.loads((out/'images.json').read_text());embedded=json.loads((out/'embedded_images.json').read_text());glyphs=json.loads((out/'glyphs.json').read_text())
    for row in images+embedded+glyphs:
        if file_hash(ROOT/row['png'])!=row['png_sha256']:raise ValueError('PNG changed')
    for row in embedded:
        if file_hash(ROOT/row['raw'])!=row['raw_sha256']:raise ValueError('Embedded texture changed')
    checked={}
    for name in ['structured','binary_candidates','elf_strings']:
        cache=None;raw=b'';count=0
        with (out/'text'/f'{name}.jsonl').open() as fp:
            for line in fp:
                row=json.loads(line)
                if row['target'] or row['status']!='untranslated':raise ValueError('Extraction catalog has translation edits')
                if row['path']!=cache:raw=(ROOT/lookup[row['path']]['raw']).read_bytes();cache=row['path']
                value=bytes.fromhex(row['raw_hex']);pos=row['payload_offset']
                if raw[pos:pos+len(value)]!=value or sha(value)!=row['source_sha256']:raise ValueError('Text source offset/hash mismatch')
                count+=1
        checked[name]=count
    with (out/'images.tsv').open('w',encoding='utf-8',newline='') as fp:
        w=csv.writer(fp,delimiter='\t');w.writerow(['kind','archive','source','offset','width','height','png','raw'])
        for row in images:w.writerow(['texture',row['archive'],row['path'],0,row['width'],row['height'],row['png'],lookup[row['path']]['raw']])
        for row in embedded:w.writerow(['embedded_texture',row['archive'],row['path'],row['offset'],row['width'],row['height'],row['png'],row['raw']])
        for row in glyphs:w.writerow(['font_glyph','SYSTEM','glyph-'+str(row['glyph_id']),'',24,24,row['png'],str((out/'raw/SYSTEM/system/kanji.dat').relative_to(ROOT))])
    with (out/'files.tsv').open('w',encoding='utf-8',newline='') as fp:
        w=csv.writer(fp,delimiter='\t');w.writerow(['archive','path','bytes','sha256','raw'])
        for row in files:w.writerow([row['archive'],row['path'],row['bytes'],row['sha256'],row['raw']])
    report['text_catalog_verification']=dict(passed=True,rows=checked,all_targets_empty=True,all_offsets_match_original_bytes=True)
    report['counts'].update(total_texture_images=len(images)+len(embedded),total_exported_raw_files=len(files),elf_strings=checked['elf_strings'])
    report['png_hashes_verified']=len(images)+len(embedded)+len(glyphs)
    report['font_atlas_sha256']=file_hash(out/'images/font/atlas.png')
    report['tool_sha256']={p:file_hash(ROOT/p) for p in ['tools/extract_all.py','tools/extract_elf_text.py','tools/verify_extraction.py','tools/ui_texture_codec.py','tools/iso_retention.py']}
    write_json(out/'manifest.json',report);write_json(ROOT/'reports/full_extraction.json',report)
    print('Verified raw files:',len(files),'PNG files:',report['png_hashes_verified'],'text rows:',checked)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='extracted/original');a=p.parse_args();out=(ROOT/a.output).resolve()
    if ROOT not in out.parents:raise ValueError('Output outside workspace')
    verify(out)
