#!/usr/bin/env python3
"""Correct two late proofing findings, validate, then replace this turn's generated ISO."""
import json, os, struct
from pathlib import Path
from localization_pipeline import ROOT, sha, write_json, hed_tree, file_hash
from iso_archive_stage import iso_inventory, exact, overlay
from korean_sentence_probe import encode_korean, decode_korean
from build_user_translation_import import verify_stream, BASE_PATH, OUT, INPUT
import rtb_codec as rtb

def main():
    report=json.loads((OUT/'manifest.json').read_text());source=ROOT/report['iso_path']
    output=OUT/'finalized.partial.iso';before_hash=report['iso']['output_sha256'];inv=iso_inventory(source);entries={e['path']:e for e in inv['files']}
    ids={'dmap/script/h07_0060.rtb:0x0000e824','dmap/script/at12.rtb:0x00010ba0'}
    rows=[r for r in map(json.loads,(INPUT/'plan.jsonl').open()) if r['id'] in ids];assert len(rows)==2
    patches=[];changes=[]
    with source.open('rb') as fp:
        he=entries['DATA/DMAP.HED'];de=entries['DATA/DMAP.DAT'];fp.seek(he['lba']*2048);hed=exact(fp,he['size']);newhed=bytearray(hed)
        members={e['path']:e for e in hed_tree(hed)[0]};ordered=sorted(members.values(),key=lambda e:e['offset'])
        limits={e['path']:(ordered[i+1]['offset'] if i+1<len(ordered) else de['size']) for i,e in enumerate(ordered)}
        for row in rows:
            m=row['metadata'];path=m['path'];e=members[path];pos=de['lba']*2048+e['offset'];fp.seek(pos);current=exact(fp,e['size'])
            original=(ROOT/'extracted/original/raw/DMAP'/path).read_bytes();assert sha(original)==m['member_sha256']
            old=rtb.parse(original);model=rtb.parse(current);assert rtb.control_signature(old)==rtb.control_signature(model)
            oldops=[o for f in old['functions'] for o in f['instructions'] if o['opcode']==0x33];ops=[o for f in model['functions'] for o in f['instructions'] if o['opcode']==0x33]
            i=next(i for i,o in enumerate(oldops) if o['offset']==m['opcode_offset']);assert oldops[i]['args'][0]==m['raw_hex']
            payload=encode_korean(row['target'],report['mapping']);assert decode_korean(payload,report['mapping'])==row['target']
            modified=rtb.replace_strings(current,{ops[i]['offset']:(bytes.fromhex(ops[i]['args'][0]),payload)},sha(current))
            span=max(len(current),len(modified));assert e['offset']+span<=limits[path]
            fp.seek(pos);oldbytes=exact(fp,span)
            if span>len(current):assert not any(oldbytes[len(current):])
            patches.append(dict(offset=pos,data=modified+bytes(span-len(modified)),expected_sha256=sha(oldbytes)))
            struct.pack_into('<I',newhed,e['index']*44+4,len(modified))
            changes.append(dict(id=row['id'],target=row['target'],path=path,before_sha256=sha(current),after_sha256=sha(modified),after_bytes=len(modified)))
        patches.append(dict(offset=he['lba']*2048,data=bytes(newhed),expected_sha256=sha(hed)))
    interim=overlay(source,output,patches,before_hash);assert iso_inventory(output)==inv
    # Verify full baseline relationship through the original explicitly staged ranges.
    full=[]
    with output.open('rb') as fp:
        for r in report['iso']['replacements']:
            fp.seek(r['offset']);data=exact(fp,r['size'])
            full.append(dict(offset=r['offset'],data=data,expected_sha256=r['before_sha256']))
            r['after_sha256']=sha(data)
    verified=verify_stream(ROOT/BASE_PATH,output,full,interim['output_sha256'])
    report['entire_iso_diff']=verified;report['iso']['output_sha256']=interim['output_sha256'];report['iso']['changed_bytes']=verified['changed_bytes']
    report['final_proofing']=dict(previous_generated_iso_sha256=before_hash,changes=changes,overlay=interim)
    report['plan_sha256']=file_hash(INPUT/'plan.jsonl')
    for c in changes:
        check=next(r for r in report['text_member_checks'] if r['path']==c['path']);check.update(after_sha256=c['after_sha256'],after_bytes=c['after_bytes'])
        check=next(r for r in report['archives']['DMAP']['changes'] if r['path']==c['path']);check.update(sha256=c['after_sha256'],new_size=c['after_bytes'])
    os.replace(output,source)
    write_json(OUT/'manifest.json',report);write_json(ROOT/'reports/user_translations_applied_20260917.json',report)
    print(json.dumps(dict(iso=str(source),sha256=interim['output_sha256'],proofing_changes=2,full_diff_verified=True),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
