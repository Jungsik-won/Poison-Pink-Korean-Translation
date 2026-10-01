#!/usr/bin/env python3
"""Two isolated, reviewed RTB string-resize probes using the verified 32-glyph font."""
import argparse
import hashlib
import json
from pathlib import Path
from localization_pipeline import ROOT,sha,file_hash,write_json
from iso_archive_stage import SOURCE,ISO,CHUNK,exact,source_sha,stage_archive,stage_iso,iso_inventory
from korean_sentence_probe import archive_member,encode_korean,decode_korean,MEMBER_PATH,TARGET_ID,ORIGINAL
from rtb_codec import parse,replace_strings,control_signature,summary

BASE=ROOT/'build/korean_sentence'
OUT=ROOT/'build/rtb_resize'
VARIANTS={'longer':'전투의 기본을 알려주마.','shorter':'전투 기본을 알려주마'}


def verify_iso(output,staged):
    inventory=iso_inventory(ISO)
    if iso_inventory(output)!=inventory:raise ValueError('ISO layout mismatch')
    entries={e['path']:e for e in inventory['files']};expected={}
    for path,replacement in staged.items():
        base=entries[path]['lba']*2048;pos=0
        with (SOURCE/path).open('rb') as a,replacement.open('rb') as b:
            while True:
                old=a.read(CHUNK)
                if not old:break
                new=exact(b,len(old))
                if new!=old:
                    expected.update((base+pos+i,(x,y)) for i,(x,y) in enumerate(zip(old,new)) if x!=y)
                pos+=len(old)
            if b.read(1):raise ValueError('Staged file size changed')
    count=len(expected);oldhash=hashlib.sha256();newhash=hashlib.sha256();pos=0
    with ISO.open('rb') as a,output.open('rb') as b:
        while True:
            old=a.read(CHUNK)
            if not old:break
            new=exact(b,len(old));oldhash.update(old);newhash.update(new)
            if new!=old:
                for i,(x,y) in enumerate(zip(old,new)):
                    if x!=y and expected.pop(pos+i,None)!=(x,y):raise ValueError('Unexpected ISO change')
            pos+=len(old)
        if b.read(1):raise ValueError('Trailing ISO bytes')
    if expected or oldhash.hexdigest()!=source_sha(ISO):raise ValueError('Source/diff mismatch')
    return dict(passed=True,changed_bytes=count,sha256=newhash.hexdigest(),layout_preserved=True)


def build(variant):
    dest=OUT/variant
    if dest.exists():raise ValueError('Refusing overwrite of probe directory')
    prior=json.loads((ROOT/'reports/korean_sentence_probe.json').read_text())
    if not prior['runtime_verified']:raise ValueError('Base font not verified')
    for filename,key in [('SYSTEM.HED','hed'),('SYSTEM.DAT','dat')]:
        if file_hash(BASE/'DATA'/filename)!=prior['stages'][0][key]['output_sha256']:
            raise ValueError('Base font archive mismatch')
    review=json.loads((ROOT/'localization/rtb_resize_review.json').read_text())[variant]
    if review['status']!='reviewed' or review['id']!=TARGET_ID or review['target']!=VARIANTS[variant]:
        raise ValueError('Missing matching reviewed translation')
    entry,data=archive_member('DMAP',MEMBER_PATH)
    source=prior['source_literal'];off=source['opcode_offset']
    if sha(data)!=source['member_sha256'] or review['source_sha256']!=source['source_sha256']:
        raise ValueError('Wrong source revision')
    encoded=encode_korean(review['target'],prior['mapping'])
    if decode_korean(encoded,prior['mapping'])!=review['target']:raise ValueError('Encoding roundtrip failed')
    original=bytes.fromhex(source['raw_hex'])
    patched=replace_strings(data,{off:(original,encoded)},source['member_sha256'])
    before,after=parse(data),parse(patched)
    if control_signature(before)!=control_signature(after):raise ValueError('Control flow differs')
    dest.mkdir(parents=True)
    (dest/'t00_0010.rtb').write_bytes(patched)
    archive=stage_archive('DMAP',dest/'DATA',{MEMBER_PATH:patched},allow_padding_growth=True,allow_shrink=True)
    staged={'DATA/SYSTEM.HED':BASE/'DATA/SYSTEM.HED','DATA/SYSTEM.DAT':BASE/'DATA/SYSTEM.DAT',
            'DATA/DMAP.HED':dest/'DATA/DMAP.HED','DATA/DMAP.DAT':dest/'DATA/DMAP.DAT'}
    output=dest/('Poison Pink (Japan) - '+variant+'.iso')
    iso=stage_iso(output,staged)
    verified=verify_iso(output,staged)
    if verified['sha256']!=iso['output_sha256']:raise ValueError('Output hash mismatch')
    report=dict(variant=variant,source=ORIGINAL,translation=review['target'],id=TARGET_ID,
        original_bytes=len(original),translated_bytes=len(encoded),delta=len(encoded)-len(original),
        original_rtb_size=len(data),rtb_size=len(patched),rtb_sha256=sha(patched),
        structure=summary(after),instruction_count_and_branches_preserved=True,
        archive=archive,iso=iso,entire_iso_diff=verified,iso_path=str(output.relative_to(ROOT)),
        runtime_verified=False,base_font_report='reports/korean_sentence_probe.json')
    write_json(dest/'manifest.json',report)
    write_json(ROOT/('reports/rtb_resize_'+variant+'.json'),report)
    print(json.dumps(dict(variant=variant,delta=report['delta'],iso_path=report['iso_path'],sha256=iso['output_sha256'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('variant',choices=list(VARIANTS));args=parser.parse_args()
    build(args.variant)
